# Kafka Consumer Command Reference

## Setup

```bash
# Activate venv (required)
source ~/Projects/LLD_TEST_CLT_Dev_linux_compatible/venv/bin/activate

# Install dependencies (first time only)
pip install kafka-python zstandard
```

## Brokers

| Broker | Address | Description |
|--------|---------|-------------|
| Stage vCMTS | `65.185.232.139:11203` | Harmonic vCMTS telemetry (active) |
| DAA Legacy | `kafka01.daas.charterlab.com:9092` | Legacy DAA metrics (mostly empty) |

## Quick Reference

```bash
# Default broker is 65.185.232.139:11203

# List all metric topics
python3 kafka_consumer.py --list-topics

# List topics on legacy broker
python3 kafka_consumer.py --broker kafka01.daas.charterlab.com:9092 --list-topics

# Show last message timestamp per partition
python3 kafka_consumer.py --topic cmts_metrics_apc01k1dccc --last-message

# Debug — show first 5 messages
python3 kafka_consumer.py --topic cmts_metrics_apc01k1dccc --latest --debug

# All messages for a MAC (live stream)
python3 kafka_consumer.py --topic cmts_metrics_apc01k1dccc --latest --mac 206a949223b8

# Filter by metric name + MAC
python3 kafka_consumer.py --topic cmts_metrics_apc01k1dccc --latest --mac 206a949223b8 --filter dp_flow

# Pipe to file during test
python3 kafka_consumer.py --topic cmts_metrics_apc01k1dccc --latest --mac 206a949223b8 --filter dp_flow > test_results.txt 2>&1
```

## MAC Address Formats

All formats work:
```bash
--mac 206a949223b8
--mac 206a.9492.23b8
--mac 20:6a:94:92:23:b8
```

---

## Per-Metric Filter Commands

### dp_flow_QueueLatencyMaxUsec (max queue latency per 30s interval)
```bash
python3 kafka_consumer.py --topic cmts_metrics_apc01k1dccc --latest --mac 206a949223b8 --filter dp_flow_QueueLatencyMaxUsec
```

### dp_flow_QueueLatencyAvgUsec (average queue latency)
```bash
python3 kafka_consumer.py --topic cmts_metrics_apc01k1dccc --latest --mac 206a949223b8 --filter dp_flow_QueueLatencyAvgUsec
```

### dp_flow_QueueLatencyBinPktCount (16-bin latency histogram for P99 calculation)
```bash
python3 kafka_consumer.py --topic cmts_metrics_apc01k1dccc --latest --mac 206a949223b8 --filter dp_flow_QueueLatencyBinPktCount
```

### dp_flow_AqmDroppedPackets (AQM dropped packets)
```bash
python3 kafka_consumer.py --topic cmts_metrics_apc01k1dccc --latest --mac 206a949223b8 --filter dp_flow_AqmDroppedPackets
```

### dp_flow_AqmMarkedCongestedPackets (AQM congestion marked)
```bash
python3 kafka_consumer.py --topic cmts_metrics_apc01k1dccc --latest --mac 206a949223b8 --filter dp_flow_AqmMarkedCongestedPackets
```

### dp_flow_SanctionedPackets (sanctioned packets)
```bash
python3 kafka_consumer.py --topic cmts_metrics_apc01k1dccc --latest --mac 206a949223b8 --filter dp_flow_SanctionedPackets
```

### K_Samis1_DeltaPacketsDropped (SAMIS delta dropped)
```bash
python3 kafka_consumer.py --topic cmts_metrics_apc01k1dccc --latest --mac 206a949223b8 --filter K_Samis1_DeltaPacketsDropped
```

### K_Samis1_ServiceTimeCreated (service flow creation time)
```bash
python3 kafka_consumer.py --topic cmts_metrics_apc01k1dccc --latest --mac 206a949223b8 --filter K_Samis1_ServiceTimeCreated
```

### snmp_docsQosServiceFlowPackets (QoS service flow packets)
```bash
python3 kafka_consumer.py --topic cmts_metrics_apc01k1dccc --latest --mac 206a949223b8 --filter snmp_docsQosServiceFlowPackets
```

### snmp_docsQosServiceFlowOctets (QoS service flow octets)
```bash
python3 kafka_consumer.py --topic cmts_metrics_apc01k1dccc --latest --mac 206a949223b8 --filter snmp_docsQosServiceFlowOctets
```

### channel_utilization (per-interface, no MAC filter needed)
```bash
python3 kafka_consumer.py --topic cmts_metrics_apc01k1dccc --latest --filter channel_utilization
```

### cm_reg_status_config (CM registration status)
```bash
python3 kafka_consumer.py --topic cmts_metrics_apc01k1dccc --latest --mac 206a949223b8 --filter cm_reg_status
```

---

## Broad Filters

```bash
# All dp_flow metrics for a MAC
python3 kafka_consumer.py --topic cmts_metrics_apc01k1dccc --latest --mac 206a949223b8 --filter dp_flow

# All latency metrics
python3 kafka_consumer.py --topic cmts_metrics_apc01k1dccc --latest --mac 206a949223b8 --filter Latency

# All AQM metrics
python3 kafka_consumer.py --topic cmts_metrics_apc01k1dccc --latest --mac 206a949223b8 --filter Aqm

# All SAMIS metrics
python3 kafka_consumer.py --topic cmts_metrics_apc01k1dccc --latest --mac 206a949223b8 --filter K_Samis1

# All QoS metrics
python3 kafka_consumer.py --topic cmts_metrics_apc01k1dccc --latest --mac 206a949223b8 --filter docsQos

# All metrics containing "downstream"
python3 kafka_consumer.py --topic cmts_metrics_apc01k1dccc --latest --mac 206a949223b8 --filter downstream

# All metrics containing "upstream"
python3 kafka_consumer.py --topic cmts_metrics_apc01k1dccc --latest --mac 206a949223b8 --filter upstream
```

---

## Test Workflow

```bash
# 1. Start listening before test (save to file + watch live)
python3 kafka_consumer.py --topic cmts_metrics_apc01k1dccc --latest --mac 206a949223b8 --filter dp_flow 2>&1 | tee test_results.txt

# 2. Run ByteBlower/iPerf3 test in another terminal

# 3. Ctrl+C when test is done

# 4. Check results
cat test_results.txt
```

### Capture specific metrics during test
```bash
# Latency only
python3 kafka_consumer.py --topic cmts_metrics_apc01k1dccc --latest --mac 206a949223b8 --filter QueueLatencyMaxUsec > latency_test.txt 2>&1

# AQM drops only
python3 kafka_consumer.py --topic cmts_metrics_apc01k1dccc --latest --mac 206a949223b8 --filter AqmDroppedPackets > aqm_test.txt 2>&1

# Everything for the MAC
python3 kafka_consumer.py --topic cmts_metrics_apc01k1dccc --latest --mac 206a949223b8 > all_metrics.txt 2>&1
```

---

## Kafka Metric Name Mapping

| DB Table Name | Kafka Metric Name |
|---------------|-------------------|
| channel_utilization | `channel_utilization` |
| cm_reg_status_config | `K_CmRegStatus_*` |
| dp_flow_aqm_dropped_packets | `dp_flow_AqmDroppedPackets` |
| dp_flow_aqm_marked_congested_packets | `dp_flow_AqmMarkedCongestedPackets` |
| dp_flow_queue_latency_bin_pkt_count | `dp_flow_QueueLatencyBinPktCount` |
| dp_flow_queue_latency_max_usec | `dp_flow_QueueLatencyMaxUsec` |
| dp_flow_sanctioned_packets | `dp_flow_SanctionedPackets` |
| ksamis1_delta_packets_dropped | `K_Samis1_DeltaPacketsDropped` |
| ksamis1_service_time_created | `K_Samis1_ServiceTimeCreated` |
| qos_service_flow_packets | `snmp_docsQosServiceFlowPackets` |
| qos_service_flow_octets | `snmp_docsQosServiceFlowOctets` |

---

## Message Format

Prometheus exposition format:
```
metric_name{label1="value1",label2="value2"} value timestamp_ms
```

Example:
```
dp_flow_QueueLatencyMaxUsec{cmMacAddr="20:6a:94:92:23:b8",dir="downstream",mdName="Md1:0/0.0",rpdName="rpd1:0",sfIndex="1",node="ap71-85-92-202",cluster="apc01k1dccc",namespace="default",pod="vcmts-cd-0-0"} 22358.6206 1775779799926
```

- **Value**: `22358.6206` (microseconds for latency, packets for counts)
- **Timestamp**: `1775779799926` (milliseconds since epoch)
- **Labels**: `cmMacAddr`, `dir` (upstream/downstream), `sfIndex`, `mdName`, `rpdName`

---

## Polling Interval

Metrics are published every **30 seconds** per CM per service flow.

---

## Troubleshooting

```bash
# Check broker connectivity
nc -zv 65.185.232.139 11203 -w 5
nslookup stamp-kafka-brk.stage.charterlab.com

# Check legacy broker
nc -zv kafka01.daas.charterlab.com 9092 -w 5
nslookup kafka01.daas.charterlab.com

# Verify kafka-python installed
python3 -c "from kafka import KafkaConsumer; print('OK')"

# Verify zstd codec
python3 -c "import zstandard; print('zstd OK')"

# Quick topic check
python3 -c "from kafka import KafkaConsumer; c = KafkaConsumer(bootstrap_servers='65.185.232.139:11203'); print('Topics:', len(c.topics())); c.close()"
```

---

## Lab Cable Modems

| HSI Config | CM MAC | CM MAC (colon) |
|------------|--------|----------------|
| HSI016 | e0db.d161.3d18 | e0:db:d1:61:3d:18 |
| HSI018 | 0cb9.3764.3ab0 | 0c:b9:37:64:3a:b0 |
| HSI021 | 206a.9492.23b8 | 20:6a:94:92:23:b8 |
| HSI029 | a456.ccfe.0e3f | a4:56:cc:fe:0e:3f |
