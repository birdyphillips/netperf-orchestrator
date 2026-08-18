"""Ingest existing Results/ data into MySQL database."""

import json
import os
import re
from datetime import datetime
from .db_models import (
    insert_test_run, insert_byteblower_flow, insert_byteblower_tcp_flow,
    insert_iperf3_result, insert_iperf3_intervals, insert_thousandeyes_result
)


def parse_folder_name(folder_name):
    """Extract test metadata from result folder name.
    Format: {test_group}_{traffic_type}_{timestamp}
    Example: HSI008_AQP_verify_ByteBlower_20260709_130448
    """
    # Match timestamp at end: _YYYYMMDD_HHMMSS
    ts_match = re.search(r'_(\d{8}_\d{6})$', folder_name)
    if not ts_match:
        return None

    timestamp_str = ts_match.group(1)
    started_at = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')

    prefix = folder_name[:ts_match.start()]

    # Detect traffic type from folder name
    traffic_types = ['ByteBlower', 'iPerf3_Linux', 'iPerf3_macOS', 'SpeedTest', 'ThousandEyes']
    traffic_type = None
    test_group = prefix
    for tt in traffic_types:
        if tt in prefix:
            traffic_type = tt
            test_group = prefix.replace(f'_{tt}', '').replace(f'{tt}_', '')
            break

    return {
        'test_group_name': test_group,
        'traffic_type': traffic_type or 'Unknown',
        'started_at': started_at
    }


def ingest_byteblower_json(test_run_id, json_path, iteration=1):
    """Parse ByteBlower JSON result and insert flows."""
    with open(json_path, 'r') as f:
        data = json.load(f)

    scenario = data.get('scenarioName', '')
    direction = 'US' if scenario.startswith('US') else 'DS'
    start_moment = data.get('startMoment')
    collected_at = None
    if start_moment:
        collected_at = datetime.fromisoformat(start_moment.replace('Z', '+00:00'))

    # Frame blasting flows
    for flow in data.get('frameBlastingFlows', []):
        config = flow.get('config', {})
        flow_name = config.get('name', 'unknown')
        for dest in flow.get('destinations', []):
            received = dest.get('received', {})
            latency = dest.get('latency', {})

            packets_sent = config.get('packets', 0)
            packets_received = received.get('packets', 0)

            # Calculate throughput from bytes/duration
            duration_ns = config.get('duration', 0)
            bytes_rx = received.get('bytes', 0)
            throughput = int((bytes_rx * 8 * 1e9) / duration_ns) if duration_ns > 0 else 0

            insert_byteblower_flow(
                test_run_id=test_run_id,
                iteration=iteration,
                flow_name=flow_name,
                flow_type='frameBlasting',
                direction=direction,
                tos=config.get('tos'),
                duration_ns=duration_ns,
                packet_interval_ns=config.get('packetInterval'),
                packets_sent=packets_sent,
                packets_received=packets_received,
                packet_loss=packets_sent - packets_received,
                bytes_received=bytes_rx,
                latency_avg_ns=latency.get('average'),
                latency_min_ns=latency.get('minimum'),
                latency_max_ns=latency.get('maximum'),
                jitter_ns=latency.get('jitter'),
                throughput_bps=throughput,
                collected_at=collected_at
            )

    # TCP flows
    for flow in data.get('tcpFlows', []):
        config = flow.get('config', {})
        flow_name = config.get('name', 'unknown')
        for dest in flow.get('destinations', []):
            result = dest.get('result', {})
            insert_byteblower_tcp_flow(
                test_run_id=test_run_id,
                iteration=iteration,
                flow_name=flow_name,
                direction=direction,
                duration_ns=config.get('duration'),
                bytes_transferred=result.get('bytes'),
                avg_throughput_bps=result.get('averageThroughput'),
                min_throughput_bps=result.get('minimumThroughput'),
                max_throughput_bps=result.get('maximumThroughput'),
                congestion_window_avg=result.get('averageCongestionWindow'),
                retransmits=result.get('retransmissions'),
                collected_at=collected_at
            )


def ingest_iperf3_json(test_run_id, json_path, iteration=1):
    """Parse iPerf3 JSON result and insert."""
    with open(json_path, 'r') as f:
        data = json.load(f)

    start = data.get('start', {})
    end = data.get('end', {})
    test_start = start.get('test_start', {})
    timestamp = start.get('timestamp', {})

    # Determine direction and flow type from filename
    filename = os.path.basename(json_path)
    direction = 'DS' if filename.startswith('DS_') else 'US'

    flow_type = None
    for ft in ['4TCP_CL', '1TCP_LL', '1UDP_CL', '1UDP_LL']:
        if ft in filename:
            flow_type = ft
            break

    # Connection info
    connected = start.get('connected', [{}])
    client_ip = connected[0].get('local_host') if connected else None
    server_ip = connected[0].get('remote_host') if connected else None
    server_port = connected[0].get('remote_port') if connected else None

    # Summary
    sum_sent = end.get('sum_sent', {})
    cpu = end.get('cpu_utilization_percent', {})

    # Get mean RTT from streams
    streams_end = end.get('streams', [])
    rtts = [s['sender'].get('mean_rtt', 0) for s in streams_end if 'sender' in s]
    mean_rtt = int(sum(rtts) / len(rtts)) if rtts else None
    min_rtts = [s['sender'].get('min_rtt', 0) for s in streams_end if 'sender' in s]
    max_rtts = [s['sender'].get('max_rtt', 0) for s in streams_end if 'sender' in s]

    collected_at = None
    if timestamp.get('timesecs'):
        collected_at = datetime.fromtimestamp(timestamp['timesecs'])

    result_id = insert_iperf3_result(
        test_run_id=test_run_id,
        iteration=iteration,
        protocol=test_start.get('protocol', 'TCP'),
        direction=direction,
        flow_type=flow_type,
        client_ip=client_ip,
        server_ip=server_ip,
        server_port=server_port,
        num_streams=test_start.get('num_streams'),
        duration_sec=sum_sent.get('seconds'),
        bytes_sent=sum_sent.get('bytes'),
        bandwidth_bps=int(sum_sent.get('bits_per_second', 0)),
        retransmits=sum_sent.get('retransmits'),
        congestion_algo=end.get('sender_tcp_congestion'),
        mean_rtt_us=mean_rtt,
        min_rtt_us=min(min_rtts) if min_rtts else None,
        max_rtt_us=max(max_rtts) if max_rtts else None,
        dscp=test_start.get('tos'),
        cpu_host_total=cpu.get('host_total'),
        cpu_remote_total=cpu.get('remote_total'),
        collected_at=collected_at
    )

    # Insert interval summaries
    intervals = data.get('intervals', [])
    interval_data = []
    for iv in intervals:
        s = iv.get('sum', {})
        # Get first stream for cwnd/rtt
        streams = iv.get('streams', [{}])
        first = streams[0] if streams else {}
        interval_data.append({
            'start': s.get('start'),
            'end': s.get('end'),
            'bytes': s.get('bytes'),
            'bps': int(s.get('bits_per_second', 0)),
            'retransmits': s.get('retransmits'),
            'snd_cwnd': first.get('snd_cwnd'),
            'rtt': first.get('rtt'),
            'rttvar': first.get('rttvar')
        })

    if interval_data:
        insert_iperf3_intervals(result_id, interval_data)


def ingest_thousandeyes_json(test_run_id, json_path, iteration=1):
    """Parse ThousandEyes JSON result and insert."""
    with open(json_path, 'r') as f:
        data = json.load(f)

    # ThousandEyes results vary — handle common structure
    if isinstance(data, list):
        for entry in data:
            _insert_te_entry(test_run_id, iteration, entry)
    elif isinstance(data, dict):
        _insert_te_entry(test_run_id, iteration, data)


def _insert_te_entry(test_run_id, iteration, entry):
    test_type = entry.get('test_type') or entry.get('type')
    insert_thousandeyes_result(
        test_run_id=test_run_id,
        iteration=iteration,
        unit_id=entry.get('unit_id'),
        test_type=test_type,
        throughput_mbps=entry.get('throughput_mbps'),
        latency_us=entry.get('latency_us'),
        jitter_down_us=entry.get('jitter_down_us'),
        jitter_up_us=entry.get('jitter_up_us'),
        collected_at=datetime.now()
    )


def ingest_results_folder(results_dir):
    """Walk the Results/ directory and ingest all test data."""
    if not os.path.isdir(results_dir):
        print(f"Results directory not found: {results_dir}")
        return

    ingested = 0
    for folder_name in sorted(os.listdir(results_dir)):
        folder_path = os.path.join(results_dir, folder_name)
        if not os.path.isdir(folder_path):
            continue

        meta = parse_folder_name(folder_name)
        if not meta:
            print(f"  Skipping (can't parse): {folder_name}")
            continue

        print(f"  Ingesting: {folder_name}")

        # Determine scenarios from subdirectories
        scenarios = []
        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            if os.path.isdir(item_path) and not item.startswith('iteration'):
                scenarios.append(item)

        # If no scenario subdirs, treat folder itself as single scenario
        if not scenarios:
            scenarios = [None]

        for scenario in scenarios:
            if scenario:
                scenario_path = os.path.join(folder_path, scenario)
            else:
                scenario_path = folder_path

            # Clean scenario name (remove _Linux suffix for iperf3)
            clean_scenario = scenario.replace('_Linux', '').replace('_macOS', '') if scenario else None

            test_run_id = insert_test_run(
                test_group_name=meta['test_group_name'],
                traffic_type=meta['traffic_type'],
                scenario=clean_scenario,
                output_dir=folder_path,
                status='completed',
                started_at=meta['started_at'],
                completed_at=meta['started_at']
            )

            # Find and ingest JSON files
            _ingest_scenario_files(test_run_id, scenario_path, meta['traffic_type'])
            ingested += 1

    print(f"\nIngested {ingested} test runs.")


def _ingest_scenario_files(test_run_id, scenario_path, traffic_type):
    """Find and ingest all result files in a scenario directory."""
    if not os.path.isdir(scenario_path):
        return

    for root, dirs, files in os.walk(scenario_path):
        for filename in files:
            if not filename.endswith('.json'):
                continue

            filepath = os.path.join(root, filename)

            # Determine iteration from path or filename
            iteration = 1
            iter_match = re.search(r'iteration[_]?(\d+)', root)
            if iter_match:
                iteration = int(iter_match.group(1))

            try:
                if traffic_type == 'ByteBlower':
                    ingest_byteblower_json(test_run_id, filepath, iteration)
                elif traffic_type in ('iPerf3_Linux', 'iPerf3_macOS'):
                    ingest_iperf3_json(test_run_id, filepath, iteration)
                elif traffic_type == 'ThousandEyes':
                    ingest_thousandeyes_json(test_run_id, filepath, iteration)
            except Exception as e:
                print(f"    Error ingesting {filepath}: {e}")


if __name__ == '__main__':
    results_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Results')
    print(f"Ingesting results from: {results_dir}")
    ingest_results_folder(results_dir)
