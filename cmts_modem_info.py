
#!/usr/bin/env python3
import paramiko
import sys
import os
import logging
from datetime import datetime
from config_loader import config

# Setup logging
log_dir = "/home/aphillips/Projects/LLD_TEST_CLT_Dev_linux_compatible/logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"cmts_modem_info_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Suppress paramiko's verbose logging
logging.getLogger("paramiko").setLevel(logging.WARNING)


def normalize_mac(mac):
    """Normalize MAC address to dotted format (e.g. 206a.9492.23b8).
    Accepts: 206a.9492.23b8, 20:6a:94:92:23:b8, 206a949223b8
    """
    raw = mac.replace(':', '').replace('.', '').replace('-', '').lower()
    if len(raw) != 12:
        raise ValueError(f"Invalid MAC address: {mac}")
    return f"{raw[0:4]}.{raw[4:8]}.{raw[8:12]}"


def parse_ipv6_from_vcmts(output):
    """Parse IPv6 from vCMTS 'scm <mac> ip' output.
    Example line:
     206a.9492.23b8   b-online(pt)   N      2605:1c00:50f2:203:9826:3c40:8796:1c3    -
    """
    import re
    for line in output.splitlines():
        m = re.search(r'([0-9a-fA-F]{1,4}(?::[0-9a-fA-F]{1,4}){5,7})', line)
        if m:
            return m.group(1)
    return None


def parse_ipv6_from_icmts(output):
    """Parse IPv6 from iCMTS 'scm <mac> detail' output.
    Looks for: Uptime=... IPv6=2605:1c00:...
    """
    import re
    m = re.search(r'IPv6=([0-9a-fA-F]{1,4}(?::[0-9a-fA-F]{0,4}){5,7})', output)
    if m:
        return m.group(1)
    # fallback: any IPv6 on any line
    for line in output.splitlines():
        m = re.search(r'([0-9a-fA-F]{1,4}(?::[0-9a-fA-F]{1,4}){5,7})', line)
        if m:
            return m.group(1)
    return None

def ssh_cmts_collector(username, jumpserver, cmts_host, cmts_password, cm_mac, cmts_type, output_file=None):
    """SSH into jump server, then to CMTS and execute service flow commands"""
    
    # Normalize MAC to dotted format for CMTS CLI
    cm_mac = normalize_mac(cm_mac)
    
    logger.info(f"Starting CMTS collection for {cmts_type.upper()} {cmts_host}, CM MAC: {cm_mac}")
    
    # Determine commands based on CMTS type
    if cmts_type.lower() == 'icmts':
        commands = [
            f"scm {cm_mac} detail",
            f"scm qos-sc cm-mac {cm_mac}",
            f"scm {cm_mac} service-flow aqm",
        ]
        labels = [
            "Cable Modem Detail",
            "QoS Service Classes",
            "Service Flow AQM Configuration",
        ]
    else:  # vcmts
        commands = [
            f"scm {cm_mac} ip",
            f"scm {cm_mac} service-flow aqm",
            f"scm {cm_mac} cpe",
            f"scm {cm_mac} qos bps"
        ]
        labels = [
            "IP Address Information",
            "Service Flow AQM Configuration",
            "CPE Information",
            "QoS Bandwidth Information"
        ]
    
    try:
        # Create SSH client for jumpserver
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Connect to jumpserver
        key_path = config.ssh_key_path
        connected = False
        
        try:
            if os.path.exists(key_path):
                logger.info(f"Connecting to jumpserver {jumpserver} with key: {key_path}")
                print(f"Connecting to jumpserver {jumpserver} with key: {key_path}")
                ssh.connect(jumpserver, username=username, key_filename=key_path, timeout=10)
                connected = True
        except Exception as e:
            logger.warning(f"Failed with key {key_path}: {e}")
            print(f"Failed with key {key_path}: {e}")
        
        if not connected:
            try:
                logger.info(f"Connecting to jumpserver {jumpserver} with default keys")
                print(f"Connecting to jumpserver {jumpserver} with default keys")
                ssh.connect(jumpserver, username=username, timeout=10)
                connected = True
            except Exception as e:
                logger.error(f"Failed with default keys: {e}")
                print(f"Failed with default keys: {e}")
        
        if not connected:
            logger.error(f"Failed to connect to jumpserver {jumpserver}")
            raise Exception(f"Failed to connect to jumpserver {jumpserver}")
        
        logger.info(f"Successfully connected to jumpserver {jumpserver}")
        print(f"Successfully connected to jumpserver {jumpserver}")
        
        logger.info(f"Executing commands on {cmts_type.upper()} {cmts_host} via jumpserver...")
        print(f"Executing commands on {cmts_type.upper()} {cmts_host} via jumpserver...")
        
        results = {}
        output_lines = []
        cm_ipv6 = None
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        output_lines.append(f"{cmts_type.upper()} Modem Information - {timestamp}")
        output_lines.append(f"{cmts_type.upper()} Host: {cmts_host}")
        output_lines.append(f"Cable Modem MAC: {cm_mac}")
        output_lines.append("="*80)
        
        # Execute commands via jumpserver using interactive shell
        for i, cmd in enumerate(commands):
            logger.info(f"Executing command {i+1}/{len(commands)}: {cmd}")
            print(f"\nExecuting: {cmd}")
            
            # Open interactive shell on jumpserver
            shell = ssh.invoke_shell()
            
            # SSH from jumpserver to CMTS
            shell.send(f"ssh -o StrictHostKeyChecking=no {username}@{cmts_host}\n")
            
            # Wait for password prompt
            import time
            time.sleep(1)
            output_buffer = shell.recv(4096).decode()
            
            # Send password if prompted
            if 'password' in output_buffer.lower():
                shell.send(cmts_password + '\n')
                time.sleep(1)
                output_buffer += shell.recv(4096).decode()
            
            # Execute command
            shell.send(cmd + '\n')
            time.sleep(3)  # Wait for command to start producing output

            # Collect output until CMTS prompt reappears (command finished)
            output = ''
            max_iterations = 100
            iteration = 0

            while iteration < max_iterations:
                if shell.recv_ready():
                    chunk = shell.recv(8192).decode('utf-8', errors='replace')
                    output += chunk

                    if '--More--' in chunk:
                        shell.send(' ')
                        time.sleep(0.5)
                    # CMTS prompt ends with '#' — command is done
                    elif chunk.rstrip().endswith('#'):
                        break
                    else:
                        time.sleep(0.2)
                else:
                    time.sleep(0.3)
                    # After waiting, if prompt is present we're done
                    if output.rstrip().endswith('#'):
                        break

                iteration += 1
            
            # Exit CMTS session
            shell.send('exit\n')
            time.sleep(0.5)
            
            shell.close()
            
            error = ''
            
            results[labels[i]] = {
                'output': output,
                'error': error if error else None
            }
            
            # Extract IPv6 on first command (IP info)
            if i == 0:
                if cmts_type.lower() == 'icmts':
                    cm_ipv6 = parse_ipv6_from_icmts(output)
                else:
                    cm_ipv6 = parse_ipv6_from_vcmts(output)
                if cm_ipv6:
                    logger.info(f"Extracted Cable Modem IPv6: {cm_ipv6}")
                    print(f"\nCable Modem IPv6: {cm_ipv6}")
            
        ssh.close()

        # Parse sfid/scn from appropriate output
        sfids = []
        import re as _re

        if cmts_type.lower() == 'icmts' and 'QoS Service Classes' in results:
            # scm qos-sc cm-mac output:
            # SCN              Sfid     Dir Prio MaxSusRate  ...
            # usHSI018           101268 US     1   42000000  ...
            qos_output = results['QoS Service Classes']['output']
            seen = set()
            for qline in qos_output.splitlines():
                parts = qline.split()
                if len(parts) >= 3 and _re.match(r'^\d+$', parts[1]) and parts[2] in ('US', 'DS'):
                    scn_val  = parts[0]
                    sfid_val = int(parts[1])
                    dir_val  = parts[2]
                    if sfid_val not in seen:
                        seen.add(sfid_val)
                        sfids.append({'sfid': sfid_val, 'scn': scn_val, 'dir': dir_val})

        elif cmts_type.lower() == 'vcmts' and 'QoS Bandwidth Information' in results:
            qos_output = results['QoS Bandwidth Information']['output']
            seen = set()
            for qline in qos_output.splitlines():
                parts = qline.split()
                if len(parts) >= 2 and parts[0].isdigit() and parts[-1].isalpha() and not parts[-1].isdigit():
                    sfid_val = int(parts[0])
                    scn_val  = parts[-1]
                    dir_val  = parts[1] if len(parts) > 1 else ''
                    key = (sfid_val, scn_val)
                    if key not in seen:
                        seen.add(key)
                        sfids.append({'sfid': sfid_val, 'scn': scn_val, 'dir': dir_val})

        # Parse bin edges from 'scm <mac> service-flow aqm' output
        # Column order: MAC_DOMAIN CHANNEL DIR SFID AQM_STATUS AQM_ALGO CLS_AQM_LAT_TRGT
        #               IAQM_MAX_THRSH IAQM_RNG_EXP LATENCY_HISTOGRAM
        # The LATENCY HISTOGRAM is everything after the 9th whitespace-delimited token
        bin_edges_by_sfid = {}
        if 'Service Flow AQM Configuration' in results:
            aqm_output = results['Service Flow AQM Configuration']['output']
            for aline in aqm_output.splitlines():
                parts = aline.split()
                # Valid data rows: parts[3] is numeric SFID, parts[2] is US/DS
                if len(parts) < 4:
                    continue
                try:
                    sfid_val = int(parts[3])
                except (ValueError, IndexError):
                    continue
                # Bin edges start at index 9 — collect all float tokens from there
                edge_tokens = parts[9:] if len(parts) > 9 else []
                edges = []
                for tok in edge_tokens:
                    try:
                        edges.append(float(tok))
                    except ValueError:
                        break  # stop at non-numeric token
                if edges:
                    bin_edges_by_sfid[sfid_val] = edges

        # Merge bin edges into sfids list
        for entry in sfids:
            sfid_key = entry.get('sfid')
            if sfid_key in bin_edges_by_sfid:
                entry['bin_edges_ms'] = bin_edges_by_sfid[sfid_key]

        # Also add any SFIDs found only in AQM output (not in QoS BPS)
        existing_sfids = {e['sfid'] for e in sfids}
        if 'Service Flow AQM Configuration' in results:
            aqm_output = results['Service Flow AQM Configuration']['output']
            for aline in aqm_output.splitlines():
                parts = aline.split()
                if len(parts) < 4:
                    continue
                try:
                    sfid_val = int(parts[3])
                except (ValueError, IndexError):
                    continue
                if sfid_val not in existing_sfids:
                    dir_val = parts[2] if len(parts) > 2 else ''
                    entry = {'sfid': sfid_val, 'scn': '', 'dir': dir_val}
                    if sfid_val in bin_edges_by_sfid:
                        entry['bin_edges_ms'] = bin_edges_by_sfid[sfid_val]
                    sfids.append(entry)
                    existing_sfids.add(sfid_val)

        # Build JSON summary
        summary = {
            'cmts_type':  cmts_type.upper(),
            'cmts_host':  cmts_host,
            'cm_mac':     cm_mac,
            'cm_ipv6':    cm_ipv6 or '',
            'timestamp':  timestamp,
            'sfids':      sfids,
        }

        # Write to file if specified
        if output_file:
            import json
            with open(output_file, 'w') as f:
                json.dump(summary, f, indent=2)
                logger.info(f"Results saved to: {output_file}")
                print(f"Results saved to: {output_file}")
        
        logger.info(f"CMTS collection completed successfully")
        return {'results': results, 'cm_ipv6': cm_ipv6}
        
    except Exception as e:
        error_msg = f"SSH connection failed: {e}"
        logger.error(error_msg)
        print(error_msg)
        if output_file:
            with open(output_file, 'w') as f:
                f.write(f"ERROR: {error_msg}\n")
        return None

def collect_cmts_data(cmts_host, cm_mac, cmts_type='vcmts', test_name=None, output_dir="Results"):
    """Collect CMTS service flow data and return IPv6 address"""
    username = config.snmp_username
    jumpserver = config.snmp_jumpserver
    cmts_password = config.vcmts_password
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Create filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(output_dir, 'modem_summary.json')
    
    logger.info(f"Collecting {cmts_type.upper()} service flow data for CM: {cm_mac}")
    print(f"Collecting {cmts_type.upper()} service flow data for CM: {cm_mac}")
    result = ssh_cmts_collector(username, jumpserver, cmts_host, cmts_password, cm_mac, cmts_type, filename)
    
    if result and 'cm_ipv6' in result:
        return result['cm_ipv6']
    return None

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python cmts_modem_info.py <cmts_host> <cm_mac> [cmts_type] [test_name] [output_dir]")
        print("Example (vCMTS): python cmts_modem_info.py apc01k1dccc e0db.d161.3d18 vcmts ByteBlower_Test Results")
        print("Example (iCMTS): python cmts_modem_info.py cts01k1dccc 0cb9.379c.64b4 icmts ByteBlower_Test Results")
        sys.exit(1)
    
    cmts_host = sys.argv[1]
    cm_mac = sys.argv[2]
    cmts_type = sys.argv[3] if len(sys.argv) > 3 else 'vcmts'
    test_name = sys.argv[4] if len(sys.argv) > 4 else None
    output_dir = sys.argv[5] if len(sys.argv) > 5 else "Results"
    
    cm_ipv6 = collect_cmts_data(cmts_host, cm_mac, cmts_type, test_name, output_dir)
    if cm_ipv6:
        logger.info(f"Cable Modem IPv6 Address: {cm_ipv6}")
        print(f"\n{'='*80}")
        print(f"Cable Modem IPv6 Address: {cm_ipv6}")
        print(f"{'='*80}")
    
    logger.info(f"Log file: {log_file}")
