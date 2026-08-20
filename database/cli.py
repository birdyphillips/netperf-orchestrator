#!/usr/bin/env python3
"""CLI to manage the DELTA MySQL database.

Usage:
    python -m database.cli init          # Create tables
    python -m database.cli ingest        # Ingest all Results/
    python -m database.cli stats         # Show DB stats
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database.db_config import init_db, DBConnection
from database.db_ingest import ingest_results_folder


def cmd_init():
    print("Initializing database tables...")
    init_db()


def cmd_ingest():
    results_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Results')
    print(f"Ingesting from: {results_dir}")
    ingest_results_folder(results_dir)


def cmd_stats():
    tables = ['test_runs', 'byteblower_flows', 'byteblower_tcp_flows',
              'iperf3_results', 'iperf3_intervals', 'thousandeyes_results',
              'snmp_latency_bins', 'kafka_ds_latency']
    with DBConnection() as db:
        print("\n--- Database Stats ---")
        for table in tables:
            db.execute(f"SELECT COUNT(*) as cnt FROM {table}")
            row = db.fetchone()
            print(f"  {table}: {row['cnt']} rows")
        print()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == 'init':
        cmd_init()
    elif cmd == 'ingest':
        cmd_ingest()
    elif cmd == 'stats':
        cmd_stats()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)
