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
    # Change this IP to your macOS client IP
    client_ip = "96.37.176.11"  # macOS client IP confirmed
    
    # macOS iPerf3 tests using iperf3-darwin with Apple QUIC and L4S
    macos_commands = [
        # US_Classic_Only
        f"python3 ../lld_test.py -iperf3-darwin --clientIP {client_ip} --scenario US_Classic_Only -test-group-name HSI018",
        
        # DS_Classic_Only
        f"python3 ../lld_test.py -iperf3-darwin --clientIP {client_ip} --scenario DS_Classic_Only -test-group-name HSI018",
        
        # US_Combined
        f"python3 ../lld_test.py -iperf3-darwin --clientIP {client_ip} --scenario US_Combined -test-group-name HSI018",
        
        # DS_Combined
        f"python3 ../lld_test.py -iperf3-darwin --clientIP {client_ip} --scenario DS_Combined -test-group-name HSI018",
        
        # US_LL_Only
        f"python3 ../lld_test.py -iperf3-darwin --clientIP {client_ip} --scenario US_LL_Only -test-group-name HSI018",
        
        # DS_LL_Only
        f"python3 ../lld_test.py -iperf3-darwin --clientIP {client_ip} --scenario DS_LL_Only -test-group-name HSI018"
    ]
    
    print("=" * 80)
    print("HSI018 macOS iPerf3 TEST SUITE")
    print("Using iperf3-darwin with Apple QUIC and L4S")
    print("=" * 80)
    print(f"macOS Client IP: {client_ip}")
    print(f"Total tests: {len(macos_commands)}")
    print(f"Estimated time: {len(macos_commands) * 10 / 60:.1f} minutes (excluding test execution time)")
    print("=" * 80)
    
    success_count = 0
    
    for i, cmd in enumerate(macos_commands, 1):
        print(f"[macOS TEST {i}/{len(macos_commands)}]")
        success = run_command(cmd)
        
        if success:
            success_count += 1
            print(f"✓ macOS test {i} completed successfully")
        else:
            print(f"✗ macOS test {i} failed. Continuing to next test...")
        
        if i < len(macos_commands):
            print(f"Waiting 10 seconds before next test...")
            time.sleep(10)
    
    print("=" * 80)
    print("HSI018 macOS iPerf3 TEST SUITE COMPLETE")
    print(f"Results: {success_count}/{len(macos_commands)} tests successful")
    print("=" * 80)

if __name__ == "__main__":
    main()