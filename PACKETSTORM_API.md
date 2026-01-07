# PacketStorm API Documentation

## Overview
PacketStorm is a network emulation tool that provides REST API endpoints for configuration management and control. This document covers the API endpoints and command line testing methods.

## Base Configuration
- **URL**: `http://10.241.0.118/xgui/rest`
- **Username**: `automation`
- **Password**: `automation`
- **Content-Type**: `application/json`
- **Timeout**: 30 seconds

## API Endpoints

### 1. Login
Authenticate with PacketStorm server.

**Request:**
```json
{
    "op": "login",
    "user": "automation",
    "args": {
        "password": "automation"
    }
}
```

**Command Line Test:**
```bash
curl -X POST http://10.241.0.118/xgui/rest \
  -H "Content-Type: application/json" \
  -d '{
    "op": "login",
    "user": "automation",
    "args": {"password": "automation"}
  }'
```

### 2. Start Configuration
Start a PacketStorm configuration file.

**Request:**
```json
{
    "op": "start",
    "user": "automation",
    "args": {
        "config": "10vcmts.json"
    }
}
```

**Command Line Test:**
```bash
curl -X POST http://10.241.0.118/xgui/rest \
  -H "Content-Type: application/json" \
  -d '{
    "op": "start",
    "user": "automation",
    "args": {"config": "vcmts10ms.json"}
  }'
```

### 3. Stop Configuration
Stop the currently running PacketStorm configuration.

**Request:**
```json
{
    "op": "stop",
    "user": "automation"
}
```

**Command Line Test:**
```bash
curl -X POST http://10.241.0.118/xgui/rest \
  -H "Content-Type: application/json" \
  -d '{
    "op": "stop",
    "user": "automation"
  }'
```

### 4. Status Check
Get current PacketStorm status.

**Request:**
```json
{
    "op": "status",
    "user": "automation"
}
```

**Command Line Test:**
```bash
curl -X POST http://10.241.0.118/xgui/rest \
  -H "Content-Type: application/json" \
  -d '{
    "op": "status",
    "user": "automation"
  }'
```

### 5. List Configurations
List available configuration files.

**Request:**
```json
{
    "op": "list",
    "user": "automation",
    "args": {
        "type": "configs"
    }
}
```

**Command Line Test:**
```bash
curl -X POST http://10.241.0.118/xgui/rest \
  -H "Content-Type: application/json" \
  -d '{
    "op": "list",
    "user": "automation",
    "args": {"type": "configs"}
  }'
```

## Common Configuration Files
Based on the codebase, common RTT configuration files include:
- `vcmts10ms.json` - 10ms RTT configuration
- `vcmts20ms.json` - 20ms RTT configuration  
- `vcmts30ms.json` - 30ms RTT configuration
- `vcmts40ms.json` - 40ms RTT configuration
- `vcmts50ms.json` - 50ms RTT configuration

Based on the codebase, common RTT configuration files include:
- `icmts10ms.json` - 10ms RTT configuration
- `icmts20ms.json` - 20ms RTT configuration  
- `icmts30ms.json` - 30ms RTT configuration
- `icmts40ms.json` - 40ms RTT configuration
- `icmts50ms.json` - 50ms RTT configuration


## Python Testing Script

Create a test script to validate PacketStorm API:

```python
#!/usr/bin/env python3
import urllib.request
import json
import sys

def test_packetstorm_api():
    url = "http://10.241.0.118/xgui/rest"
    
    def send_request(data):
        try:
            req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'))
            req.add_header('Content-Type', 'application/json')
            response = urllib.request.urlopen(req, timeout=30)
            return response.read().decode('utf-8')
        except Exception as e:
            return f"Error: {e}"
    
    # Test login
    print("Testing login...")
    login_response = send_request({
        "op": "login",
        "user": "automation",
        "args": {"password": "automation"}
    })
    print(f"Login response: {login_response}")
    
    # Test status
    print("\nTesting status...")
    status_response = send_request({
        "op": "status",
        "user": "automation"
    })
    print(f"Status response: {status_response}")
    
    # Test list configs
    print("\nTesting list configs...")
    list_response = send_request({
        "op": "list",
        "user": "automation",
        "args": {"type": "configs"}
    })
    print(f"List response: {list_response}")

if __name__ == "__main__":
    test_packetstorm_api()
```

## Bash Testing Script

```bash
#!/bin/bash

BASE_URL="http://10.241.0.118/xgui/rest"
CONTENT_TYPE="Content-Type: application/json"

echo "=== PacketStorm API Test ==="

echo "1. Testing Login..."
curl -s -X POST $BASE_URL \
  -H "$CONTENT_TYPE" \
  -d '{"op": "login", "user": "automation", "args": {"password": "automation"}}' \
  | jq '.' 2>/dev/null || echo "Response received"

echo -e "\n2. Testing Status..."
curl -s -X POST $BASE_URL \
  -H "$CONTENT_TYPE" \
  -d '{"op": "status", "user": "automation"}' \
  | jq '.' 2>/dev/null || echo "Response received"

echo -e "\n3. Testing List Configs..."
curl -s -X POST $BASE_URL \
  -H "$CONTENT_TYPE" \
  -d '{"op": "list", "user": "automation", "args": {"type": "configs"}}' \
  | jq '.' 2>/dev/null || echo "Response received"

echo -e "\n4. Testing Start Config (10vcmts.json)..."
curl -s -X POST $BASE_URL \
  -H "$CONTENT_TYPE" \
  -d '{"op": "start", "user": "automation", "args": {"config": "10vcmts.json"}}' \
  | jq '.' 2>/dev/null || echo "Response received"

echo -e "\n5. Waiting 5 seconds..."
sleep 5

echo -e "\n6. Testing Stop Config..."
curl -s -X POST $BASE_URL \
  -H "$CONTENT_TYPE" \
  -d '{"op": "stop", "user": "automation"}' \
  | jq '.' 2>/dev/null || echo "Response received"

echo -e "\n=== Test Complete ==="
```

## Integration with LLD Test CLI

The PacketStorm API is integrated into the LLD Test CLI tool via `packetstorm_logic.py`. Usage:

```bash
# PacketStorm only
python3 lld_test.py -packetstorm --rtt 10vcmts.json

# Full workflow (PacketStorm + ByteBlower)
python3 lld_test.py -byteblower --bbp P16_vcmts_cm2068949223b8.bbp --scenario US_Classic_Only -packetstorm --rtt 10vcmts.json -iteration 3
```

## Troubleshooting

### Common Issues:
1. **Connection Timeout**: Check if PacketStorm server is accessible at `10.241.0.118`
2. **Authentication Failed**: Verify username/password are correct
3. **Config Not Found**: Ensure the configuration file exists on the PacketStorm server
4. **JSON Parse Error**: Verify request format matches expected schema

### Debug Commands:
```bash
# Test connectivity
ping 10.241.0.118

# Test HTTP connectivity
curl -v http://10.241.0.118/xgui/rest

# Check if service is running
nmap -p 80 10.241.0.118
```

## Response Codes
- **200**: Success
- **400**: Bad Request (malformed JSON)
- **401**: Unauthorized (authentication failed)
- **404**: Not Found (config file not found)
- **500**: Internal Server Error

## Logging
All PacketStorm API interactions are logged to:
- **Log File**: `/home/aphillips/Projects/Access_Architecture/LLD_TEST_CLT/logs/packetstorm_{timestamp}.log`
- **Rotation**: 10MB limit with automatic rotation
- **Format**: Timestamped entries with request/response details