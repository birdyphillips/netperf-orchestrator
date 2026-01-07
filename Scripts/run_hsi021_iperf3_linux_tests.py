#!/usr/bin/env python3
import subprocess
import time
import os

def run_command(cmd):
    print(f"Executing: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, cwd='/home/aphillips/Projects/Access_Architecture/LLD_TEST_CLT/Scripts')
        print(f"✓ Command completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Command failed with exit code {e.returncode}")
        return False
    finally:
        print("-" * 80)

def main():
    # Change this IP to your Linux client IP
    client_ip = "96.37.176.3"
    
    # Baseline tests - RTT_0 only (no PacketStorm latency injection)
    baseline_commands = [
        # US_Classic_Only - RTT_0
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario US_Classic_Only -test-group-name HSI021",
        
        # DS_Classic_Only
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario DS_Classic_Only -test-group-name HSI021",
        
        # US_Combined
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario US_Combined -test-group-name HSI021",
        
        # DS_Combined
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario DS_Combined -test-group-name HSI021",
        
        # US_LL_Only
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario US_LL_Only -test-group-name HSI021",
        
        # DS_LL_Only
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario DS_LL_Only -test-group-name HSI021"
    ]
    
    print("=" * 80)
    print("HSI021 iPerf3 BASELINE TEST SUITE")
    print("Running RTT_0 (Zero Latency) Tests Only")
    print("=" * 80)
    print(f"Client IP: {client_ip}")
    print(f"Total baseline tests: {len(baseline_commands)}")
    print(f"Estimated time: {len(baseline_commands) * 10 / 60:.1f} minutes (excluding test execution time)")
    print("=" * 80)
    
    success_count = 0
    
    for i, cmd in enumerate(baseline_commands, 1):
        print(f"[BASELINE TEST {i}/{len(baseline_commands)}]")
        success = run_command(cmd)
        
        if success:
            success_count += 1
            print(f"✓ Baseline test {i} completed successfully")
        else:
            print(f"✗ Baseline test {i} failed. Continuing to next test...")
        
        if i < len(baseline_commands):
            print(f"Waiting 10 seconds before next baseline test...")
            time.sleep(10)
    
    print("=" * 80)
    print("HSI021 iPerf3 BASELINE TEST SUITE COMPLETE")
    print(f"Results: {success_count}/{len(baseline_commands)} tests successful")
    print("=" * 80)

if __name__ == "__main__":
    main()