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
    commands = [
        # US_Classic_Only
        "python3 ../lld_test.py -byteblower --bbp ../bb_flows/HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario US_Classic_Only -test-group-name HSI018_RTT_0",
        "python3 ../lld_test.py -byteblower --bbp HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario US_Classic_Only -test-group-name HSI018_RTT_10 -packetstorm --rtt vcmts10ms.json -iteration 1",
        "python3 ../lld_test.py -byteblower --bbp HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario US_Classic_Only -test-group-name HSI018_RTT_20 -packetstorm --rtt vcmts20ms.json -iteration 1",
        "python3 ../lld_test.py -byteblower --bbp HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario US_Classic_Only -test-group-name HSI018_RTT_30 -packetstorm --rtt vcmts30ms.json -iteration 1",
        "python3 ../lld_test.py -byteblower --bbp HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario US_Classic_Only -test-group-name HSI018_RTT_40 -packetstorm --rtt vcmts40ms.json -iteration 1",
        "python3 ../lld_test.py -byteblower --bbp HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario US_Classic_Only -test-group-name HSI018_RTT_50 -packetstorm --rtt vcmts50ms.json -iteration 1",
        
        # DS_Classic_Only
        "python3 ../lld_test.py -byteblower --bbp ../bb_flows/HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario DS_Classic_Only -test-group-name HSI018_RTT_0",
        "python3 ../lld_test.py -byteblower --bbp HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario DS_Classic_Only -test-group-name HSI018_RTT_10 -packetstorm --rtt vcmts10ms.json -iteration 1",
        "python3 ../lld_test.py -byteblower --bbp HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario DS_Classic_Only -test-group-name HSI018_RTT_20 -packetstorm --rtt vcmts20ms.json -iteration 1",
        "python3 ../lld_test.py -byteblower --bbp HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario DS_Classic_Only -test-group-name HSI018_RTT_30 -packetstorm --rtt vcmts30ms.json -iteration 1",
        "python3 ../lld_test.py -byteblower --bbp HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario DS_Classic_Only -test-group-name HSI018_RTT_40 -packetstorm --rtt vcmts40ms.json -iteration 1",
        "python3 ../lld_test.py -byteblower --bbp HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario DS_Classic_Only -test-group-name HSI018_RTT_50 -packetstorm --rtt vcmts50ms.json -iteration 1",
        
        # US_Combined
        "python3 ../lld_test.py -byteblower --bbp ../bb_flows/HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario US_Combined -test-group-name HSI018_RTT_0",
        "python3 ../lld_test.py -byteblower --bbp HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario US_Combined -test-group-name HSI018_RTT_10 -packetstorm --rtt vcmts10ms.json -iteration 1",
        "python3 ../lld_test.py -byteblower --bbp HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario US_Combined -test-group-name HSI018_RTT_20 -packetstorm --rtt vcmts20ms.json -iteration 1",
        "python3 ../lld_test.py -byteblower --bbp HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario US_Combined -test-group-name HSI018_RTT_30 -packetstorm --rtt vcmts30ms.json -iteration 1",
        "python3 ../lld_test.py -byteblower --bbp HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario US_Combined -test-group-name HSI018_RTT_40 -packetstorm --rtt vcmts40ms.json -iteration 1",
        "python3 ../lld_test.py -byteblower --bbp HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario US_Combined -test-group-name HSI018_RTT_50 -packetstorm --rtt vcmts50ms.json -iteration 1",
        
        # DS_Combined
        "python3 ../lld_test.py -byteblower --bbp ../bb_flows/HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario DS_Combined -test-group-name HSI018_RTT_0",
        "python3 ../lld_test.py -byteblower --bbp HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario DS_Combined -test-group-name HSI018_RTT_10 -packetstorm --rtt vcmts10ms.json -iteration 1",
        "python3 ../lld_test.py -byteblower --bbp HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario DS_Combined -test-group-name HSI018_RTT_20 -packetstorm --rtt vcmts20ms.json -iteration 1",
        "python3 ../lld_test.py -byteblower --bbp HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario DS_Combined -test-group-name HSI018_RTT_30 -packetstorm --rtt vcmts30ms.json -iteration 1",
        "python3 ../lld_test.py -byteblower --bbp HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario DS_Combined -test-group-name HSI018_RTT_40 -packetstorm --rtt vcmts40ms.json -iteration 1",
        "python3 ../lld_test.py -byteblower --bbp HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario DS_Combined -test-group-name HSI018_RTT_50 -packetstorm --rtt vcmts50ms.json -iteration 1",
        
        # DS_LL_Only
        "python3 ../lld_test.py -byteblower --bbp ../bb_flows/HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario DS_LL_Only -test-group-name HSI018_RTT_0",
        "python3 ../lld_test.py -byteblower --bbp HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario DS_LL_Only -test-group-name HSI018_RTT_10 -packetstorm --rtt vcmts10ms.json -iteration 1",
        "python3 ../lld_test.py -byteblower --bbp HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario DS_LL_Only -test-group-name HSI018_RTT_20 -packetstorm --rtt vcmts20ms.json -iteration 1",
        "python3 ../lld_test.py -byteblower --bbp HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario DS_LL_Only -test-group-name HSI018_RTT_30 -packetstorm --rtt vcmts30ms.json -iteration 1",
        "python3 ../lld_test.py -byteblower --bbp HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario DS_LL_Only -test-group-name HSI018_RTT_40 -packetstorm --rtt vcmts40ms.json -iteration 1",
        "python3 ../lld_test.py -byteblower --bbp HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario DS_LL_Only -test-group-name HSI018_RTT_50 -packetstorm --rtt vcmts50ms.json -iteration 1",
        
        # US_LL_Only
        "python3 ../lld_test.py -byteblower --bbp ../bb_flows/HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario US_LL_Only -test-group-name HSI018_RTT_0",
        "python3 ../lld_test.py -byteblower --bbp HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario US_LL_Only -test-group-name HSI018_RTT_10 -packetstorm --rtt vcmts10ms.json -iteration 1",
        "python3 ../lld_test.py -byteblower --bbp HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario US_LL_Only -test-group-name HSI018_RTT_20 -packetstorm --rtt vcmts20ms.json -iteration 1",
        "python3 ../lld_test.py -byteblower --bbp HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario US_LL_Only -test-group-name HSI018_RTT_30 -packetstorm --rtt vcmts30ms.json -iteration 1",
        "python3 ../lld_test.py -byteblower --bbp HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario US_LL_Only -test-group-name HSI018_RTT_40 -packetstorm --rtt vcmts40ms.json -iteration 1",
        "python3 ../lld_test.py -byteblower --bbp HSI018_P20_vcmts_cm0cb937643ab0.bbp --scenario US_LL_Only -test-group-name HSI018_RTT_50 -packetstorm --rtt vcmts50ms.json -iteration 1"
    ]
    
    print(f"Starting execution of {len(commands)} test commands...")
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
    
    print("All tests completed!")

if __name__ == "__main__":
    main()