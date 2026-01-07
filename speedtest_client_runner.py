#!/usr/bin/env python3
import subprocess
import time
import os
import logging
from datetime import datetime

# Setup logging
def setup_logging():
    """Setup logging configuration"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = "/home/aphillips/Projects/Access_Architecture/LLD_TEST_CLT/logs"
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"speedtest_runner_{timestamp}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # Keep console logging to match original format
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Speedtest runner started - Log file: {log_file}")
    return logger

def run_ssh_command(host, username, password, command, description, logger):
    """Execute command on remote host via SSH"""
    logger.info(f"Executing on {host}: {description}")
    print(f"Executing on {host}: {description}")
    
    # Use sshpass for password authentication
    ssh_cmd = f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no {username}@{host} '{command}'"
    logger.debug(f"SSH Command: {ssh_cmd.replace(password, '***')}")
    print(f"  → SSH Command: {ssh_cmd.replace(password, '***')}")
    
    try:
        logger.info(f"Starting SSH execution with 30-second timeout...")
        print(f"  → Starting SSH execution with 30-second timeout...")
        
        result = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            logger.info(f"✓ {description} completed successfully")
            print(f"✓ {description} completed successfully")
            if result.stdout.strip():
                logger.debug(f"Command output: {result.stdout[:200]}...")  # Log first 200 chars
            return True, result.stdout
        else:
            logger.error(f"✗ {description} failed with return code {result.returncode}: {result.stderr}")
            print(f"✗ {description} failed: {result.stderr}")
            return False, result.stderr
    except subprocess.TimeoutExpired:
        logger.error(f"✗ {description} timed out after 30 seconds")
        print(f"✗ {description} timed out after 30 seconds")
        return False, "Command timed out"
    except Exception as e:
        logger.error(f"✗ {description} error: {str(e)}")
        print(f"✗ {description} error: {str(e)}")
        return False, str(e)

def copy_file_from_remote(host, username, password, remote_path, local_path, logger):
    """Copy file from remote host using scp"""
    logger.info(f"Copying {remote_path} from {host} to {local_path}")
    print(f"Copying {remote_path} from {host} to {local_path}")
    
    scp_cmd = f"sshpass -p '{password}' scp -o StrictHostKeyChecking=no {username}@{host}:{remote_path} {local_path}"
    logger.debug(f"SCP Command: {scp_cmd.replace(password, '***')}")
    print(f"  → SCP Command: {scp_cmd.replace(password, '***')}")
    
    try:
        result = subprocess.run(scp_cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"✓ File copied successfully")
            print(f"✓ File copied successfully")
            return True
        else:
            logger.error(f"✗ File copy failed: {result.stderr}")
            print(f"✗ File copy failed: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"✗ File copy error: {str(e)}")
        print(f"✗ File copy error: {str(e)}")
        return False

def run_speedtest_on_client(host, username, password, client_name, test_name, logger):
    """Run 3 iterations of speedtest on a client and retrieve results"""
    logger.info(f"Starting speedtest on {client_name} ({host})")
    print(f"\n{'='*60}")
    print(f"Running Speedtest on {client_name} ({host})")
    print(f"{'='*60}")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"{test_name}_{client_name}_Speedtest_{timestamp}.txt"
    
    logger.info(f"Output file will be: {output_file}")
    print(f"  → Output file: {output_file}")
    
    # Create output directory if it doesn't exist
    results_dir = "/home/aphillips/Projects/Access_Architecture/LLD_TEST_CLT/Results"
    os.makedirs(results_dir, exist_ok=True)
    logger.info(f"Results directory: {results_dir}")
    print(f"  → Results directory: {results_dir}")
    
    success_count = 0
    
    # Determine platform-specific commands
    is_windows = client_name.upper() == "NVIDIA"
    
    for iteration in range(1, 4):
        logger.info(f"Starting iteration {iteration}/3 for {client_name}")
        print(f"\n[ITERATION {iteration}/3]")
        
        if is_windows:
            # Windows commands using cmd syntax
            if iteration == 1:
                # First iteration - create new file
                speedtest_cmd = f'cd C:\\Users\\Administrator\\Desktop\\ookla-speedtest-1.2.0-win64 && echo === {test_name} Speedtest Results - {client_name} === > {output_file} && echo Timestamp: {timestamp} >> {output_file} && echo. >> {output_file}'
                logger.info(f"Creating new output file for iteration 1 (Windows)")
                print(f"  → Creating new output file for iteration 1 (Windows)")
            else:
                speedtest_cmd = f'cd C:\\Users\\Administrator\\Desktop\\ookla-speedtest-1.2.0-win64 && echo. >> {output_file}'
                logger.info(f"Appending to existing file for iteration {iteration} (Windows)")
                print(f"  → Appending to existing file for iteration {iteration} (Windows)")
            
            # Add iteration header and run speedtest (Windows)
            speedtest_cmd += f' && echo --- Iteration {iteration} --- >> {output_file} && speedtest.exe >> {output_file}'
        else:
            # Linux/macOS commands using bash syntax
            if iteration == 1:
                # First iteration - create new file
                speedtest_cmd = f'echo "=== {test_name} Speedtest Results - {client_name} ===" > {output_file} && echo "Timestamp: {timestamp}" >> {output_file} && echo "" >> {output_file}'
                logger.info(f"Creating new output file for iteration 1 (Unix)")
                print(f"  → Creating new output file for iteration 1 (Unix)")
            else:
                speedtest_cmd = f'echo "" >> {output_file}'
                logger.info(f"Appending to existing file for iteration {iteration} (Unix)")
                print(f"  → Appending to existing file for iteration {iteration} (Unix)")
            
            # Add iteration header and run speedtest (Linux/macOS)
            if client_name.upper() == "MACOS":
                speedtest_cmd += f' && echo "--- Iteration {iteration} ---" >> {output_file} && /opt/homebrew/bin/speedtest >> {output_file}'
            else:
                speedtest_cmd += f' && echo "--- Iteration {iteration} ---" >> {output_file} && speedtest >> {output_file}'
        
        logger.debug(f"Full speedtest command: {speedtest_cmd}")
        print(f"  → Running: speedtest (iteration {iteration})")
        
        success, output = run_ssh_command(host, username, password, speedtest_cmd, f"Speedtest iteration {iteration}", logger)
        
        if success:
            success_count += 1
            logger.info(f"Iteration {iteration} completed successfully")
            print(f"✓ Iteration {iteration} completed")
        else:
            logger.error(f"Iteration {iteration} failed")
            print(f"✗ Iteration {iteration} failed")
        
        # Wait between iterations
        if iteration < 3:
            logger.info(f"Waiting 10 seconds before iteration {iteration + 1}")
            print("  → Waiting 10 seconds before next iteration...")
            time.sleep(10)
    
    # Copy results file to local machine
    if success_count > 0:
        logger.info(f"Attempting to copy results file from {client_name}")
        print(f"\n  → Copying results file from {client_name}...")
        
        local_file_path = os.path.join(results_dir, output_file)
        
        if is_windows:
            # Windows file path for scp
            remote_file_path = f"C:/Users/Administrator/Desktop/ookla-speedtest-1.2.0-win64/{output_file}"
        else:
            remote_file_path = output_file
        
        copy_success = copy_file_from_remote(host, username, password, remote_file_path, local_file_path, logger)
        
        if copy_success:
            # Skip cleanup - keep results file on remote client
            logger.info(f"Results file kept on remote client: {output_file}")
            print(f"  → Results file kept on remote client: {output_file}")
            
            logger.info(f"Speedtest results saved to: {local_file_path}")
            print(f"\n✓ Speedtest results saved to: {local_file_path}")
        else:
            logger.error(f"Failed to retrieve results file from {client_name}")
            print(f"\n✗ Failed to retrieve results file")
    else:
        logger.warning(f"No successful iterations for {client_name}, skipping file copy")
        print(f"\n⚠ No successful iterations, skipping file copy")
    
    logger.info(f"{client_name} speedtest summary: {success_count}/3 iterations successful")
    print(f"\n{client_name} Speedtest Summary: {success_count}/3 iterations successful")
    return success_count

def main():
    # Setup logging first
    logger = setup_logging()
    
    # Client configurations - UPDATE THESE IP ADDRESSES AS NEEDED
    clients = {
        "linux": {
            "host": "96.37.176.25",  # From HSI018 Linux tests
            "username": "lld",
            "password": "aqm@2024"  # Linux client password from iperf3_logic.py
        },
        "macos": {
            "host": "96.37.176.11",  # From HSI021 macOS tests  
            "username": "lld_mac_client",
            "password": "aqm@2022"  # macOS client password from iperf3_logic.py
        },
        "nvidia": {
            "host": "96.37.176.14",
            "username": "Administrator", 
            "password": "aqm@2022"
        }
    }
    
    # Test name - change this for different modem configurations
    test_name = "HSI018_Ookla_Speed_test"
    
    logger.info(f"Starting speedtest suite with test name: {test_name}")
    logger.info(f"Configured clients: {list(clients.keys())}")
    
    print("=" * 80)
    print("OOKLA SPEEDTEST CLIENT RUNNER")
    print("=" * 80)
    print(f"Test Name: {test_name}")
    print("Clients:")
    for name, config in clients.items():
        print(f"  - {name.upper()}: {config['username']}@{config['host']}")
        logger.info(f"Client {name.upper()}: {config['username']}@{config['host']}")
    print("=" * 80)
    
    # Check if sshpass is installed
    logger.info("Checking for sshpass installation")
    print("  → Checking for sshpass installation...")
    try:
        subprocess.run(["which", "sshpass"], check=True, capture_output=True)
        logger.info("sshpass found")
        print("  ✓ sshpass found")
    except subprocess.CalledProcessError:
        logger.error("sshpass not installed")
        print("ERROR: sshpass is not installed. Please install it:")
        print("  Ubuntu/Debian: sudo apt-get install sshpass")
        print("  CentOS/RHEL: sudo yum install sshpass")
        return
    
    total_success = 0
    total_tests = len(clients) * 3
    
    logger.info(f"Starting tests on {len(clients)} clients, {total_tests} total tests")
    print(f"\n  → Starting tests on {len(clients)} clients, {total_tests} total tests")
    
    # Run speedtest on each client
    for i, (client_name, config) in enumerate(clients.items(), 1):
        logger.info(f"Processing client {i}/{len(clients)}: {client_name.upper()}")
        print(f"\n[CLIENT {i}/{len(clients)}] Processing {client_name.upper()}...")
        
        success_count = run_speedtest_on_client(
            config["host"], 
            config["username"], 
            config["password"], 
            client_name.upper(), 
            test_name,
            logger
        )
        total_success += success_count
        
        logger.info(f"Client {client_name.upper()} completed: {success_count}/3 successful")
        
        # Wait between clients
        if i < len(clients):  # Not the last client
            logger.info(f"Waiting 15 seconds before next client")
            print(f"\n  → Waiting 15 seconds before next client...")
            time.sleep(15)
    
    logger.info(f"Speedtest suite completed: {total_success}/{total_tests} tests successful")
    print("\n" + "=" * 80)
    print("SPEEDTEST SUITE COMPLETE")
    print(f"Overall Results: {total_success}/{total_tests} tests successful")
    print(f"Results saved in: /home/aphillips/Projects/Access_Architecture/LLD_TEST_CLT/Results/")
    print("=" * 80)

if __name__ == "__main__":
    main()