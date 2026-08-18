# NetPerf Orchestrator

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![GitHub](https://img.shields.io/badge/GitHub-netperf--orchestrator-black.svg)](https://github.com/birdyphillips/netperf-orchestrator)

CLI-based DOCSIS 3.1 / 4.0 network performance testing tool for automated traffic generation, SNMP latency collection, Kafka telemetry capture, and PDF/Excel report generation.

## Features

- **ByteBlower** — automated traffic generation with HTML/CSV/JSON/Excel reports
- **iPerf3 Linux** — TCP (cubic/Prague) + UDP parallel flows via SSH
- **iPerf3 macOS** — Apple QUIC + L4S flows via SSH
- **SpeedTest** — Ookla multi-client (Linux, macOS, Windows/NVIDIA)
- **ThousandEyes/SamKnows** — instant-test API (DS throughput, US throughput, UDP jitter)
- **PacketStorm** — configurable RTT emulation (10–50 ms)
- **SNMP monitoring** — before/after latency bin collection → `SNMP_US/DS_Latency_Report_*.xlsx`
- **Kafka telemetry** — real-time vCMTS `dp_flow_*` metrics → `Kafka_*_Latency_Report_*.xlsx`
- **Continuous cm_collector** — per-poll SNMP + Kafka CSVs + raw `.txt` files during test
- **PDF report** — per-session summary with throughput, weighted avg latency, P50/P99/P99.9 bins, AQM drops, loss%
- **Excel TimeSeries** — raw time-series workbook (TimeSeries, Throughput, per-SFID bins, Modem Info)
- **CMTS IPv6 auto-lookup** — SSH to CMTS to resolve modem IPv6 before test starts
- **Auto zip** — results folder compressed to `.zip` on completion

## Table of Contents

- [Setup](#setup)
- [Usage](#usage)
- [Scenarios](#scenarios)
- [Output Structure](#output-structure)
- [Architecture](#architecture)
- [Version History](#version-history)

## Setup

### 1. Clone and configure

```bash
git clone git@github.com:birdyphillips/netperf-orchestrator.git
cd netperf-orchestrator
cp config.yaml.example config.yaml
nano config.yaml   # fill in your environment
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
sudo apt install -y sshpass openssh-client
```

### 3. Key config.yaml sections

```yaml
snmp:
  jumpserver: <jump_host>
  username: <user>
  community: open

cmts_hosts:
  - name: <cmts_hostname>

kafka:
  broker: <broker_ip:port>
  topic: <topic_name>

byteblower:
  cli_path: /path/to/ByteBlowerCLI
  bb_flows_dir: bb_flows/
```

See `config.yaml.example` and `SETUP_GUIDE.md` for full documentation.

## Usage

Use the `netperf` wrapper script (sets up PATH/venv) or call `python3 netperf_orchestrator.py` directly.

`--cmts-type` is **required** for every run:
- `vcmts` — Kafka for DS latency
- `icmts` — SNMP for DS latency

### ByteBlower

```bash
# Single scenario, 1 iteration — vCMTS
./netperf --cmts-type vcmts -byteblower --bbp Port_20_example.bbp --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_0

# Single scenario, 1 iteration — iCMTS
./netperf --cmts-type icmts -byteblower --bbp Port_7_example.bbp --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_0

# Multiple iterations
./netperf --cmts-type vcmts -byteblower --bbp Port_20_example.bbp --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_0 -iteration 3

# All 6 scenarios
./netperf --cmts-type vcmts -byteblower --bbp Port_20_example.bbp --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_0
./netperf --cmts-type vcmts -byteblower --bbp Port_20_example.bbp --scenario DS_Classic_Only -test-group-name TEST_SCN_RTT_0
./netperf --cmts-type vcmts -byteblower --bbp Port_20_example.bbp --scenario US_Combined -test-group-name TEST_SCN_RTT_0
./netperf --cmts-type vcmts -byteblower --bbp Port_20_example.bbp --scenario DS_Combined -test-group-name TEST_SCN_RTT_0
./netperf --cmts-type vcmts -byteblower --bbp Port_20_example.bbp --scenario US_LL_Only -test-group-name TEST_SCN_RTT_0
./netperf --cmts-type vcmts -byteblower --bbp Port_20_example.bbp --scenario DS_LL_Only -test-group-name TEST_SCN_RTT_0

# Run all scenarios in one command
./netperf --cmts-type vcmts -byteblower --bbp Port_20_example.bbp \
  --scenario US_Classic_Only,DS_Classic_Only,US_Combined,DS_Combined,US_LL_Only,DS_LL_Only \
  -test-group-name HSI016_AQM -iteration 3
```

### ByteBlower + PacketStorm RTT

```bash
# vCMTS RTT values
./netperf --cmts-type vcmts -byteblower --bbp Port_20_example.bbp --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_10 -packetstorm --rtt vcmts10ms.json
./netperf --cmts-type vcmts -byteblower --bbp Port_20_example.bbp --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_20 -packetstorm --rtt vcmts20ms.json
./netperf --cmts-type vcmts -byteblower --bbp Port_20_example.bbp --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_30 -packetstorm --rtt vcmts30ms.json
./netperf --cmts-type vcmts -byteblower --bbp Port_20_example.bbp --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_40 -packetstorm --rtt vcmts40ms.json
./netperf --cmts-type vcmts -byteblower --bbp Port_20_example.bbp --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_50 -packetstorm --rtt vcmts50ms.json

# iCMTS RTT values
./netperf --cmts-type icmts -byteblower --bbp Port_7_example.bbp --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_10 -packetstorm --rtt icmts10ms.json
./netperf --cmts-type icmts -byteblower --bbp Port_7_example.bbp --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_30 -packetstorm --rtt icmts30ms.json
./netperf --cmts-type icmts -byteblower --bbp Port_7_example.bbp --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_50 -packetstorm --rtt icmts50ms.json

# All scenarios + all RTT values in one command
./netperf --cmts-type vcmts -byteblower --bbp Port_20_example.bbp \
  --scenario US_Classic_Only,DS_Classic_Only,US_Combined,DS_Combined,US_LL_Only,DS_LL_Only \
  -test-group-name TEST_SCN_RTT -packetstorm --rtt vcmts10ms.json,vcmts30ms.json,vcmts50ms.json -iteration 1
```

### iPerf3 Linux

```bash
# Single scenario
./netperf --cmts-type vcmts -iperf3 --clientIP <CLIENT_IP> --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_0

# JSON output
./netperf --cmts-type vcmts -iperf3 --clientIP <CLIENT_IP> --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_0 --output json

# All 6 scenarios
./netperf --cmts-type vcmts -iperf3 --clientIP <CLIENT_IP> --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_0
./netperf --cmts-type vcmts -iperf3 --clientIP <CLIENT_IP> --scenario DS_Classic_Only -test-group-name TEST_SCN_RTT_0
./netperf --cmts-type vcmts -iperf3 --clientIP <CLIENT_IP> --scenario US_Combined -test-group-name TEST_SCN_RTT_0
./netperf --cmts-type vcmts -iperf3 --clientIP <CLIENT_IP> --scenario DS_Combined -test-group-name TEST_SCN_RTT_0
./netperf --cmts-type vcmts -iperf3 --clientIP <CLIENT_IP> --scenario US_LL_Only -test-group-name TEST_SCN_RTT_0
./netperf --cmts-type vcmts -iperf3 --clientIP <CLIENT_IP> --scenario DS_LL_Only -test-group-name TEST_SCN_RTT_0

# Multiple scenarios in one command, 3 iterations, JSON
./netperf --cmts-type vcmts -iperf3 --clientIP <CLIENT_IP> \
  --scenario US_Classic_Only,DS_Classic_Only,US_Combined,DS_Combined \
  -test-group-name HSI029_AQP --output json -iteration 3

# 1000-packet AQM validation
./netperf --cmts-type vcmts -iperf3 --clientIP <CLIENT_IP> --scenario US_1000_Packets -test-group-name AQM_packet_count_test
./netperf --cmts-type vcmts -iperf3 --clientIP <CLIENT_IP> --scenario DS_1000_Packets -test-group-name AQM_packet_count_test

# STVA (Set Top Video Analyzer)
./netperf --cmts-type vcmts -iperf3 --clientIP <CLIENT_IP> --scenario DS_STVA -test-group-name STVA_TEST -iteration 3
./netperf --cmts-type vcmts -iperf3 --clientIP <CLIENT_IP> --scenario DS_STVA_ECT1 -test-group-name STVA_ECT1_TEST -iteration 3
```

### iPerf3 Linux + PacketStorm RTT

```bash
./netperf --cmts-type vcmts -iperf3 --clientIP <CLIENT_IP> --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_10 -packetstorm --rtt vcmts10ms.json
./netperf --cmts-type vcmts -iperf3 --clientIP <CLIENT_IP> --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_20 -packetstorm --rtt vcmts20ms.json
./netperf --cmts-type vcmts -iperf3 --clientIP <CLIENT_IP> --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_30 -packetstorm --rtt vcmts30ms.json
./netperf --cmts-type vcmts -iperf3 --clientIP <CLIENT_IP> --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_40 -packetstorm --rtt vcmts40ms.json
./netperf --cmts-type vcmts -iperf3 --clientIP <CLIENT_IP> --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_50 -packetstorm --rtt vcmts50ms.json
```

### iPerf3 macOS (Apple QUIC / L4S)

```bash
# TXT output (interval reporting)
./netperf --cmts-type vcmts -iperf3-darwin --clientIP <CLIENT_IP> --scenario US_Classic_Only -test-group-name TEST_SCN --output txt

# All 6 scenarios
./netperf --cmts-type vcmts -iperf3-darwin --clientIP <CLIENT_IP> --scenario US_Classic_Only -test-group-name TEST_SCN
./netperf --cmts-type vcmts -iperf3-darwin --clientIP <CLIENT_IP> --scenario DS_Classic_Only -test-group-name TEST_SCN
./netperf --cmts-type vcmts -iperf3-darwin --clientIP <CLIENT_IP> --scenario US_Combined -test-group-name TEST_SCN
./netperf --cmts-type vcmts -iperf3-darwin --clientIP <CLIENT_IP> --scenario DS_Combined -test-group-name TEST_SCN
./netperf --cmts-type vcmts -iperf3-darwin --clientIP <CLIENT_IP> --scenario US_LL_Only -test-group-name TEST_SCN
./netperf --cmts-type vcmts -iperf3-darwin --clientIP <CLIENT_IP> --scenario DS_LL_Only -test-group-name TEST_SCN

# Multiple scenarios in one command
./netperf --cmts-type vcmts -iperf3-darwin --clientIP <CLIENT_IP> \
  --scenario US_Classic_Only,DS_Classic_Only,US_Combined,DS_Combined \
  -test-group-name TEST_SCN --output txt -iteration 3
```

### SpeedTest

```bash
# All clients (linux, macos, nvidia)
./netperf --cmts-type vcmts -speedtest -test-group-name TEST_SCN_Ookla_Speedtest

# Specific clients
./netperf --cmts-type vcmts -speedtest --client linux -test-group-name TEST_SCN_Ookla_Speedtest
./netperf --cmts-type vcmts -speedtest --client linux,macos -test-group-name TEST_SCN_Ookla_Speedtest
./netperf --cmts-type vcmts -speedtest --client nvidia -test-group-name TEST_SCN_Ookla_Speedtest
```

### ThousandEyes / SamKnows

Runs all 3 tests per iteration: `http_get_mt` (DS throughput), `http_post_mt` (US throughput), `udp_jitter`.

```bash
# Basic run — unit ID required
./netperf --cmts-type vcmts -thousandeyes --unit-id 82670821 -test-group-name HSI021_SamKnows

# Multiple iterations
./netperf --cmts-type vcmts -thousandeyes --unit-id 82670821 -test-group-name HSI021_SamKnows -iteration 3

# With PacketStorm RTT impairment
./netperf --cmts-type vcmts -thousandeyes --unit-id 82670821 -packetstorm --rtt vcmts10ms.json -test-group-name HSI021_SamKnows_RTT_10
./netperf --cmts-type vcmts -thousandeyes --unit-id 82670821 -packetstorm --rtt vcmts30ms.json -test-group-name HSI021_SamKnows_RTT_30
./netperf --cmts-type vcmts -thousandeyes --unit-id 82670821 -packetstorm --rtt vcmts50ms.json -test-group-name HSI021_SamKnows_RTT_50
```

#### ThousandEyes tests per iteration

| Test | Metrics |
|---|---|
| `http_get_mt` | Downstream throughput (Mbps) |
| `http_post_mt` | Upstream throughput (Mbps) |
| `udp_jitter` | Latency (µs), Down jitter (µs), Up jitter (µs) |

### PacketStorm only

```bash
./netperf --cmts-type vcmts -packetstorm --rtt vcmts10ms.json
./netperf --cmts-type vcmts -packetstorm --rtt vcmts20ms.json
./netperf --cmts-type vcmts -packetstorm --rtt vcmts30ms.json
./netperf --cmts-type vcmts -packetstorm --rtt vcmts40ms.json
./netperf --cmts-type vcmts -packetstorm --rtt vcmts50ms.json
```

### PacketStorm API

```bash
# Login
curl -X POST http://<PACKETSTORM_IP>/xgui/rest \
  -H "Content-Type: application/json" \
  -d '{"op": "login", "user": "<username>", "args": {"password": "<password>"}}'

# Start RTT config
curl -X POST http://<PACKETSTORM_IP>/xgui/rest \
  -H "Content-Type: application/json" \
  -d '{"op": "start", "user": "<username>", "args": {"config": "vcmts10ms.json"}}'

# Stop
curl -X POST http://<PACKETSTORM_IP>/xgui/rest \
  -H "Content-Type: application/json" \
  -d '{"op": "stop", "user": "<username>"}'

# Status
curl -X POST http://<PACKETSTORM_IP>/xgui/rest \
  -H "Content-Type: application/json" \
  -d '{"op": "status", "user": "<username>"}'
```

## Scenarios

All traffic modes support the same scenario names:

| Scenario | Direction | Flows |
|---|---|---|
| `US_Classic_Only` | Upstream | 4 TCP cubic + 1 UDP |
| `DS_Classic_Only` | Downstream | 4 TCP cubic + 1 UDP |
| `US_Combined` | Upstream | 4 TCP cubic + 1 TCP Prague + 1 UDP CL + 1 UDP LL |
| `DS_Combined` | Downstream | 4 TCP cubic + 1 TCP Prague + 1 UDP CL + 1 UDP LL |
| `US_LL_Only` | Upstream | 1 TCP Prague + 1 UDP DSCP45 |
| `DS_LL_Only` | Downstream | 1 TCP Prague + 1 UDP DSCP45 |
| `US_UDP_NC` | Upstream | UDP non-conforming |
| `DS_UDP_NC` | Downstream | UDP non-conforming |
| `US_LL_1TCP_LL` | Upstream | 1 TCP Prague |
| `US_LL_4TCP_LL` | Upstream | 4 TCP Prague |
| `DS_LL_1TCP_LL` | Downstream | 1 TCP Prague |
| `DS_LL_4TCP_LL` | Downstream | 4 TCP Prague |
| `DS_STVA` | Downstream | 1 TCP cubic + 1 TCP ECT(1) |
| `DS_STVA_ECT1` | Downstream | 1 TCP cubic + 1 TCP ECT(1) |
| `US_1000_Packets` | Upstream | 1000 UDP packets (1400B, 10 Mbps) |
| `DS_1000_Packets` | Downstream | 1000 UDP packets (1400B, 10 Mbps) |

macOS (`-iperf3-darwin`) uses Apple QUIC (`--apple-quic`) and `--apple-l4s` in place of TCP Prague.

## Output Structure

### ByteBlower (multiple iterations)

```
Results/<TestGroup>_ByteBlower_<ts>/
└── <Scenario>/
    └── iteration_<n>/
        ├── ByteBlower_<Scenario>_iteration_<n>_SNMP_before_<ts>.txt
        ├── ByteBlower_<Scenario>_iteration_<n>_SNMP_after_<ts>.txt
        ├── <Scenario> - <ts>_R2_1.html
        ├── <Scenario> - <ts>_1.csv
        ├── <Scenario> - <ts>_1.json
        ├── Kafka_DS_Latency_Report_<Scenario>_iteration_<n>_<ts>.xlsx  (vcmts)
        ├── Kafka_Raw_Messages_<Scenario>_iteration_<n>_<ts>.txt
        └── SNMP_US_Latency_Report_iteration_<n>_<ts>.xlsx
```

### iPerf3 Linux (multiple iterations)

```
Results/<TestGroup>_iPerf3_Linux_<ts>/
└── <Scenario>_Linux/
    ├── iPerf3_Linux_<Scenario>_iteration_<n>_SNMP_before_<ts>.txt
    ├── iPerf3_Linux_<Scenario>_iteration_<n>_SNMP_after_<ts>.txt
    ├── Kafka_DS_Latency_Report_<Scenario>_iteration_<n>_<ts>.xlsx  (vcmts)
    ├── Kafka_Raw_Messages_<Scenario>_iteration_<n>_<ts>.txt
    ├── SNMP_US_Latency_Report_<Scenario>_Linux_iteration_<n>_<ts>.xlsx
    └── iteration_<n>/
        ├── <Dir>_<Group>_<Scenario>_4TCP_CL.json
        └── <Dir>_<Group>_<Scenario>_1TCP_LL.json
```

### cm_collector session (continuous polling)

```
Results/<mac>_<cmts_type>/<ts>/
├── snmp_us_<mac>_<ts>.csv
├── snmp_ds_<mac>_<ts>.csv          (icmts only)
├── kafka_<mac>_<ts>.csv            (vcmts only)
├── SNMP_poll_<n>_<ts>.txt          (one per poll)
├── Kafka_Raw_Messages_<mac>_<ts>.txt
├── TimeSeries_<cmts_type>_<mac>_<ts>.xlsx
└── <TestGroup>_<ts>_Report.pdf
```

## Arguments

| Argument | Description |
|---|---|
| `--cmts-type` | **Required.** `vcmts` or `icmts` |
| `-byteblower` | Enable ByteBlower mode |
| `--bbp` | `.bbp` file from `bb_flows/` (required with `-byteblower`) |
| `--scenario` | Scenario name(s), comma-separated |
| `-test-group-name` | Results folder prefix |
| `-packetstorm` | Enable PacketStorm RTT emulation |
| `--rtt` | PacketStorm config file (required with `-packetstorm`) |
| `-iperf3` | Enable iPerf3 Linux mode |
| `-iperf3-darwin` | Enable iPerf3 macOS mode |
| `--clientIP` | Client IP (required with `-iperf3` / `-iperf3-darwin`) |
| `--output` | iPerf3 output format: `json` or `txt` (default: `json`) |
| `-speedtest` | Enable SpeedTest mode |
| `--client` | SpeedTest clients: `linux`, `macos`, `nvidia` (default: all) |
| `-thousandeyes` | Enable ThousandEyes/SamKnows instant-test mode |
| `--unit-id` | SamKnows unit ID (required with `-thousandeyes`) |
| `--report-formats` | ByteBlower report formats (default: `html pdf csv xls xlsx json docx`) |
| `-iteration` | Number of iterations (default: `1`) |

## Architecture

### Files

| File | Purpose |
|---|---|
| `netperf_orchestrator.py` | Main CLI entry point |
| `netperf` | Wrapper script |
| `byteblower_logic.py` | ByteBlower subprocess execution |
| `iperf3_logic.py` | iPerf3 SSH execution (Linux + macOS) |
| `speedtest_logic.py` | Ookla SpeedTest SSH execution |
| `thousandeyes_logic.py` | ThousandEyes/SamKnows instant-test API |
| `packetstorm_logic.py` | PacketStorm RTT API |
| `snmp_collector.py` | SNMP before/after collection + latency report |
| `kafka_collector.py` | Kafka consumer for vCMTS `dp_flow_*` metrics |
| `cm_collector.py` | Continuous SNMP + Kafka polling threads |
| `cmts_modem_info.py` | SSH to CMTS to resolve modem IPv6 |
| `metrics_pdf_report.py` | PDF report generator (page summary + charts) |
| `config_loader.py` | YAML config loader |
| `logger.py` | Logging utility |
| `log_rotator.py` | Log rotation utility |
| `get_device_ips.py` | Standalone diagnostic: resolve modem IPv6 from CMTS |
| `config.yaml` | Environment configuration (not committed) |
| `config.yaml.example` | Documented config template |
| `bb_flows/` | ByteBlower `.bbp` project files |

### Latency data sources

| Direction | CMTS type | Collector | Report |
|---|---|---|---|
| Upstream | both | `snmp_collector.py` (before/after) | `SNMP_US_Latency_Report_*.xlsx` |
| Downstream | vcmts | `kafka_collector.py` (real-time) | `Kafka_DS_Latency_Report_*.xlsx` |
| Downstream | icmts | `snmp_collector.py` (before/after) | `SNMP_DS_Latency_Report_*.xlsx` |
| Both (continuous) | both | `cm_collector.py` (per-poll) | `TimeSeries_*.xlsx` + `*_Report.pdf` |

### Test flow

1. Prompt for CM MAC → SSH to CMTS → resolve modem IPv6
2. `start_cm_collector` — spawn SNMP + Kafka polling threads
3. For each iteration: SNMP before → start Kafka → run traffic → stop Kafka → SNMP after → latency report
4. `stop_cm_collector` — stop threads → write `TimeSeries_*.xlsx`
5. `generate_pdf_report` — call `metrics_pdf_report.py` → write `*_Report.pdf`
6. Zip results folder

## Version History

### v1.6 (current)
- Renamed `cmts_collector.py` → `kafka_collector.py`; all imports updated
- Added `metrics_pdf_report.py` to LLD project (previously only in CM_Collector)
- Fixed `result_files` undefined variable in `iperf3_logic.py` `run_scenario`
- Added `_write_snmp_txt()` — writes `SNMP_poll_<n>_<ts>.txt` per poll matching existing format
- Added `session_dir` to `cfg` dict in `start_cm_collector`

### v1.5
- Added `cm_collector.py` — continuous SNMP + Kafka polling threads
- Added `generate_excel_timeseries()` — TimeSeries Excel workbook
- Added `start_cm_collector` / `stop_cm_collector` / `generate_pdf_report` to orchestrator
- Added `metrics_pdf_report.py` — PDF with `page_summary` (throughput, weighted avg latency, P50/P99/P99.9, AQM drops, loss%)
- Replaced inline `_lookup_ipv6_from_cmts` with `cmts_modem_info.collect_cmts_data`
- Kafka `kafka_collector_thread` writes `Kafka_Raw_Messages_<mac>_<ts>.txt` on stop

### v1.4
- Added `kafka_collector.py` (was `cmts_collector.py`) — real-time vCMTS Kafka telemetry
- Added `cmts_modem_info.py` — SSH CMTS lookup for modem IPv6
- Added `Kafka_*_Latency_Report_*.xlsx` with P50/P99/P99.9, AQM drops, throughput, TimeSeries sheet
- `kafka` section added to `config.yaml`

### v1.3
- Added `config.yaml` / `config_loader.py` — all credentials and paths externalized
- Added `config.yaml.example` and `SETUP_GUIDE.md`

### v1.2
- Consolidated documentation into single README

### v1.1
- Added SpeedTest integration (`speedtest_logic.py`) with multi-client support

### v1.0
- ByteBlower, iPerf3 Linux/macOS, PacketStorm, SNMP collection
- Smart folder structure, RTT naming, iteration subfolders

## Author

**birdyphillips** — [@birdyphillips](https://github.com/birdyphillips)
