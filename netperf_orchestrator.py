#!/home/aphillips/Projects/LLD_TEST_CLT_v1.4_20260115_160000_linux_compatible/venv/bin/python3

import argparse
import sys
import subprocess
import os
import glob
import time
from datetime import datetime

import csv

try:
    import readline  # enables arrow-key editing in input() prompts
except ImportError:
    pass

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

from packetstorm_logic import PacketStormLogic
from byteblower_logic import ByteBlowerLogic
from iperf3_logic import IPerf3Logic
from speedtest_logic import SpeedTestLogic
from thousandeyes_logic import ThousandEyesLogic
from logger import Logger
from snmp_collector import collect_snmp_data, generate_latency_report, find_snmp_files

try:
    from cmts_collector import CmtsCollector
    CMTS_AVAILABLE = True
except ImportError:
    CMTS_AVAILABLE = False

class NetperfCLI:
    def __init__(self, cmts_type="vcmts"):
        self.logger = Logger("NetperfCLI")
        self.cmts_type = cmts_type
        self.logger.info(f"CMTS type: {cmts_type} ({'Kafka for DS latency' if cmts_type == 'vcmts' else 'SNMP for DS latency'})")

        # Prompt for CM MAC (downstream CMTS Kafka collector — vcmts only)
        if cmts_type == "vcmts":
            from cmts_modem_info import normalize_mac
            while True:
                mac_input = input("Enter CM MAC address (or press Enter to skip CMTS collection): ").strip()
                if not mac_input:
                    self.cm_mac = None
                    self.logger.warning("No CM MAC — downstream CMTS Kafka collection will be skipped")
                    break
                try:
                    self.cm_mac = normalize_mac(mac_input)
                    break
                except ValueError:
                    print(f"Invalid MAC address: '{mac_input}'. Expected format: aabbccddeeff or aa:bb:cc:dd:ee:ff")
                    print("Tip: if you meant to enter an IPv6 address, press Enter to skip and provide it at the next prompt.")
        else:
            self.cm_mac = None
        
        # Auto-lookup IPv6 from CMTS using CM MAC
        self.target_ip = None
        if self.cm_mac:
            self.target_ip = self._lookup_ipv6_from_cmts(self.cm_mac)
            if not self.target_ip:
                answer = input("Cable modem not found on CMTS. Continue without SNMP? [y/N]: ").strip().lower()
                if answer != 'y':
                    print("Test stopped.")
                    sys.exit(1)
        if self.target_ip:
            print(f"Modem IPv6: {self.target_ip}")
        else:
            self.logger.warning("No modem IPv6 — upstream SNMP collection will be skipped")
        
        self.output_dir = None
        self.cmts_collector = None
    
    def _lookup_ipv6_from_cmts(self, mac):
        """SSH to CMTS and run scm command to get the modem IPv6 address.
        vcmts: 'scm <mac> ip'     — IPv6 in table column
        icmts: 'scm <mac> detail' — IPv6= on Uptime line
        Returns the IPv6 string or None if lookup fails."""
        import re
        import paramiko
        import time
        try:
            from config_loader import config
            jumpserver = config.snmp_jumpserver
            username   = config.snmp_username
            key_path   = os.path.expanduser(config.ssh_key_path)
            cmts_pass  = config.vcmts_password

            # Pick CMTS host and command based on type
            if self.cmts_type == 'icmts':
                cmts_host = 'cts01k1dccc'
                scm_cmd   = f"scm {mac} detail"
            else:
                cmts_host = 'apc01k1dccc'
                scm_cmd   = f"scm {mac} ip"

            self.logger.info(f"Looking up IPv6 for {mac} via {cmts_host}...")

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            if os.path.exists(key_path):
                ssh.connect(jumpserver, username=username, key_filename=key_path, timeout=10)
            else:
                ssh.connect(jumpserver, username=username, timeout=10)

            shell = ssh.invoke_shell()
            shell.send(f"ssh -o StrictHostKeyChecking=no {username}@{cmts_host}\n")
            time.sleep(2)
            buf = shell.recv(4096).decode(errors='ignore')
            # Handle up to 3 password attempts (tacacs may prompt multiple times)
            for _ in range(3):
                if 'password' in buf.lower():
                    shell.send(cmts_pass + '\n')
                    time.sleep(2)
                    buf = shell.recv(4096).decode(errors='ignore')
                else:
                    break
            shell.send(scm_cmd + '\n')
            time.sleep(3)
            output = ''
            for _ in range(30):
                if shell.recv_ready():
                    output += shell.recv(4096).decode(errors='ignore')
                    time.sleep(0.3)
                else:
                    time.sleep(0.3)
                    if not shell.recv_ready():
                        break
            shell.send('exit\n')
            shell.close()
            ssh.close()

            # icmts: parse IPv6=<addr> from detail output
            if self.cmts_type == 'icmts':
                match = re.search(r'IPv6=([0-9a-fA-F]{1,4}(?::[0-9a-fA-F]{1,4}){5,7})', output)
            else:
                match = re.search(r'([0-9a-fA-F]{1,4}(?::[0-9a-fA-F]{1,4}){5,7})', output)

            if not match:
                self.logger.warning(f"No IPv6 found in scm output")

            if match:
                ipv6 = match.group(1)
                print(f"Modem IPv6 (auto-detected): {ipv6}")
                return ipv6
            self.logger.warning("scm ran but no IPv6 found")
        except Exception as e:
            self.logger.warning(f"CMTS IPv6 lookup failed: {e}")
        return None

    def start_cmts_collection(self, direction="downstream"):
        """Start CMTS Kafka metrics collection in background.
        Only used for vCMTS downstream. For iCMTS downstream, SNMP handles it."""
        if self.cmts_type == "icmts" and direction == "downstream":
            self.logger.info("iCMTS mode — DS latency collected via SNMP (skipping Kafka)")
            return False
        if not self.cm_mac:
            return False
        if not CMTS_AVAILABLE:
            self.logger.warning("CMTS collector not available (kafka-python not installed) — skipping")
            return False
        try:
            self.cmts_collector = CmtsCollector(mac=self.cm_mac, direction=direction)
            self.cmts_collector.start()
            return True
        except Exception as e:
            self.logger.warning(f"CMTS collection unavailable: {e} — test will continue without it")
            self.cmts_collector = None
            return False

    def wait_for_cmts_poll(self, timeout=None):
        """Wait for next Kafka polling interval. Safe to call if collector not started.

        Uses detected polling interval + 20% headroom. Falls back to 150s on first
        call before any interval is known (covers up to a 120s polling environment).
        """
        if not self.cmts_collector:
            return False
        try:
            if timeout is None:
                interval = self.cmts_collector._get_polling_interval_s()
                # If interval is still the 60s default (not yet detected), use 150s
                # to safely cover environments with up to 120s polling
                timeout = interval * 1.2 if self.cmts_collector._detected_interval_s else 150
            return self.cmts_collector.wait_for_poll(timeout=timeout)
        except Exception as e:
            self.logger.warning(f"wait_for_cmts_poll failed: {e}")
            return False

    def stop_cmts_collection(self, output_dir, test_name, post_test_polls=2, test_duration_s=60):
        """Stop CMTS Kafka collection and generate report.

        Detects the actual Kafka polling interval and waits for
        post_test_polls additional poll cycles after the test ends
        to capture delayed bin reporting data.

        test_duration_s: actual test duration for throughput calculation.
        """
        if not self.cmts_collector:
            return None
        try:
            poll_interval_s = self.cmts_collector._get_polling_interval_s()
            poll_timeout = poll_interval_s * 1.2

            for i in range(post_test_polls):
                if not self.cmts_collector.wait_for_poll(timeout=poll_timeout):
                    self.logger.warning(f"Post-test poll {i+1} timed out")
                    break
            self.cmts_collector.stop()
            report = self.cmts_collector.generate_report(output_dir, test_name, test_duration_s=test_duration_s)
            self.cmts_collector = None
            if report:
                self.logger.info(f"CMTS latency report: {os.path.basename(report)}")
            return report
        except Exception as e:
            self.logger.warning(f"CMTS report generation failed: {e}")
            self.cmts_collector = None
            return None

    def run_snmp_collection(self, test_name, phase, output_dir=None, rtt_suffix=""):
        if not self.target_ip:
            return False
        try:
            if output_dir is None:
                output_dir = "Results"
            collect_snmp_data(self.target_ip, f"{test_name}{rtt_suffix}", phase, output_dir)
            return True
        except Exception as e:
            self.logger.error(f"SNMP collection failed: {e}")
            return False
    
    def execute(self, bbp_file, rtt_files, iterations, scenarios, test_group_name=None, client_ip=None, output_format="json", byteblower_only=False, packetstorm_only=False, iperf3_only=False, iperf3_darwin=False, speedtest_only=False, speedtest_clients=None, thousandeyes_only=False, thousandeyes_unit_id=None, report_formats="html pdf csv xls xlsx json docx"):
        """Execute workflow based on selected modes"""
        try:
            scenario_list = [s.strip() for s in scenarios.split(',')] if scenarios else ['default']
            rtt_list = [r.strip() for r in rtt_files.split(',')] if rtt_files else ['default.json']
            
            # Determine traffic type
            if thousandeyes_only:
                traffic_type = "ThousandEyes"
            elif byteblower_only or (not iperf3_only and not iperf3_darwin and not speedtest_only and not thousandeyes_only):
                traffic_type = "ByteBlower"
            elif iperf3_darwin:
                traffic_type = "iPerf3_macOS"
            elif iperf3_only:
                traffic_type = "iPerf3_Linux"
            elif speedtest_only:
                traffic_type = "SpeedTest"
            else:
                traffic_type = "PacketStorm"
            
            # Extract RTT suffix from first RTT file
            rtt_suffix = ""
            if rtt_list[0] and rtt_list[0] != 'default.json':
                import re
                rtt_match = re.search(r'(\d+)ms', rtt_list[0])
                if rtt_match:
                    rtt_suffix = f"_RTT_{rtt_match.group(1)}ms"
            
            # Create parent output directory with test group name, traffic type, RTT and timestamp
            parent_output_dir = f"Results/{test_group_name}_{traffic_type}{rtt_suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.makedirs(parent_output_dir, exist_ok=True)
            
            # Store traffic type and rtt_suffix for subdirectory naming
            self.traffic_type = traffic_type
            self.rtt_suffix = rtt_suffix
            
            if len(scenario_list) > 1 or len(rtt_list) > 1:
                self.logger.info(f"Multi-scenario run: {len(scenario_list)} scenarios x {len(rtt_list)} RTT configs → {parent_output_dir}")
            
            all_success = True
            all_snmp_files = []
            
            # Run combinations
            for scenario in scenario_list:
                for rtt_file in rtt_list:
                    success, snmp_files = self._run_single_test(bbp_file, rtt_file, iterations, scenario, test_group_name, client_ip, output_format, byteblower_only, packetstorm_only, iperf3_only, iperf3_darwin, speedtest_only, speedtest_clients, thousandeyes_only, thousandeyes_unit_id, report_formats, parent_output_dir, rtt_list)
                    all_success = all_success and success
                    all_snmp_files.extend(snmp_files)
            
            if all_success:
                self.logger.info("All workflows completed successfully")
                return 0
            else:
                self.logger.error("Some workflows completed with errors")
                return 1
                
        except Exception as e:
            self.logger.error(f"Workflow failed: {e}")
            return 1
    
    def _run_single_test(self, bbp_file, rtt_file, iterations, scenario_name, test_group_name, client_ip, output_format, byteblower_only, packetstorm_only, iperf3_only, iperf3_darwin, speedtest_only, speedtest_clients, thousandeyes_only, thousandeyes_unit_id, report_formats, parent_output_dir, rtt_list):
        """Run a single test scenario"""
        try:
            success = True
            snmp_files = []
            
            # Extract RTT value from filename for naming
            rtt_suffix = ""
            rtt_dir_suffix = ""
            if rtt_file and rtt_file != 'default.json':
                import re
                rtt_match = re.search(r'(\d+)ms', rtt_file)
                if rtt_match:
                    rtt_suffix = f"_RTT_{rtt_match.group(1)}ms"
                    rtt_dir_suffix = f"RTT_{rtt_match.group(1)}ms"
            
            # Create subdirectory only if multiple RTT values
            test_output_dir = parent_output_dir
            if len(rtt_list) > 1 and rtt_dir_suffix:
                traffic_subdir = f"{self.traffic_type}_{rtt_dir_suffix}"
                test_output_dir = os.path.join(parent_output_dir, traffic_subdir)
                os.makedirs(test_output_dir, exist_ok=True)
            
            # Determine test name for SNMP collection
            test_name = scenario_name
            if byteblower_only:
                test_name = f"ByteBlower_{scenario_name}"
            elif iperf3_only:
                test_name = f"iPerf3_Linux_{scenario_name}"
            elif iperf3_darwin:
                test_name = f"iPerf3_macOS_{scenario_name}"
            elif packetstorm_only:
                test_name = f"PacketStorm_{scenario_name}"
            else:
                if client_ip:
                    test_name = f"iPerf3_Linux_{scenario_name}"
                else:
                    test_name = f"ByteBlower_{scenario_name}"
            
            if thousandeyes_only:
                self.logger.info(f"ThousandEyes mode - all tests (http_get_mt, http_post_mt, udp_jitter)")
                sk = ThousandEyesLogic(scenario_name, test_group_name, rtt_suffix, thousandeyes_unit_id)
                self.output_dir = test_output_dir
                success = True
                snmp_dir = test_output_dir

                for i in range(iterations):
                    self.run_snmp_collection(f"ThousandEyes_iteration_{i+1}", "before", snmp_dir, "")

                    self.start_cmts_collection(direction="downstream")
                    self.wait_for_cmts_poll()

                    test_start = time.time()
                    if not sk.run_downstream(i, iterations, test_output_dir):
                        self.logger.error("ThousandEyes downstream failed — stopping test")
                        self.stop_cmts_collection(snmp_dir, "ThousandEyes_DS")
                        return False, []

                    if not sk.run_upstream(i, iterations, test_output_dir):
                        self.logger.error("ThousandEyes upstream failed — stopping test")
                        self.stop_cmts_collection(snmp_dir, f"ThousandEyes_DS_iteration_{i+1}")
                        return False, []

                    sk.run_jitter(i, iterations, test_output_dir)

                    test_elapsed = time.time() - test_start
                    self.stop_cmts_collection(snmp_dir, f"ThousandEyes_DS_iteration_{i+1}", post_test_polls=2, test_duration_s=test_elapsed)

                    self.run_snmp_collection(f"ThousandEyes_iteration_{i+1}", "after", snmp_dir, "")
                    self._run_latency_report(snmp_dir, iteration=i+1, prefix="ThousandEyes")
            elif speedtest_only:
                self.logger.info(f"SpeedTest mode - clients: {speedtest_clients}")
                st = SpeedTestLogic(speedtest_clients, test_group_name)
                self.output_dir = test_output_dir
                if not st.run_iterations(iterations):
                    self.logger.error("SpeedTest failed — stopping test")
                    return False, []
                success = True
            elif packetstorm_only:
                self.logger.info(f"PacketStorm only mode - config: {rtt_file}")
                ps = PacketStormLogic(rtt_file)
                success = ps.start_config() and ps.stop_config()
            elif byteblower_only:
                bb = ByteBlowerLogic(bbp_file, scenario_name, scenario_name, test_group_name, rtt_suffix, report_formats)
                self.output_dir = test_output_dir
                success = True
                snmp_dir = os.path.join(test_output_dir, scenario_name + rtt_suffix)
                os.makedirs(snmp_dir, exist_ok=True)
                
                # Determine CMTS collection direction from scenario name
                cmts_dir = "upstream" if scenario_name.lower().startswith("us") else "downstream"
                
                for i in range(iterations):
                    iter_dir = os.path.join(snmp_dir, f"iteration_{i+1}") if iterations > 1 else snmp_dir
                    os.makedirs(iter_dir, exist_ok=True)
                    self.run_snmp_collection(f"{test_name}_iteration_{i+1}", "before", iter_dir, "")
                    self.start_cmts_collection(direction=cmts_dir)
                    self.wait_for_cmts_poll()
                    test_start = time.time()
                    if not bb.run_scenario(i, iterations, test_output_dir):
                        self.logger.error("ByteBlower failed — stopping test")
                        self.stop_cmts_collection(iter_dir, scenario_name)
                        return False, []
                    test_elapsed = time.time() - test_start
                    self.stop_cmts_collection(iter_dir, f"{scenario_name}_iteration_{i+1}", test_duration_s=test_elapsed)
                    self.run_snmp_collection(f"{test_name}_iteration_{i+1}", "after", iter_dir, "")
                    self._run_latency_report(iter_dir, iteration=i+1)
            elif iperf3_only or iperf3_darwin:
                platform_override = 'macos' if iperf3_darwin else None
                platform_suffix = "_macOS" if iperf3_darwin else "_Linux"
                self.logger.info(f"iPerf3 only mode - client: {client_ip}, scenario: {scenario_name}")
                iperf3 = IPerf3Logic(client_ip, scenario_name, test_group_name, rtt_suffix, output_format, platform_override, test_output_dir)
                self.output_dir = test_output_dir
                
                # Setup SSH and servers once
                if not iperf3.setup_ssh_keys():
                    self.logger.error("SSH key setup failed")
                    return False, []
                if not iperf3.setup_iperf3_servers():
                    self.logger.error("iPerf3 server setup failed")
                    return False, []
                
                success = True
                snmp_dir = os.path.join(test_output_dir, scenario_name + platform_suffix + rtt_suffix)
                os.makedirs(snmp_dir, exist_ok=True)
                
                # Determine CMTS collection direction from scenario name
                cmts_dir = "upstream" if scenario_name.lower().startswith("us") else "downstream"
                
                for i in range(iterations):
                    self.run_snmp_collection(f"{test_name}_iteration_{i+1}", "before", snmp_dir, "")
                    self.start_cmts_collection(direction=cmts_dir)
                    self.wait_for_cmts_poll()
                    test_start = time.time()
                    if not iperf3.run_scenario(i, iterations):
                        self.logger.error("iPerf3 failed — stopping test")
                        self.stop_cmts_collection(snmp_dir, scenario_name)
                        iperf3.stop_iperf3_servers()
                        return False, []
                    test_elapsed = time.time() - test_start
                    self.stop_cmts_collection(snmp_dir, f"{scenario_name}_iteration_{i+1}", test_duration_s=test_elapsed)
                    self.run_snmp_collection(f"{test_name}_iteration_{i+1}", "after", snmp_dir, "")
                    self._run_latency_report(snmp_dir, iteration=i+1)
                iperf3.stop_iperf3_servers()
            else:
                ps = PacketStormLogic(rtt_file)
                
                if client_ip:
                    iperf3 = IPerf3Logic(client_ip, scenario_name, test_group_name, rtt_suffix, output_format, None, test_output_dir)
                    self.output_dir = test_output_dir
                    
                    success = ps.start_config()
                    if success:
                        # Setup SSH and servers once
                        if not iperf3.setup_ssh_keys():
                            self.logger.error("SSH key setup failed")
                            ps.stop_config()
                            return False, []
                        if not iperf3.setup_iperf3_servers():
                            self.logger.error("iPerf3 server setup failed")
                            ps.stop_config()
                            return False, []
                        
                        snmp_dir = os.path.join(test_output_dir, scenario_name + rtt_suffix)
                        os.makedirs(snmp_dir, exist_ok=True)
                        
                        cmts_dir = "upstream" if scenario_name.lower().startswith("us") else "downstream"
                        
                        for i in range(iterations):
                            self.run_snmp_collection(f"{test_name}_iteration_{i+1}", "before", snmp_dir, "")
                            self.start_cmts_collection(direction=cmts_dir)
                            self.wait_for_cmts_poll()
                            test_start = time.time()
                            if not iperf3.run_scenario(i, iterations):
                                self.logger.error("iPerf3 failed — stopping test")
                                self.stop_cmts_collection(snmp_dir, scenario_name)
                                iperf3.stop_iperf3_servers()
                                ps.stop_config()
                                return False, []
                            test_elapsed = time.time() - test_start
                            self.stop_cmts_collection(snmp_dir, f"{scenario_name}_iteration_{i+1}", test_duration_s=test_elapsed)
                            self.run_snmp_collection(f"{test_name}_iteration_{i+1}", "after", snmp_dir, "")
                            self._run_latency_report(snmp_dir, iteration=i+1)
                        iperf3.stop_iperf3_servers()
                        success = success and ps.stop_config()
                else:
                    bb = ByteBlowerLogic(bbp_file, scenario_name, scenario_name, test_group_name, rtt_suffix, report_formats)
                    self.output_dir = test_output_dir
                    
                    success = ps.start_config()
                    if success:
                        snmp_dir = os.path.join(test_output_dir, scenario_name + rtt_suffix)
                        os.makedirs(snmp_dir, exist_ok=True)
                        
                        cmts_dir = "upstream" if scenario_name.lower().startswith("us") else "downstream"
                        
                        for i in range(iterations):
                            self.run_snmp_collection(f"{test_name}_iteration_{i+1}", "before", snmp_dir, "")
                            self.start_cmts_collection(direction=cmts_dir)
                            self.wait_for_cmts_poll()
                            test_start = time.time()
                            if not bb.run_scenario(i, iterations, test_output_dir):
                                self.logger.error("ByteBlower failed — stopping test")
                                self.stop_cmts_collection(snmp_dir, scenario_name)
                                ps.stop_config()
                                return False, []
                            test_elapsed = time.time() - test_start
                            self.stop_cmts_collection(snmp_dir, f"{scenario_name}_iteration_{i+1}", test_duration_s=test_elapsed)
                            self.run_snmp_collection(f"{test_name}_iteration_{i+1}", "after", snmp_dir, "")
                            self._run_latency_report(snmp_dir, iteration=i+1)
                        success = success and ps.stop_config()
            
            # Collect SNMP files from scenario directory
            if iperf3_only or iperf3_darwin:
                platform_suffix = "_macOS" if iperf3_darwin else "_Linux"
                scenario_snmp_dir = os.path.join(test_output_dir, scenario_name + platform_suffix + rtt_suffix)
            else:
                scenario_snmp_dir = os.path.join(test_output_dir, scenario_name + rtt_suffix)
            scenario_snmp_files = glob.glob(os.path.join(scenario_snmp_dir, "*_SNMP_*.txt"))
            
            snmp_files = scenario_snmp_files if scenario_snmp_files else glob.glob(os.path.join(test_output_dir, "*_SNMP_*.txt"))
            
            return success, snmp_files
                
        except Exception as e:
            self.logger.error(f"Single test failed: {e}")
            return False, []
    
    def _run_latency_report(self, snmp_dir, iteration=None, prefix=None):
        """Generate latency bin report from SNMP before/after files"""
        try:
            if iteration is not None:
                # Find before/after files for this specific iteration
                if prefix:
                    before_files = sorted(glob.glob(os.path.join(snmp_dir, f"*{prefix}_iteration_{iteration}_SNMP_before_*.txt")))
                    after_files = sorted(glob.glob(os.path.join(snmp_dir, f"*{prefix}_iteration_{iteration}_SNMP_after_*.txt")))
                else:
                    before_files = sorted(glob.glob(os.path.join(snmp_dir, f"*_iteration_{iteration}_SNMP_before_*.txt")))
                    after_files = sorted(glob.glob(os.path.join(snmp_dir, f"*_iteration_{iteration}_SNMP_after_*.txt")))
                before_file = before_files[-1] if before_files else None
                after_file = after_files[-1] if after_files else None
            else:
                before_file, after_file = find_snmp_files(snmp_dir)
            if before_file and after_file:
                # Build output filename with iteration
                output_dir = os.path.dirname(after_file) or "."
                dir_name = os.path.basename(os.path.abspath(output_dir))
                iter_tag = f"_iteration_{iteration}" if iteration else ""
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                # US report (from modem) — always generated
                us_output = os.path.join(output_dir, f"SNMP_US_Latency_Report_{dir_name}{iter_tag}_{timestamp}.xlsx")
                result = generate_latency_report(before_file, after_file, output_file=us_output, direction="US")
                if result:
                    self.logger.info(f"US Latency report: {os.path.basename(result)}")
                else:
                    self.logger.info("US Latency report skipped (no US latency OIDs)")
                # DS report (from iCMTS SNMP) — only for iCMTS mode
                if self.cmts_type == "icmts":
                    ds_output = os.path.join(output_dir, f"SNMP_DS_Latency_Report_{dir_name}{iter_tag}_{timestamp}.xlsx")
                    result_ds = generate_latency_report(before_file, after_file, output_file=ds_output, direction="DS")
                    if result_ds:
                        self.logger.info(f"DS Latency report (iCMTS SNMP): {os.path.basename(result_ds)}")
                    else:
                        self.logger.info("DS Latency report skipped (no DS latency OIDs found)")
                else:
                    self.logger.info("DS latency via Kafka (vCMTS) — see CMTS_Latency_Report_*.xlsx")
            else:
                self.logger.warning("Latency report skipped (SNMP files not found)")
        except Exception as e:
            self.logger.error(f"Latency report failed: {e}")

    def _consolidate_snmp_to_excel(self, snmp_files, parent_dir, test_group_name):
        """Consolidate all SNMP files into Excel with separate sheets"""
        try:
            if not snmp_files:
                return
            
            # Create Excel with separate sheets if pandas available
            if HAS_PANDAS:
                try:
                    import openpyxl
                    wb = openpyxl.Workbook()
                    wb.remove(wb.active)
                    
                    for snmp_file in sorted(set(snmp_files)):
                        sheet_name = os.path.basename(snmp_file).replace('.txt', '').replace('_SNMP_', '_')[:31]
                        ws = wb.create_sheet(sheet_name)
                        with open(snmp_file, 'r') as f:
                            for r_idx, line in enumerate(f, 1):
                                ws.cell(row=r_idx, column=1, value=line.rstrip())
                    
                    excel_file = os.path.join(parent_dir, f"{test_group_name}_SNMP_Combined_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
                    wb.save(excel_file)
                    self.logger.info(f"Combined SNMP Excel: {os.path.basename(excel_file)}")
                except Exception as e:
                    self.logger.warning(f"Excel creation skipped: {e}")
        except Exception as e:
            self.logger.error(f"Error consolidating SNMP: {e}")

def main():
    parser = argparse.ArgumentParser(description='ByteBlower, PacketStorm, iPerf3, and SpeedTest CLI Tool')
    # Required: CMTS type must be specified first
    parser.add_argument('--cmts-type', choices=['vcmts', 'icmts'], required=True, help='CMTS type: vcmts (Kafka for DS latency) or icmts (SNMP for DS latency)')
    # Traffic generation mode
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
    parser.add_argument('-speedtest', action='store_true', help='Enable SpeedTest mode')
    parser.add_argument('--client', default='linux,macos,nvidia', help='SpeedTest clients: linux,macos,nvidia (default: all)')
    parser.add_argument('-thousandeyes', action='store_true', help='Enable ThousandEyes instant-test mode')
    parser.add_argument('--unit-id', default=None, help='ThousandEyes unit ID (overrides config.yaml)')
    parser.add_argument('--report-formats', default='html pdf csv xls xlsx json docx', help='ByteBlower report formats (default: all formats)')
    parser.add_argument('-iteration', type=int, default=1, help='Number of iterations (default: 1)')
    
    args = parser.parse_args()
    
    if not args.byteblower and not args.packetstorm and not args.iperf3 and not getattr(args, 'iperf3_darwin', False) and not getattr(args, 'speedtest', False) and not getattr(args, 'thousandeyes', False):
        parser.error("At least one of -byteblower, -packetstorm, -iperf3, -iperf3-darwin, -speedtest, or -thousandeyes is required")
    
    if (args.iperf3 or getattr(args, 'iperf3_darwin', False)) and (not args.scenario or not args.clientIP):
        parser.error("Both --scenario and --clientIP are required when using -iperf3 or -iperf3-darwin")
    
    if getattr(args, 'thousandeyes', False) and not getattr(args, 'unit_id', None):
        parser.error("--unit-id is required when using -thousandeyes (e.g., --unit-id 82670821)")

    if args.packetstorm and not args.rtt:
        parser.error("--rtt is required when using -packetstorm")
    
    bb_file = args.bbp or 'default.bbp'
    speedtest_clients = [c.strip() for c in args.client.split(',')] if getattr(args, 'speedtest', False) else None
    
    tool = NetperfCLI(cmts_type=args.cmts_type)
    return tool.execute(
        bb_file, 
        args.rtt or 'default.json', 
        args.iteration,
        args.scenario or 'default',
        getattr(args, 'test_group_name', None),
        getattr(args, 'clientIP', None),
        getattr(args, 'output', 'json'),
        byteblower_only=args.byteblower and not args.packetstorm and not args.iperf3 and not getattr(args, 'speedtest', False) and not getattr(args, 'thousandeyes', False),
        packetstorm_only=args.packetstorm and not args.byteblower and not args.iperf3 and not getattr(args, 'speedtest', False) and not getattr(args, 'thousandeyes', False),
        iperf3_only=args.iperf3 and not args.byteblower and not args.packetstorm and not getattr(args, 'iperf3_darwin', False) and not getattr(args, 'speedtest', False) and not getattr(args, 'thousandeyes', False),
        iperf3_darwin=getattr(args, 'iperf3_darwin', False) and not getattr(args, 'speedtest', False) and not getattr(args, 'thousandeyes', False),
        speedtest_only=getattr(args, 'speedtest', False) and not getattr(args, 'thousandeyes', False),
        speedtest_clients=speedtest_clients,
        thousandeyes_only=getattr(args, 'thousandeyes', False),
        thousandeyes_unit_id=getattr(args, 'unit_id', None),
        report_formats=getattr(args, 'report_formats', 'html pdf csv xls xlsx json docx')
    )

if __name__ == '__main__':
    sys.exit(main())
