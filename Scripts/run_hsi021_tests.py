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
    # Baseline tests - RTT_0 only (no PacketStorm latency injection)
    baseline_commands = [
        # US_Classic_Only - RTT_0
        "python3 ../lld_test.py -byteblower --bbp ../bb_flows/HSI021_P20_vcmts_cm74375fd62c28.bbp --scenario US_Classic_Only -test-group-name HSI021",
        
        # DS_Classic_Only
        "python3 ../lld_test.py -byteblower --bbp ../bb_flows/HSI021_P20_vcmts_cm74375fd62c28.bbp --scenario DS_Classic_Only -test-group-name HSI021",
        
        # US_Combined
        "python3 ../lld_test.py -byteblower --bbp ../bb_flows/HSI021_P20_vcmts_cm74375fd62c28.bbp --scenario US_Combined -test-group-name HSI021",
        
        # DS_Combined
        "python3 ../lld_test.py -byteblower --bbp ../bb_flows/HSI021_P20_vcmts_cm74375fd62c28.bbp --scenario DS_Combined -test-group-name HSI021",
        
        # US_LL_Only
        "python3 ../lld_test.py -byteblower --bbp ../bb_flows/HSI021_P20_vcmts_cm74375fd62c28.bbp --scenario US_LL_Only -test-group-name HSI021",
        
        # DS_LL_Only
        "python3 ../lld_test.py -byteblower --bbp ../bb_flows/HSI021_P20_vcmts_cm74375fd62c28.bbp --scenario DS_LL_Only -test-group-name HSI021"
    ]
    
    print("=" * 80)
    print("HSI029 BASELINE TEST SUITE")
    print("Running RTT_0 (Zero Latency) Tests Only")
    print("=" * 80)
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
    print("BASELINE TEST SUITE COMPLETE")
    print(f"Results: {success_count}/{len(baseline_commands)} tests successful")
    print("=" * 80)

if __name__ == "__main__":
    main()