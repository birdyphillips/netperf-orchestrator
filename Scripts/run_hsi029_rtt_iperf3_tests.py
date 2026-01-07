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
    client_ip = "96.37.176.26"
    
    commands = [
        # US_Classic_Only
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario US_Classic_Only -test-group-name HSI029_RTT_0",
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario US_Classic_Only -test-group-name HSI029_RTT_10 -packetstorm --rtt vcmts10ms.json -iteration 1",
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario US_Classic_Only -test-group-name HSI029_RTT_20 -packetstorm --rtt vcmts20ms.json -iteration 1",
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario US_Classic_Only -test-group-name HSI029_RTT_30 -packetstorm --rtt vcmts30ms.json -iteration 1",
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario US_Classic_Only -test-group-name HSI029_RTT_40 -packetstorm --rtt vcmts40ms.json -iteration 1",
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario US_Classic_Only -test-group-name HSI029_RTT_50 -packetstorm --rtt vcmts50ms.json -iteration 1",
        
        # DS_Classic_Only
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario DS_Classic_Only -test-group-name HSI029_RTT_0",
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario DS_Classic_Only -test-group-name HSI029_RTT_10 -packetstorm --rtt vcmts10ms.json -iteration 1",
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario DS_Classic_Only -test-group-name HSI029_RTT_20 -packetstorm --rtt vcmts20ms.json -iteration 1",
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario DS_Classic_Only -test-group-name HSI029_RTT_30 -packetstorm --rtt vcmts30ms.json -iteration 1",
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario DS_Classic_Only -test-group-name HSI029_RTT_40 -packetstorm --rtt vcmts40ms.json -iteration 1",
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario DS_Classic_Only -test-group-name HSI029_RTT_50 -packetstorm --rtt vcmts50ms.json -iteration 1",
        
        # US_Combined
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario US_Combined -test-group-name HSI029_RTT_0",
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario US_Combined -test-group-name HSI029_RTT_10 -packetstorm --rtt vcmts10ms.json -iteration 1",
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario US_Combined -test-group-name HSI029_RTT_20 -packetstorm --rtt vcmts20ms.json -iteration 1",
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario US_Combined -test-group-name HSI029_RTT_30 -packetstorm --rtt vcmts30ms.json -iteration 1",
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario US_Combined -test-group-name HSI029_RTT_40 -packetstorm --rtt vcmts40ms.json -iteration 1",
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario US_Combined -test-group-name HSI029_RTT_50 -packetstorm --rtt vcmts50ms.json -iteration 1",
        
        # DS_Combined
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario DS_Combined -test-group-name HSI029_RTT_0",
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario DS_Combined -test-group-name HSI029_RTT_10 -packetstorm --rtt vcmts10ms.json -iteration 1",
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario DS_Combined -test-group-name HSI029_RTT_20 -packetstorm --rtt vcmts20ms.json -iteration 1",
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario DS_Combined -test-group-name HSI029_RTT_30 -packetstorm --rtt vcmts30ms.json -iteration 1",
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario DS_Combined -test-group-name HSI029_RTT_40 -packetstorm --rtt vcmts40ms.json -iteration 1",
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario DS_Combined -test-group-name HSI029_RTT_50 -packetstorm --rtt vcmts50ms.json -iteration 1",
        
        # US_LL_Only
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario US_LL_Only -test-group-name HSI029_RTT_0",
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario US_LL_Only -test-group-name HSI029_RTT_10 -packetstorm --rtt vcmts10ms.json -iteration 1",
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario US_LL_Only -test-group-name HSI029_RTT_20 -packetstorm --rtt vcmts20ms.json -iteration 1",
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario US_LL_Only -test-group-name HSI029_RTT_30 -packetstorm --rtt vcmts30ms.json -iteration 1",
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario US_LL_Only -test-group-name HSI029_RTT_40 -packetstorm --rtt vcmts40ms.json -iteration 1",
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario US_LL_Only -test-group-name HSI029_RTT_50 -packetstorm --rtt vcmts50ms.json -iteration 1",
        
        # DS_LL_Only
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario DS_LL_Only -test-group-name HSI029_RTT_0",
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario DS_LL_Only -test-group-name HSI029_RTT_10 -packetstorm --rtt vcmts10ms.json -iteration 1",
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario DS_LL_Only -test-group-name HSI029_RTT_20 -packetstorm --rtt vcmts20ms.json -iteration 1",
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario DS_LL_Only -test-group-name HSI029_RTT_30 -packetstorm --rtt vcmts30ms.json -iteration 1",
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario DS_LL_Only -test-group-name HSI029_RTT_40 -packetstorm --rtt vcmts40ms.json -iteration 1",
        f"python3 ../lld_test.py -iperf3 --clientIP {client_ip} --scenario DS_LL_Only -test-group-name HSI029_RTT_50 -packetstorm --rtt vcmts50ms.json -iteration 1"
    ]
    
    print(f"Starting execution of {len(commands)} iPerf3 test commands...")
    print(f"Client IP: {client_ip}")
    print(f"Total estimated time: {len(commands) * 15 / 60:.1f} minutes (excluding test execution time)")
    print("=" * 80)
    
    for i, cmd in enumerate(commands, 1):
        print(f"[{i}/{len(commands)}]")
        success = run_command(cmd)
        
        if not success:
            print(f"Test failed. Continuing to next test...")
        
        if i < len(commands):
            print(f"Waiting 15 seconds before next command...")
            time.sleep(15)
    
    print("All iPerf3 tests completed!")

if __name__ == "__main__":
    main()