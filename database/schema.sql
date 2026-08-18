-- NetPerf Orchestrator MySQL Schema
-- Run: mysql -u netperf -p netperf < schema.sql

CREATE DATABASE IF NOT EXISTS netperf;
USE netperf;

-- Master record per test execution
CREATE TABLE IF NOT EXISTS test_runs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    test_group_name VARCHAR(255) NOT NULL,
    traffic_type VARCHAR(50) NOT NULL COMMENT 'ByteBlower, iPerf3_Linux, iPerf3_macOS, SpeedTest, ThousandEyes',
    cmts_type VARCHAR(10) COMMENT 'vcmts or icmts',
    scenario VARCHAR(100),
    rtt_config VARCHAR(100),
    bbp_file VARCHAR(255),
    iterations INT DEFAULT 1,
    output_dir VARCHAR(500),
    status VARCHAR(20) DEFAULT 'completed' COMMENT 'running, completed, failed',
    started_at DATETIME NOT NULL,
    completed_at DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_test_group (test_group_name),
    INDEX idx_traffic_type (traffic_type),
    INDEX idx_scenario (scenario),
    INDEX idx_started_at (started_at)
) ENGINE=InnoDB;

-- ByteBlower frame blasting flow results
CREATE TABLE IF NOT EXISTS byteblower_flows (
    id INT AUTO_INCREMENT PRIMARY KEY,
    test_run_id INT NOT NULL,
    iteration INT NOT NULL,
    flow_name VARCHAR(255) NOT NULL,
    flow_type VARCHAR(50) COMMENT 'frameBlasting, tcp',
    direction VARCHAR(10) COMMENT 'US, DS',
    tos VARCHAR(10),
    duration_ns BIGINT,
    packet_interval_ns BIGINT,
    packets_sent INT,
    packets_received INT,
    packet_loss INT,
    bytes_received BIGINT,
    latency_avg_ns BIGINT,
    latency_min_ns BIGINT,
    latency_max_ns BIGINT,
    jitter_ns BIGINT,
    throughput_bps BIGINT,
    collected_at DATETIME,
    FOREIGN KEY (test_run_id) REFERENCES test_runs(id) ON DELETE CASCADE,
    INDEX idx_test_run (test_run_id),
    INDEX idx_collected_at (collected_at)
) ENGINE=InnoDB;

-- ByteBlower TCP flow results
CREATE TABLE IF NOT EXISTS byteblower_tcp_flows (
    id INT AUTO_INCREMENT PRIMARY KEY,
    test_run_id INT NOT NULL,
    iteration INT NOT NULL,
    flow_name VARCHAR(255) NOT NULL,
    direction VARCHAR(10) COMMENT 'US, DS',
    duration_ns BIGINT,
    bytes_transferred BIGINT,
    avg_throughput_bps BIGINT,
    min_throughput_bps BIGINT,
    max_throughput_bps BIGINT,
    congestion_window_avg INT,
    retransmits INT,
    collected_at DATETIME,
    FOREIGN KEY (test_run_id) REFERENCES test_runs(id) ON DELETE CASCADE,
    INDEX idx_test_run (test_run_id)
) ENGINE=InnoDB;

-- iPerf3 per-stream results (summary)
CREATE TABLE IF NOT EXISTS iperf3_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    test_run_id INT NOT NULL,
    iteration INT NOT NULL,
    client_ip VARCHAR(45),
    server_ip VARCHAR(45),
    server_port INT,
    protocol VARCHAR(10) NOT NULL COMMENT 'TCP, UDP, QUIC',
    num_streams INT,
    direction VARCHAR(10) COMMENT 'US, DS',
    flow_type VARCHAR(30) COMMENT '4TCP_CL, 1TCP_LL, 1UDP_CL, 1UDP_LL',
    duration_sec DECIMAL(10,6),
    bytes_sent BIGINT,
    bandwidth_bps BIGINT,
    retransmits INT,
    congestion_algo VARCHAR(30),
    mean_rtt_us INT,
    min_rtt_us INT,
    max_rtt_us INT,
    dscp INT,
    cpu_host_total DECIMAL(8,4),
    cpu_remote_total DECIMAL(8,4),
    collected_at DATETIME,
    FOREIGN KEY (test_run_id) REFERENCES test_runs(id) ON DELETE CASCADE,
    INDEX idx_test_run (test_run_id),
    INDEX idx_direction (direction),
    INDEX idx_collected_at (collected_at)
) ENGINE=InnoDB;

-- iPerf3 per-interval data (for time-series charts)
CREATE TABLE IF NOT EXISTS iperf3_intervals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    iperf3_result_id INT NOT NULL,
    interval_start DECIMAL(10,6),
    interval_end DECIMAL(10,6),
    bytes_transferred BIGINT,
    bandwidth_bps BIGINT,
    retransmits INT,
    snd_cwnd INT,
    rtt_us INT,
    rttvar_us INT,
    FOREIGN KEY (iperf3_result_id) REFERENCES iperf3_results(id) ON DELETE CASCADE,
    INDEX idx_result (iperf3_result_id)
) ENGINE=InnoDB;

-- ThousandEyes/SamKnows results
CREATE TABLE IF NOT EXISTS thousandeyes_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    test_run_id INT NOT NULL,
    iteration INT NOT NULL,
    unit_id VARCHAR(50),
    test_type VARCHAR(30) COMMENT 'http_get_mt, http_post_mt, udp_jitter',
    throughput_mbps DECIMAL(10,4),
    latency_us BIGINT,
    jitter_down_us BIGINT,
    jitter_up_us BIGINT,
    collected_at DATETIME,
    FOREIGN KEY (test_run_id) REFERENCES test_runs(id) ON DELETE CASCADE,
    INDEX idx_test_run (test_run_id)
) ENGINE=InnoDB;

-- SNMP latency bin data (upstream)
CREATE TABLE IF NOT EXISTS snmp_latency_bins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    test_run_id INT NOT NULL,
    iteration INT NOT NULL,
    phase VARCHAR(10) NOT NULL COMMENT 'before, after',
    sfid INT,
    bin_number INT,
    lower_bound_ms DECIMAL(10,4),
    upper_bound_ms DECIMAL(10,4),
    packet_count BIGINT,
    collected_at DATETIME,
    FOREIGN KEY (test_run_id) REFERENCES test_runs(id) ON DELETE CASCADE,
    INDEX idx_test_run (test_run_id),
    INDEX idx_phase (phase)
) ENGINE=InnoDB;

-- Kafka CMTS downstream latency metrics
CREATE TABLE IF NOT EXISTS kafka_ds_latency (
    id INT AUTO_INCREMENT PRIMARY KEY,
    test_run_id INT NOT NULL,
    iteration INT NOT NULL,
    sfid INT,
    metric_name VARCHAR(100),
    metric_value DECIMAL(20,4),
    timestamp_ms BIGINT,
    collected_at DATETIME,
    FOREIGN KEY (test_run_id) REFERENCES test_runs(id) ON DELETE CASCADE,
    INDEX idx_test_run (test_run_id),
    INDEX idx_metric (metric_name),
    INDEX idx_timestamp (timestamp_ms)
) ENGINE=InnoDB;

-- Setup user and permissions
-- CREATE USER IF NOT EXISTS 'netperf'@'localhost' IDENTIFIED BY '<password>';
-- GRANT ALL PRIVILEGES ON netperf.* TO 'netperf'@'localhost';
-- FLUSH PRIVILEGES;
