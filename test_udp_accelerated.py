#!/usr/bin/env python3
"""Quick test script to run ThousandEyes UDP accelerated DL and UL tests."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from thousandeyes_logic import ThousandEyesLogic
from config_loader import config

unit_id = str(getattr(config, 'thousandeyes_unit_id', None) or '82670821')

print(f"\n  ThousandEyes UDP Accelerated Tests")
print(f"  Unit ID: {unit_id}")
print(f"  {'='*50}\n")

te = ThousandEyesLogic(
    scenario_name="udp_accelerated",
    test_group_name="UDP_Accelerated",
    unit_id=unit_id
)

output_dir = os.path.join("Results", f"UDP_Accelerated_{te.timestamp_str}")
os.makedirs(output_dir, exist_ok=True)

results = {}

print("  Running UDP Accelerated Download (udp_accelerated_dl)...")
dl = te._run_test("udp_accelerated_dl")
if dl:
    results["udp_accelerated_dl"] = dl
else:
    print("  [FAILED] udp_accelerated_dl")

print("\n  Running UDP Accelerated Upload (udp_accelerated_ul)...")
ul = te._run_test("udp_accelerated_ul")
if ul:
    results["udp_accelerated_ul"] = ul
else:
    print("  [FAILED] udp_accelerated_ul")

if results:
    te._save_results(output_dir, 0, results)
    print(f"\n  Results saved to: {output_dir}")
else:
    print("\n  No results to save.")

sys.exit(0 if len(results) == 2 else 1)
