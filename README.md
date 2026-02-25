# NetPerf Orchestrator v1.3

Network Performance Testing Orchestration Tool - Integrates ByteBlower, PacketStorm, iPerf3, and SpeedTest for automated network testing.

## Version 1.3 Features

- **Default 1 iteration**: Commands without `-iteration` parameter run only 1 iteration
- **Smart folder structure**: Single iterations save directly to main folder, multiple iterations create iteration subfolders
- **RTT naming**: Result folders include RTT information when PacketStorm is used (e.g., `SCN_RTT_10_US_Classic_Only_RTT_10ms_20251224_202431`)
- **Automated test runner**: `run_scn_rtt_tests.py` executes all Service Class Name (SCN) RTT tests with 15-second intervals
- **Configuration file**: All hardcoded paths, IPs, and credentials externalized to `config.yaml` for easy environment portability

## Initial Setup

### 1. Create Configuration File
```bash
# Copy example configuration
cp config.yaml.example config.yaml

# Edit for your environment
nano config.yaml
```

### 2. Configure Your Environment
Edit `config.yaml` to match your environment:
- ByteBlower CLI path
- PacketStorm URL and credentials
- iPerf3 client/server IPs and credentials
- SpeedTest client IPs and credentials
- SNMP jump server and credentials
- SSH key paths

### 3. Install Dependencies
```bash
# Install Python dependencies
pip install pyyaml paramiko pandas openpyxl

# Install system tools
sudo apt install -y sshpass openssh-client
```

### 4. Detailed Setup Instructions
For complete setup instructions including ByteBlower, iPerf3, SpeedTest, SSH keys, and SNMP configuration, see **[SETUP_GUIDE.md](SETUP_GUIDE.md)**.

## Quick Start

### Using the Wrapper Script (Recommended)
Use the `netperf` wrapper script to ensure all dependencies are available:

```bash
# Single iteration (default)
./netperf -byteblower --bbp Port_20_example.bbp --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_0

# With RTT configuration
./netperf -byteblower --bbp Port_20_example.bbp --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_10 -packetstorm --rtt vcmts10ms.json -iteration 1
```

### Using Python Directly
Alternatively, run with the venv Python:

```bash
source venv/bin/activate
python3 netperf_orchestrator.py -byteblower --bbp Port_20_example.bbp --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_0
```

### Run All Service Class Name (SCN) RTT Tests
```bash
./netperf -byteblower --bbp Port_13_example.bbp --scenario US_Classic_Only,DS_Classic_Only,US_Combined,DS_Combined,US_LL_Only,DS_LL_Only -test-group-name TEST_SCN_RTT -packetstorm --rtt vcmts10ms.json,vcmts30ms.json,vcmts50ms.json -iteration 1
```

## Usage Examples

### ByteBlower Only
```bash
# Single iteration (saves to main folder)
./netperf -byteblower --bbp Port_20_example.bbp --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_0

# Multiple iterations (creates iteration subfolders)
./netperf -byteblower --bbp Port_20_example.bbp --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_0 -iteration 3

# All ByteBlower scenarios
./netperf -byteblower --bbp Port_20_example.bbp --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_0
./netperf -byteblower --bbp Port_20_example.bbp --scenario DS_Classic_Only -test-group-name TEST_SCN_RTT_0
./netperf -byteblower --bbp Port_20_example.bbp --scenario US_Combined -test-group-name TEST_SCN_RTT_0
./netperf -byteblower --bbp Port_20_example.bbp --scenario DS_Combined -test-group-name TEST_SCN_RTT_0
./netperf -byteblower --bbp Port_20_example.bbp --scenario US_LL_Only -test-group-name TEST_SCN_RTT_0
./netperf -byteblower --bbp Port_20_example.bbp --scenario DS_LL_Only -test-group-name TEST_SCN_RTT_0
```

### ByteBlower + PacketStorm
```bash
# With RTT configuration
./netperf -byteblower --bbp HSI --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_10 -packetstorm --rtt vcmts10ms.json -iteration 1

# All RTT values
./netperf -byteblower --bbp Port_20_example.bbp --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_10 -packetstorm --rtt vcmts10ms.json -iteration 1
./netperf -byteblower --bbp Port_20_example.bbp --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_20 -packetstorm --rtt vcmts20ms.json -iteration 1
./netperf -byteblower --bbp Port_20_example.bbp --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_30 -packetstorm --rtt vcmts30ms.json -iteration 1
./netperf -byteblower --bbp Port_20_example.bbp --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_40 -packetstorm --rtt vcmts40ms.json -iteration 1
./netperf -byteblower --bbp Port_20_example.bbp --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_50 -packetstorm --rtt vcmts50ms.json -iteration 1
```

### iPerf3 Linux Client
```bash
# TXT output (default)
./netperf -iperf3 --clientIP <CLIENT_IP> --scenario US_Classic_Only -test-group-name TEST_SCN

# JSON output
./netperf -iperf3 --clientIP <CLIENT_IP> --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_0 --output json

# All iPerf3 scenarios (TXT)
./netperf -iperf3 --clientIP <CLIENT_IP> --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_0
./netperf -iperf3 --clientIP <CLIENT_IP> --scenario DS_Classic_Only -test-group-name TEST_SCN_RTT_0
./netperf -iperf3 --clientIP <CLIENT_IP> --scenario US_Combined -test-group-name TEST_SCN_RTT_0
./netperf -iperf3 --clientIP <CLIENT_IP> --scenario DS_Combined -test-group-name TEST_SCN_RTT_0
./netperf -iperf3 --clientIP <CLIENT_IP> --scenario US_LL_Only -test-group-name TEST_SCN_RTT_0
./netperf -iperf3 --clientIP <CLIENT_IP> --scenario DS_LL_Only -test-group-name TEST_SCN_RTT_0

# All iPerf3 scenarios (JSON)
./netperf -iperf3 --clientIP <CLIENT_IP> --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_0 --output json
./netperf -iperf3 --clientIP <CLIENT_IP> --scenario DS_Classic_Only -test-group-name TEST_SCN_RTT_0 --output json
./netperf -iperf3 --clientIP <CLIENT_IP> --scenario US_Combined -test-group-name TEST_SCN_RTT_0 --output json
./netperf -iperf3 --clientIP <CLIENT_IP> --scenario DS_Combined -test-group-name TEST_SCN_RTT_0 --output json
./netperf -iperf3 --clientIP <CLIENT_IP> --scenario US_LL_Only -test-group-name TEST_SCN_RTT_0 --output json
./netperf -iperf3 --clientIP <CLIENT_IP> --scenario DS_LL_Only -test-group-name TEST_SCN_RTT_0 --output json
```

### iPerf3 macOS Client (Apple QUIC/L4S)
```bash
# JSON output (default for macOS)
./netperf -iperf3-darwin --clientIP <CLIENT_IP> --scenario US_Classic_Only -test-group-name TEST_SCN

# TXT output
./netperf -iperf3-darwin --clientIP <CLIENT_IP> --scenario US_Classic_Only -test-group-name TEST_SCN --output txt

# All iPerf3-darwin scenarios (JSON)
./netperf -iperf3-darwin --clientIP <CLIENT_IP> --scenario US_Classic_Only -test-group-name TEST_SCN
./netperf -iperf3-darwin --clientIP <CLIENT_IP> --scenario DS_Classic_Only -test-group-name TEST_SCN
./netperf -iperf3-darwin --clientIP <CLIENT_IP> --scenario US_Combined -test-group-name TEST_SCN
./netperf -iperf3-darwin --clientIP <CLIENT_IP> --scenario DS_Combined -test-group-name TEST_SCN
./netperf -iperf3-darwin --clientIP <CLIENT_IP> --scenario US_LL_Only -test-group-name TEST_SCN
./netperf -iperf3-darwin --clientIP <CLIENT_IP> --scenario DS_LL_Only -test-group-name TEST_SCN

# All iPerf3-darwin scenarios (TXT)
./netperf -iperf3-darwin --clientIP <CLIENT_IP> --scenario US_Classic_Only -test-group-name TEST_SCN --output txt
./netperf -iperf3-darwin --clientIP <CLIENT_IP> --scenario DS_Classic_Only -test-group-name TEST_SCN --output txt
./netperf -iperf3-darwin --clientIP <CLIENT_IP> --scenario US_Combined -test-group-name TEST_SCN --output txt
./netperf -iperf3-darwin --clientIP <CLIENT_IP> --scenario DS_Combined -test-group-name TEST_SCN --output txt
./netperf -iperf3-darwin --clientIP <CLIENT_IP> --scenario US_LL_Only -test-group-name TEST_SCN --output txt
./netperf -iperf3-darwin --clientIP <CLIENT_IP> --scenario DS_LL_Only -test-group-name TEST_SCN --output txt
```

### iPerf3 + PacketStorm
```bash
# TXT output with RTT (default)
./netperf -iperf3 --clientIP <CLIENT_IP> --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_50 -packetstorm --rtt vcmts40ms.json -iteration 1

# JSON output with RTT
./netperf -iperf3 --clientIP <CLIENT_IP> --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_50 -packetstorm --rtt vcmts40ms.json --output json -iteration 1

# All RTT values with iPerf3
./netperf -iperf3 --clientIP <CLIENT_IP> --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_10 -packetstorm --rtt vcmts10ms.json -iteration 1
./netperf -iperf3 --clientIP <CLIENT_IP> --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_20 -packetstorm --rtt vcmts20ms.json -iteration 1
./netperf -iperf3 --clientIP <CLIENT_IP> --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_30 -packetstorm --rtt vcmts30ms.json -iteration 1
./netperf -iperf3 --clientIP <CLIENT_IP> --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_40 -packetstorm --rtt vcmts40ms.json -iteration 1
./netperf -iperf3 --clientIP <CLIENT_IP> --scenario US_Classic_Only -test-group-name TEST_SCN_RTT_50 -packetstorm --rtt vcmts50ms.json -iteration 1
```

### PacketStorm Only
```bash
# Start and stop RTT configuration
./netperf -packetstorm --rtt vcmts10ms.json
./netperf -packetstorm --rtt vcmts20ms.json
./netperf -packetstorm --rtt vcmts30ms.json
./netperf -packetstorm --rtt vcmts40ms.json
./netperf -packetstorm --rtt vcmts50ms.json
```

### SpeedTest
```bash
# Run on all clients (linux, macos, nvidia)
./netperf -speedtest -test-group-name TEST_SCN_Ookla_Speedtest

# Run on specific clients
./netperf -speedtest --client linux -test-group-name TEST_SCN_Ookla_Speedtest
./netperf -speedtest --client linux,macos -test-group-name TEST_SCN_Ookla_Speedtest
./netperf -speedtest --client nvidia -test-group-name TEST_SCN_Ookla_Speedtest
```

## Workflow

- **Full**: PacketStorm start → ByteBlower (3 iterations) → PacketStorm stop
- **ByteBlower Only**: Run ByteBlower scenario with 3 iterations
- **PacketStorm Only**: PacketStorm start → PacketStorm stop

## PacketStorm API Documentation

### Base Configuration
- **URL**: `http://<PACKETSTORM_IP>/xgui/rest`
- **Username**: `automation`
- **Password**: `automation`
- **Content-Type**: `application/json`
- **Timeout**: 30 seconds

### API Endpoints

#### Login
```bash
curl -X POST http://<PACKETSTORM_IP>/xgui/rest \
  -H "Content-Type: application/json" \
  -d '{"op": "login", "user": "<username>", "args": {"password": "<password>"}}'
```

#### Start Configuration
```bash
curl -X POST http://<PACKETSTORM_IP>/xgui/rest \
  -H "Content-Type: application/json" \
  -d '{"op": "start", "user": "<username>", "args": {"config": "vcmts10ms.json"}}'
```

#### Stop Configuration
```bash
curl -X POST http://<PACKETSTORM_IP>/xgui/rest \
  -H "Content-Type: application/json" \
  -d '{"op": "stop", "user": "<username>"}'
```

#### Status Check
```bash
curl -X POST http://<PACKETSTORM_IP>/xgui/rest \
  -H "Content-Type: application/json" \
  -d '{"op": "status", "user": "<username>"}'
```

#### List Configurations
```bash
curl -X POST http://<PACKETSTORM_IP>/xgui/rest \
  -H "Content-Type: application/json" \
  -d '{"op": "list", "user": "<username>", "args": {"type": "configs"}}'
```

### Testing

#### Python API Tester
```bash
# Test all endpoints
python3 test_packetstorm_api.py full vcmts10ms

# Test individual endpoints
python3 test_packetstorm_api.py login
python3 test_packetstorm_api.py status
python3 test_packetstorm_api.py start vcmts25ms
python3 test_packetstorm_api.py stop
```

#### Bash API Tester
```bash
# Test all endpoints
./test_packetstorm.sh full icmts30ms

# Test individual endpoints
./test_packetstorm.sh login
./test_packetstorm.sh status
./test_packetstorm.sh start vcmts40ms
./test_packetstorm.sh stop
```

### Response Codes
- **200**: Success
- **400**: Bad Request (malformed JSON)
- **401**: Unauthorized (authentication failed)
- **404**: Not Found (config file not found)
- **500**: Internal Server Error

## Arguments

- `-byteblower`: Enable ByteBlower mode
- `--bbp`: .bbp filename from bb_flows/ directory (required with -byteblower)
- `--scenario`: Scenario name (required with -byteblower or -iperf3)
- `-test-group-name`: Test group name prefix for results (e.g., SCN_RTT_0)
- `-packetstorm`: Enable PacketStorm mode
- `--rtt`: PacketStorm configuration name (required with -packetstorm)
- `-iperf3`: Enable iPerf3 Linux mode
- `-iperf3-darwin`: Enable iPerf3 macOS mode (Apple QUIC/L4S)
- `--clientIP`: Client IP address (required with -iperf3 or -iperf3-darwin)
- `--output`: iPerf3 output format: json or txt (default: txt)
- `-iteration`: Number of iterations (default: 1)
- `-speedtest`: Enable SpeedTest mode
- `--client`: SpeedTest clients to run on: linux, macos, nvidia (default: all three)

## Supported Scenarios

All tools support the same 6 test scenarios:

### Upstream Tests
- **US_Classic_Only**: Upstream Classic service flow only (4 TCP + 1 UDP)
- **US_Combined**: Upstream Classic + Low Latency combined (4 TCP Classic + 1 TCP LL + 1 UDP Classic + 1 UDP LL)
- **US_LL_Only**: Upstream Low Latency service flow only (1 TCP + 1 UDP with DSCP 45)

### Downstream Tests  
- **DS_Classic_Only**: Downstream Classic service flow only (4 TCP + 1 UDP)
- **DS_Combined**: Downstream Classic + Low Latency combined (4 TCP Classic + 1 TCP LL + 1 UDP Classic + 1 UDP LL)
- **DS_LL_Only**: Downstream Low Latency service flow only (1 TCP + 1 UDP with DSCP 45)

## Linux iPerf3 Integration

The tool supports running iPerf3 tests on Linux clients with automatic SSH key setup and result collection.

### Prerequisites
- Linux client with iPerf3 installed
- SSH access to client (username: `lld`, password: `<password>`)
- `sshpass` installed on control machine

### Supported Scenarios
- **US_Classic_Only**: Upstream Classic service flow tests
- **DS_Classic_Only**: Downstream Classic service flow tests  
- **US_Combined**: Upstream Classic + Low Latency combined tests
- **DS_Combined**: Downstream Classic + Low Latency combined tests
- **US_LL_Only**: Upstream Low Latency service flow tests
- **DS_LL_Only**: Downstream Low Latency service flow tests

### Automatic Features
- SSH key generation and deployment
- Remote directory creation
- Parallel iPerf3 test execution
- JSON and text result collection
- Local result storage with RTT naming

## macOS iPerf3 Integration

The tool supports running iPerf3-darwin tests on macOS clients with Apple QUIC and L4S support.

### Prerequisites
- macOS client with iperf3-darwin installed
- macOS server with iperf3-darwin installed
- SSH access to client (username: `lld_mac_client`, password: `<password>`)
- SSH access to server (username: `mac_studio_server`, password: `<password>`)
- `sshpass` installed on control machine

### Supported Scenarios
- **US_Classic_Only**: Upstream Classic service flow tests (QUIC + UDP)
- **DS_Classic_Only**: Downstream Classic service flow tests (QUIC + UDP)
- **US_Combined**: Upstream Classic + Low Latency combined tests (QUIC + QUIC L4S + UDP + UDP L4S)
- **DS_Combined**: Downstream Classic + Low Latency combined tests (QUIC + QUIC L4S + UDP + UDP L4S)
- **US_LL_Only**: Upstream Low Latency service flow tests (QUIC L4S + UDP L4S)
- **DS_LL_Only**: Downstream Low Latency service flow tests (QUIC L4S + UDP L4S)

### Apple QUIC/L4S Features
- Apple QUIC protocol support with `--apple-quic`
- Apple L4S (Low Latency, Low Loss, Scalable Throughput) with `--apple-l4s`
- Automatic SSH key deployment to both client and server
- Platform-specific directory paths (/Users vs /home)
- JSON and text result collection
- Local result storage with RTT naming

## Logs

- **Application Logs**: Stored in `logs/` directory with 10MB rotation
- **ByteBlower Logs**: Individual log files per test execution
- **PacketStorm Logs**: API interaction logs with timestamps

## Output Structure

### Single Iteration (Default)
Results saved directly to main folder:
```
Results/SCN_RTT_10_US_Classic_Only_RTT_10ms_20251224_202431/
├── US_Classic_Only_RTT_10ms - 20251224_202431__1.csv
├── US_Classic_Only_RTT_10ms - 20251224_202431__1.html
├── US_Classic_Only_RTT_10ms - 20251224_202431__1.json
├── US_Classic_Only_RTT_10ms - 20251224_202431__1_R1_1.html
├── US_Classic_Only_RTT_10ms - 20251224_202431__1_R2_1.html
└── US_Classic_Only_RTT_10ms - 20251224_202431__1_R3_1.html
```

### Multiple Iterations
Results organized in iteration subfolders:
```
Results/SCN_RTT_10_US_Classic_Only_RTT_10ms_20251224_202431/
├── iteration_1/
│   ├── US_Classic_Only_RTT_10ms - 20251224_202431__1.csv
│   └── ...
├── iteration_2/
│   ├── US_Classic_Only_RTT_10ms - 20251224_202431__1.csv
│   └── ...
└── iteration_3/
    ├── US_Classic_Only_RTT_10ms - 20251224_202431__1.csv
    └── ...
```

## Automated Test Runner

The `run_scn_rtt_tests.py` script executes all 36 Service Class Name (SCN) RTT test combinations:
- 6 scenarios: US_Classic_Only, DS_Classic_Only, US_Combined, DS_Combined, DS_LL_Only, US_LL_Only
- 6 RTT values per scenario: 0ms, 10ms, 20ms, 30ms, 40ms, 50ms
- 15-second intervals between tests
- Continues on individual test failures

```bash
# Run all Service Class Name (SCN) RTT tests
python3 run_scn_rtt_tests.py

# Estimated runtime: 9 minutes (intervals only) + test execution time
```

## Common Configuration Files

### PacketStorm RTT Configurations (vCMTS)
- `vcmts10ms.json` - 10ms RTT configuration
- `vcmts20ms.json` - 20ms RTT configuration  
- `vcmts30ms.json` - 30ms RTT configuration
- `vcmts40ms.json` - 40ms RTT configuration
- `vcmts50ms.json` - 50ms RTT configuration

### PacketStorm RTT Configurations (iCMTS)
- `icmts10ms.json` - 10ms RTT configuration
- `icmts20ms.json` - 20ms RTT configuration  
- `icmts30ms.json` - 30ms RTT configuration
- `icmts40ms.json` - 40ms RTT configuration
- `icmts50ms.json` - 50ms RTT configuration

### ByteBlower Project Files
- `Port_2_example.bbp` - Port 2 iCMTS configuration
- `Port_7_example.bbp` - Port 7 iCMTS configuration
- `Port_15_example.bbp` - Port 15 iCMTS configuration
- `Port_16_example.bbp` - Port 16 vCMTS configuration
- `Port_20_example.bbp` - Port 20 vCMTS configuration

#### Standard Scenarios Available in .bbp Files:
- **US_Classic_Only**: Upstream Classic service flow only
- **DS_Classic_Only**: Downstream Classic service flow only
- **US_Combined**: Upstream Classic + Low Latency combined
- **DS_Combined**: Downstream Classic + Low Latency combined
- **US_LL_Only**: Upstream Low Latency service flow only
- **DS_LL_Only**: Downstream Low Latency service flow only
- **US_UDP_NC**: Upstream UDP non-conforming traffic
- **DS_UDP_NC**: Downstream UDP non-conforming traffic
- **US_TCP_NC**: Upstream TCP non-conforming traffic
- **DS_TCP_NC**: Downstream TCP non-conforming traffic

## Files

- `config.yaml`: Main configuration file (create from config.yaml.example)
- `config.yaml.example`: Example configuration with all settings documented
- `config_loader.py`: Configuration file loader module
- `netperf_orchestrator.py`: Main CLI tool
- `netperf`: Wrapper script for easy execution
- `byteblower_logic.py`: ByteBlower execution logic
- `packetstorm_logic.py`: PacketStorm execution logic
- `iperf3_logic.py`: iPerf3 execution logic
- `speedtest_logic.py`: SpeedTest execution logic
- `snmp_collector.py`: SNMP data collection module
- `logger.py`: Logging utility
- `log_rotator.py`: Log rotation utility
- `SETUP_GUIDE.md`: Setup and installation guide
- `README.md`: This file

## SpeedTest Integration

The tool supports running Ookla SpeedTest on multiple client platforms with SNMP metrics collection before and after each client test.

### Supported Clients
- **Linux**: Ubuntu/Debian client with speedtest CLI
- **macOS**: macOS client with speedtest CLI via Homebrew
- **NVIDIA**: Windows NVIDIA client with speedtest.exe

### Features
- 3 iterations per client with 10-second intervals
- SNMP metrics collection before and after each client test
- Automatic SSH execution via sshpass
- Results collection and local storage
- Platform-specific command handling (Windows/Unix)
- All results consolidated in single folder
- Excel spreadsheet with all SNMP metrics

### Client Credentials
- Linux: `lld@<CLIENT_IP>` (password: `<password>`)
- macOS: `lld_mac_client@<CLIENT_IP>` (password: `<password>`)
- NVIDIA: `Administrator@<CLIENT_IP>` (password: `<password>`)

### Output Structure
```
Results/SCN_Speedtest_20250115_160000/
├── SNMP_before_SCN_Speedtest_linux_*.csv
├── SCN_Speedtest_linux_20250115_160000.txt
├── SNMP_after_SCN_Speedtest_linux_*.csv
├── SNMP_before_SCN_Speedtest_macos_*.csv
├── SCN_Speedtest_macos_20250115_160000.txt
├── SNMP_after_SCN_Speedtest_macos_*.csv
├── SNMP_before_SCN_Speedtest_nvidia_*.csv
├── SCN_Speedtest_nvidia_20250115_160000.txt
├── SNMP_after_SCN_Speedtest_nvidia_*.csv
└── SCN_Speedtest_Results.xlsx (consolidated SNMP data)
```

### Implementation
- **Module**: `speedtest_logic.py` - Core SpeedTest execution with per-client SNMP integration
- **SNMP Target**: `<MODEM_IPV6>` (CMTS)
- **Execution Flow**: For each client: SNMP Before → SpeedTest (3 iterations) → SNMP After
- **Excel Consolidation**: All SNMP CSV files merged into single Excel workbook with separate sheets per test

## Version History

### v1.3 (2025-01-16)
- **NEW**: Configuration file system (`config.yaml`) for environment portability
- **NEW**: All hardcoded paths, IPs, and credentials externalized to config file
- **NEW**: `config_loader.py` module for centralized configuration management
- **NEW**: `config.yaml.example` with fully documented settings
- **NEW**: `SETUP_GUIDE.md` with comprehensive setup instructions
- **ENHANCED**: Easy migration between different test environments
- **IMPROVED**: Security with file-based credential management
- **UPDATED**: All modules (byteblower, packetstorm, iperf3, speedtest, snmp) use config file

### v1.2 (2025-01-15)
- **CONSOLIDATED**: All documentation merged into single README.md
- **REMOVED**: Separate PACKETSTORM_API.md and SPEEDTEST_INTEGRATION.md files
- **UPDATED**: Complete PacketStorm API documentation with all endpoints
- **ENHANCED**: SpeedTest section with output structure and implementation details

### v1.1 (2025-01-15)
- **NEW**: SpeedTest integration with multi-client support
- **NEW**: `-speedtest` flag for running Ookla SpeedTest
- **NEW**: `--client` parameter to select specific clients (linux, macos, nvidia)
- **NEW**: `speedtest_logic.py` module for SpeedTest execution with SNMP metrics collection
- **NEW**: SNMP data collection before/after SpeedTest execution
- Default client selection: all three (linux, macos, nvidia)

### v1.0 (2025-01-03)
- Changed default iterations from 3 to 1
- Smart folder structure (no iteration subfolders for single iterations)
- RTT information included in result folder names
- Added automated test runner for Service Class Name (SCN) RTT tests
- Iteration folders now start from 1 instead of 0
- Enhanced README with examples and folder structure diagrams
- **NEW**: Linux iPerf3 integration with SSH key automation
- **NEW**: macOS iPerf3-darwin integration with Apple QUIC and L4S support
- **NEW**: Support for all 6 iPerf3 test scenarios (US/DS Classic/Combined/LL_Only)
- **NEW**: Automatic result collection from remote Linux and macOS clients
- **NEW**: iPerf3 output format selection (JSON or TXT with --output parameter)
- **NEW**: Platform-specific SSH authentication and directory handling
- **NEW**: Comprehensive usage examples for all scenarios and combinations

## Dependencies

Requires access to the lld_automation project at `/home/aphillips/Projects/lld_automation`