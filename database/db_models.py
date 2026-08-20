"""Database insert and query helpers for DELTA."""

from .db_config import DBConnection


# --- INSERT HELPERS ---

def insert_test_run(test_group_name, traffic_type, cmts_type=None, scenario=None,
                    rtt_config=None, bbp_file=None, iterations=1, output_dir=None,
                    status='completed', started_at=None, completed_at=None):
    with DBConnection() as db:
        db.execute("""
            INSERT INTO test_runs (test_group_name, traffic_type, cmts_type, scenario,
                rtt_config, bbp_file, iterations, output_dir, status, started_at, completed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (test_group_name, traffic_type, cmts_type, scenario,
              rtt_config, bbp_file, iterations, output_dir, status, started_at, completed_at))
        return db.lastrowid


def insert_byteblower_flow(test_run_id, iteration, flow_name, flow_type=None,
                           direction=None, tos=None, duration_ns=None,
                           packet_interval_ns=None, packets_sent=None,
                           packets_received=None, packet_loss=None,
                           bytes_received=None, latency_avg_ns=None,
                           latency_min_ns=None, latency_max_ns=None,
                           jitter_ns=None, throughput_bps=None, collected_at=None):
    with DBConnection() as db:
        db.execute("""
            INSERT INTO byteblower_flows (test_run_id, iteration, flow_name, flow_type,
                direction, tos, duration_ns, packet_interval_ns, packets_sent,
                packets_received, packet_loss, bytes_received, latency_avg_ns,
                latency_min_ns, latency_max_ns, jitter_ns, throughput_bps, collected_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (test_run_id, iteration, flow_name, flow_type, direction, tos,
              duration_ns, packet_interval_ns, packets_sent, packets_received,
              packet_loss, bytes_received, latency_avg_ns, latency_min_ns,
              latency_max_ns, jitter_ns, throughput_bps, collected_at))
        return db.lastrowid


def insert_byteblower_tcp_flow(test_run_id, iteration, flow_name, direction=None,
                               duration_ns=None, bytes_transferred=None,
                               avg_throughput_bps=None, min_throughput_bps=None,
                               max_throughput_bps=None, congestion_window_avg=None,
                               retransmits=None, collected_at=None):
    with DBConnection() as db:
        db.execute("""
            INSERT INTO byteblower_tcp_flows (test_run_id, iteration, flow_name, direction,
                duration_ns, bytes_transferred, avg_throughput_bps, min_throughput_bps,
                max_throughput_bps, congestion_window_avg, retransmits, collected_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (test_run_id, iteration, flow_name, direction, duration_ns,
              bytes_transferred, avg_throughput_bps, min_throughput_bps,
              max_throughput_bps, congestion_window_avg, retransmits, collected_at))
        return db.lastrowid


def insert_iperf3_result(test_run_id, iteration, protocol, direction=None,
                         flow_type=None, client_ip=None, server_ip=None,
                         server_port=None, num_streams=None, duration_sec=None,
                         bytes_sent=None, bandwidth_bps=None, retransmits=None,
                         congestion_algo=None, mean_rtt_us=None, min_rtt_us=None,
                         max_rtt_us=None, dscp=None, cpu_host_total=None,
                         cpu_remote_total=None, collected_at=None):
    with DBConnection() as db:
        db.execute("""
            INSERT INTO iperf3_results (test_run_id, iteration, protocol, direction,
                flow_type, client_ip, server_ip, server_port, num_streams, duration_sec,
                bytes_sent, bandwidth_bps, retransmits, congestion_algo, mean_rtt_us,
                min_rtt_us, max_rtt_us, dscp, cpu_host_total, cpu_remote_total, collected_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (test_run_id, iteration, protocol, direction, flow_type, client_ip,
              server_ip, server_port, num_streams, duration_sec, bytes_sent,
              bandwidth_bps, retransmits, congestion_algo, mean_rtt_us, min_rtt_us,
              max_rtt_us, dscp, cpu_host_total, cpu_remote_total, collected_at))
        return db.lastrowid


def insert_iperf3_intervals(iperf3_result_id, intervals):
    """Insert batch of interval data. intervals = list of dicts."""
    if not intervals:
        return
    with DBConnection() as db:
        db.executemany("""
            INSERT INTO iperf3_intervals (iperf3_result_id, interval_start, interval_end,
                bytes_transferred, bandwidth_bps, retransmits, snd_cwnd, rtt_us, rttvar_us)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, [(iperf3_result_id, i['start'], i['end'], i['bytes'], i['bps'],
               i.get('retransmits'), i.get('snd_cwnd'), i.get('rtt'), i.get('rttvar'))
              for i in intervals])


def insert_thousandeyes_result(test_run_id, iteration, unit_id=None,
                               test_type=None, throughput_mbps=None,
                               latency_us=None, jitter_down_us=None,
                               jitter_up_us=None, collected_at=None):
    with DBConnection() as db:
        db.execute("""
            INSERT INTO thousandeyes_results (test_run_id, iteration, unit_id, test_type,
                throughput_mbps, latency_us, jitter_down_us, jitter_up_us, collected_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (test_run_id, iteration, unit_id, test_type, throughput_mbps,
              latency_us, jitter_down_us, jitter_up_us, collected_at))
        return db.lastrowid


# --- QUERY HELPERS ---

def get_test_runs(limit=50, traffic_type=None, scenario=None):
    with DBConnection() as db:
        query = "SELECT * FROM test_runs WHERE 1=1"
        params = []
        if traffic_type:
            query += " AND traffic_type = %s"
            params.append(traffic_type)
        if scenario:
            query += " AND scenario = %s"
            params.append(scenario)
        query += " ORDER BY started_at DESC LIMIT %s"
        params.append(limit)
        db.execute(query, params)
        return db.fetchall()


def get_test_run(test_run_id):
    with DBConnection() as db:
        db.execute("SELECT * FROM test_runs WHERE id = %s", (test_run_id,))
        return db.fetchone()


def get_byteblower_flows(test_run_id):
    with DBConnection() as db:
        db.execute("SELECT * FROM byteblower_flows WHERE test_run_id = %s ORDER BY iteration, flow_name",
                   (test_run_id,))
        return db.fetchall()


def get_iperf3_results(test_run_id):
    with DBConnection() as db:
        db.execute("SELECT * FROM iperf3_results WHERE test_run_id = %s ORDER BY iteration, flow_type",
                   (test_run_id,))
        return db.fetchall()


def get_iperf3_intervals(iperf3_result_id):
    with DBConnection() as db:
        db.execute("SELECT * FROM iperf3_intervals WHERE iperf3_result_id = %s ORDER BY interval_start",
                   (iperf3_result_id,))
        return db.fetchall()


def get_thousandeyes_results(test_run_id):
    with DBConnection() as db:
        db.execute("SELECT * FROM thousandeyes_results WHERE test_run_id = %s ORDER BY iteration",
                   (test_run_id,))
        return db.fetchall()


def delete_test_run(test_run_id):
    """Delete test run and all related data (cascades)."""
    with DBConnection() as db:
        db.execute("DELETE FROM test_runs WHERE id = %s", (test_run_id,))
