
## Credentials

| User | Password | Database |
|------|----------|----------|
| root | charter | - |
| netperf | charter | netperf |

## Connection

```bash
# root
mysql -u root -p

# netperf
mysql -u netperf -p netperf
```

## Load Schema

```bash
mysql -u netperf -p netperf < /home/aphillips/Projects/LLD_TEST_CLT_Dev_linux_compatible/database/schema.sql
```

## Schema Overview

### `test_runs`
Master record per test execution. Tracks test group, traffic type, CMTS type, scenario, iterations, status, and timestamps.

### `byteblower_flows`
ByteBlower frame blasting flow results. Stores packet loss, latency, jitter, and throughput per flow per iteration.

### `byteblower_tcp_flows`
ByteBlower TCP flow results. Stores throughput, congestion window, and retransmit data per flow per iteration.

### `iperf3_results`
iPerf3 per-stream summary results. Supports TCP, UDP, and QUIC protocols with RTT, bandwidth, and CPU metrics.

### `iperf3_intervals`
iPerf3 per-interval time-series data. Used for charting bandwidth and RTT over time.

### `thousandeyes_results`
ThousandEyes/SamKnows results. Stores throughput, latency, and jitter for HTTP and UDP tests.

### `snmp_latency_bins`
SNMP upstream latency bin data. Captures packet distribution across latency buckets before and after tests.

### `kafka_ds_latency`
Kafka CMTS downstream latency metrics. Time-series metric values per SFID.

## Verify Tables

```sql
USE netperf;
SHOW TABLES;
```

Expected tables:
- test_runs
- byteblower_flows
- byteblower_tcp_flows
- iperf3_results
- iperf3_intervals
- thousandeyes_results
- snmp_latency_bins
- kafka_ds_latency
