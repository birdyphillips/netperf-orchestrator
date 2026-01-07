#!/usr/bin/env python3

import argparse
import sys

from packetstorm_logic import PacketStormLogic
from byteblower_logic import ByteBlowerLogic
from iperf3_logic import IPerf3Logic
from logger import Logger

class ByteBlowerCLI:
    def __init__(self):
        self.logger = Logger("ByteBlowerCLI")
    
    def execute(self, bbp_file, rtt_file, iterations, scenario_name, test_group_name=None, client_ip=None, output_format="json", byteblower_only=False, packetstorm_only=False, iperf3_only=False, iperf3_darwin=False, report_formats="html pdf csv xls xlsx json docx"):
        """Execute workflow based on selected modes"""
        try:
            success = True
            
            # Extract RTT value from filename for naming
            rtt_suffix = ""
            if rtt_file and rtt_file != 'default.json':
                # Extract RTT value from filename like 'vcmts10ms.json' -> 'RTT_10ms'
                import re
                rtt_match = re.search(r'(\d+)ms', rtt_file)
                if rtt_match:
                    rtt_suffix = f"_RTT_{rtt_match.group(1)}ms"
            
            if packetstorm_only:
                self.logger.info(f"PacketStorm only mode - config: {rtt_file}")
                ps = PacketStormLogic(rtt_file)
                success = ps.start_config() and ps.stop_config()
            elif byteblower_only:
                self.logger.info(f"ByteBlower only mode - file: {bbp_file}")
                bb = ByteBlowerLogic(bbp_file, scenario_name, scenario_name, test_group_name, rtt_suffix, report_formats)
                success = bb.run_iterations(iterations)
            elif iperf3_only or iperf3_darwin:
                platform_override = 'macos' if iperf3_darwin else None
                self.logger.info(f"iPerf3 only mode - client: {client_ip} - platform: {platform_override or 'auto'}")
                iperf3 = IPerf3Logic(client_ip, scenario_name, test_group_name, rtt_suffix, output_format, platform_override)
                success = iperf3.run_iterations(iterations)
            else:
                # Full workflow with PacketStorm
                ps = PacketStormLogic(rtt_file)
                
                if client_ip:  # iPerf3 + PacketStorm
                    iperf3 = IPerf3Logic(client_ip, scenario_name, test_group_name, rtt_suffix, output_format)
                    success = (ps.start_config() and 
                              iperf3.run_iterations(iterations) and 
                              ps.stop_config())
                else:  # ByteBlower + PacketStorm
                    bb = ByteBlowerLogic(bbp_file, scenario_name, scenario_name, test_group_name, rtt_suffix, report_formats)
                    success = (ps.start_config() and 
                              bb.run_iterations(iterations) and 
                              ps.stop_config())
            
            if success:
                self.logger.info("Workflow completed successfully")
                return 0
            else:
                self.logger.error("Workflow completed with errors")
                return 1
                
        except Exception as e:
            self.logger.error(f"Workflow failed: {e}")
            return 1

def main():
    parser = argparse.ArgumentParser(description='ByteBlower, PacketStorm, and iPerf3 CLI Tool')
    parser.add_argument('-byteblower', action='store_true', help='Enable ByteBlower mode')
    parser.add_argument('--bbp', required=False, help='ByteBlower .bbp file path (e.g., bb_flows/US_Classic.bbp)')
    parser.add_argument('--scenario', required=False, help='Scenario name (e.g., US_Classic_Only)')
    parser.add_argument('-test-group-name', '--test-group-name', help='Test group name (e.g., HSI029_RTT_0)')
    parser.add_argument('-packetstorm', action='store_true', help='Enable PacketStorm mode')
    parser.add_argument('--rtt', help='RTT configuration file (e.g., vcmts10ms.json)')
    parser.add_argument('-iperf3', action='store_true', help='Enable iPerf3 Linux mode')
    parser.add_argument('-iperf3-darwin', action='store_true', help='Enable iPerf3 macOS mode with iperf3-darwin')
    parser.add_argument('--clientIP', help='Linux client IP address for iPerf3 (required with -iperf3)')
    parser.add_argument('--output', choices=['json', 'txt'], default='json', help='iPerf3 output format: json or txt (default: json)')
    parser.add_argument('--report-formats', default='html pdf csv xls xlsx json docx', help='ByteBlower report formats (default: all formats)')
    parser.add_argument('-iteration', type=int, default=1, help='Number of iterations (default: 1)')
    
    args = parser.parse_args()
    
    if not args.byteblower and not args.packetstorm and not args.iperf3 and not getattr(args, 'iperf3_darwin', False):
        parser.error("At least one of -byteblower, -packetstorm, -iperf3, or -iperf3-darwin is required")
    
    if (args.iperf3 or getattr(args, 'iperf3_darwin', False)) and (not args.scenario or not args.clientIP):
        parser.error("Both --scenario and --clientIP are required when using -iperf3 or -iperf3-darwin")
    
    if args.packetstorm and not args.rtt:
        parser.error("--rtt is required when using -packetstorm")
    
    # Use provided bbp file or default
    bb_file = args.bbp or 'default.bbp'
    
    tool = ByteBlowerCLI()
    return tool.execute(
        bb_file, 
        args.rtt or 'default.json', 
        args.iteration,
        args.scenario or 'default',
        getattr(args, 'test_group_name', None),
        getattr(args, 'clientIP', None),
        getattr(args, 'output', 'json'),
        byteblower_only=args.byteblower and not args.packetstorm and not args.iperf3,
        packetstorm_only=args.packetstorm and not args.byteblower and not args.iperf3,
        iperf3_only=args.iperf3 and not args.byteblower and not args.packetstorm and not getattr(args, 'iperf3_darwin', False),
        iperf3_darwin=getattr(args, 'iperf3_darwin', False),
        report_formats=getattr(args, 'report_formats', 'html pdf csv xls xlsx json docx')
    )

if __name__ == '__main__':
    sys.exit(main())