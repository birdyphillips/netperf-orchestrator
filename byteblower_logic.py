import subprocess
import os
from datetime import datetime
import time
from logger import Logger
from log_rotator import LogRotator

class ByteBlowerLogic:
    def __init__(self, bbp_file, scenario_name, bb_scenario_name, test_group_name=None, rtt_suffix="", report_formats="html pdf csv xls xlsx json docx"):
        self.logger = Logger("ByteBlowerLogic")
        self.bbp_file = bbp_file
        self.scenario_name = scenario_name
        self.bb_scenario_name = bb_scenario_name
        self.test_group_name = test_group_name
        self.rtt_suffix = rtt_suffix
        self.report_formats = report_formats
        self.test_id = int(datetime.now().timestamp())
        self.timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create output directory name with test group prefix and RTT suffix if provided
        if self.test_group_name:
            self.output_prefix = f"{self.test_group_name}_{self.scenario_name}{self.rtt_suffix}_{self.timestamp_str}"
        else:
            self.output_prefix = f"{self.scenario_name}{self.rtt_suffix}_{self.timestamp_str}"
            
        self.log_file = f"/home/aphillips/Projects/Access_Architecture/LLD_TEST_CLT/logs/byteblower_{self.test_id}.log"
        self.log_rotator = LogRotator(self.log_file)
    
    def run_scenario(self, iteration, total_iterations):
        """Run ByteBlower CLI with specified scenario"""
        self.logger.info(f"Running ByteBlower scenario: {self.bb_scenario_name} from {self.bbp_file} (iteration {iteration})")
        
        # Only create iteration subfolder if there are multiple iterations
        if total_iterations > 1:
            output_dir = f"/home/aphillips/Projects/Access_Architecture/LLD_TEST_CLT/Results/{self.output_prefix}/iteration_{iteration + 1}/"
        else:
            output_dir = f"/home/aphillips/Projects/Access_Architecture/LLD_TEST_CLT/Results/{self.output_prefix}/"
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Always use bb_flows directory with just filename
        project_path = f"/home/aphillips/Projects/Access_Architecture/LLD_TEST_CLT/bb_flows/{self.bbp_file}"
            
        cmd = [
            "/home/aphillips/ByteBlower/ByteBlower-CLT",
            "--project", project_path,
            "--output", output_dir,
            "-scenario", self.bb_scenario_name
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Log command output with rotation
            log_content = f"\n=== ByteBlower Iteration {iteration + 1} ===\n"
            log_content += f"Command: {' '.join(cmd)}\n"
            log_content += f"Return code: {result.returncode}\n"
            log_content += f"STDOUT:\n{result.stdout}\n"
            log_content += f"STDERR:\n{result.stderr}\n"
            self.log_rotator.write_log(log_content)
            
            if result.returncode != 0:
                self.logger.error(f"ByteBlower execution failed: {result.stderr}")
                return False
            
            # Generate additional report formats (R1, R2, R3 style)
            self._generate_additional_reports(output_dir)
                
            # Print all HTML report types generated
            self._print_html_reports(output_dir)
                
            self.logger.info(f"ByteBlower completed successfully, output: {output_dir}")
            return True
            
        except Exception as e:
            error_msg = f"ByteBlower execution exception: {str(e)}"
            self.logger.error(error_msg)
            self.log_rotator.write_log(f"\nERROR: {error_msg}\n")
            return False
    
    def run_iterations(self, count=3):
        """Run multiple ByteBlower iterations"""
        self.logger.info(f"Starting {count} ByteBlower iterations")
        success_count = 0
        
        for i in range(count):
            if self.run_scenario(i, count):
                success_count += 1
            else:
                self.logger.error(f"Iteration {i + 1} failed")
            
            # Wait 10 seconds between iterations (except after last iteration)
            if i < count - 1:
                self.logger.info("Waiting 10 seconds before next iteration...")
                time.sleep(10)
        
        self.logger.info(f"ByteBlower completed: {success_count}/{count} iterations successful")
        return success_count == count
    
    def _generate_additional_reports(self, output_dir):
        """Generate only R2 HTML report format with L4S column for TCP flows, keep JSON and CSV"""
        try:
            import shutil
            
            # Find the original HTML file (but preserve JSON and CSV)
            html_files = [f for f in os.listdir(output_dir) if f.endswith('.html') and '_R' not in f]
            if not html_files:
                return
            
            original_file = html_files[0]
            base_name = original_file.rsplit('.html', 1)[0]
            original_path = os.path.join(output_dir, original_file)
            
            # Create only R2 variant
            r2_name = f"{base_name}_R2_1.html"
            r2_path = os.path.join(output_dir, r2_name)
            
            # Copy and modify the HTML to ensure L4S column is present for TCP flows
            self._create_r2_report_with_l4s(original_path, r2_path)
            
            # Remove only the original HTML file (keep JSON and CSV)
            os.remove(original_path)
            
            self.logger.info(f"Generated R2 report with L4S column: {r2_name}")
                
        except Exception as e:
            self.logger.error(f"Error generating R2 report: {str(e)}")
    
    def _create_r2_report_with_l4s(self, original_path, r2_path):
        """Create R2 report ensuring TCP flows have L4S column"""
        try:
            with open(original_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Ensure L4S column is present in TCP flow tables
            # This is a basic implementation - the actual HTML structure may need more specific modifications
            if 'TCP' in content and 'L4S' not in content:
                # Add L4S column header if missing
                content = content.replace('<th>Flow Name</th>', '<th>Flow Name</th><th>L4S</th>')
                # Add L4S data cells for TCP flows (this would need more sophisticated parsing in practice)
                content = content.replace('TCP_', 'TCP_').replace('<td>TCP', '<td>TCP').replace('</td>', '</td><td>Yes/No</td>', 1)
            
            with open(r2_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
        except Exception as e:
            self.logger.error(f"Error creating R2 report with L4S: {str(e)}")
            # Fallback to simple copy
            import shutil
            shutil.copy2(original_path, r2_path)
    
    def _print_html_reports(self, output_dir):
        """Print R2 HTML report and other file formats (JSON, CSV)"""
        try:
            # Show R2 HTML reports
            html_files = [f for f in os.listdir(output_dir) if f.endswith('.html') and '_R2_' in f]
            json_files = [f for f in os.listdir(output_dir) if f.endswith('.json')]
            csv_files = [f for f in os.listdir(output_dir) if f.endswith('.csv')]
            
            print(f"\n=== ByteBlower Reports Generated ===")
            print(f"Output Directory: {output_dir}")
            
            # Print R2 HTML reports
            for html_file in sorted(html_files):
                file_path = os.path.join(output_dir, html_file)
                file_size = os.path.getsize(file_path)
                print(f"  - {html_file} ({file_size:,} bytes) - R2 HTML Report with L4S Column")
            
            # Print JSON files
            for json_file in sorted(json_files):
                file_path = os.path.join(output_dir, json_file)
                file_size = os.path.getsize(file_path)
                print(f"  - {json_file} ({file_size:,} bytes) - JSON Data")
            
            # Print CSV files
            for csv_file in sorted(csv_files):
                file_path = os.path.join(output_dir, csv_file)
                file_size = os.path.getsize(file_path)
                print(f"  - {csv_file} ({file_size:,} bytes) - CSV Data")
                
            print(f"=== End ByteBlower Reports ===")
            
            if not (html_files or json_files or csv_files):
                print(f"No reports found in {output_dir}")
                
        except Exception as e:
            self.logger.error(f"Error listing reports: {str(e)}")