# modem_metrics Database - Findings Summary

## Overview
Yesterday I reran classic traffic across all 4 SCNs with LLD disabled and did not see any changes in latency compared to when LLD enabled testing I did with passing classic traffic

I also worked on collecting the downstream data from the testing I conducted from the  PostgreSQL database, to calculate latency like we did with STVA testing. 

The DB (172.30.80.33:5433) modem_metrics has about 4 weeks of vCMTS data (March 12 – April 9) but the CM metrics tables that had the flowstats, hsitogram stats sfid cogestions stats stopped collecting on March 24th so theres no data after march 24 for cm metric tables — that pipeline needs to be looked at.

The main finding is that the qos_service_flow_packets/octets counters are not data-plane — during a 421 Mbps ByteBlower upstream test, those counters only showed ~28KB, which is just management traffic. 
 
So throughput still needs to come from ByteBlower. What the DB is useful for is latency (histogram bins + max), AQM drops, congestion marking, and sanctioned packets — all per modem MAC, direction, and service flow. I wrote a modem_metrics.py CLI tool that can snapshot all these metrics for a given test window and export to CSV/Excel with deltas. Polling interval is ~15 seconds so we need to account for that when aligning with test start/end times.


## Database Access

Remote access via psql:

```bash
# Run a query
PGPASSWORD=postgres psql -h 172.30.80.33 -p 5433 -U postgres -d modem_metrics -c 'SELECT * FROM "dp_flow_queue_latency_bin_pkt_count" ORDER BY timestamp DESC NULLS LAST LIMIT 10;'

# List all tables
PGPASSWORD=postgres psql -h 172.30.80.33 -p 5433 -U postgres -d modem_metrics -c '\dt'
```

Or use the `modem_metrics.py` CLI tool:

```bash
python3 modem_metrics.py tables
python3 modem_metrics.py describe <table>
python3 modem_metrics.py sql "<SQL>"
python3 modem_metrics.py vcmts-snapshot --since "<start>" --until "<end>" --cm-mac <mac> -o <outdir>
```

## Data Availability

**vCMTS metrics:** 2026-03-12 → 2026-04-09 (~4 weeks)
**CM metrics:** 2026-03-12 → 2026-03-24 (~12 days, then collection stopped)

To verify what dates have data:

```sql
-- Check vCMTS data range
SELECT MIN("timestamp"), MAX("timestamp") FROM dp_flow_aqm_dropped_packets;

-- Check CM metrics data range
SELECT MIN(time), MAX(time) FROM flow_stats;

-- Check all tables at once
SELECT 'flow_stats' as table_name, MAX(time) as last_entry FROM flow_stats
UNION ALL SELECT 'histogram_stats', MAX(time) FROM histogram_stats
UNION ALL SELECT 'agg_flow_stats', MAX(time) FROM agg_flow_stats
UNION ALL SELECT 'congestion_stats', MAX(time) FROM congestion_stats
UNION ALL SELECT 'vcmts_sfid_info', MAX(time) FROM vcmts_sfid_info
UNION ALL SELECT 'dp_flow_aqm_dropped_packets', MAX("timestamp") FROM dp_flow_aqm_dropped_packets
UNION ALL SELECT 'qos_service_flow_packets', MAX("timestamp") FROM qos_service_flow_packets
ORDER BY table_name;
```

**⚠️ CM metrics collector appears to have stopped on March 24th. Needs investigation.**

## Key Finding: Throughput Counters Are NOT Data-Plane

The `qos_service_flow_packets` and `qos_service_flow_octets` tables look like they should have throughput data, but they don't. During a ByteBlower test pushing **421.79 Mbps** (~3.16 billion octets), the vCMTS counters only showed **28KB** of traffic over the same window. That's just management/keepalive traffic.

Verified this across all modems — no single 70-second test window showed more than a few hundred KB in these counters:

```sql
-- Check per-interval deltas for a modem during a test window
SELECT cm_mac_addr, direction, sf_index, "timestamp", value,
       value - LAG(value) OVER (PARTITION BY cm_mac_addr, direction, sf_index ORDER BY "timestamp") as delta
FROM qos_service_flow_octets
WHERE cm_mac_addr = '0c:b9:37:64:3a:b0'
  AND direction = 'upstream' AND sf_index = 0
  AND "timestamp" >= '2026-04-08 17:55:00'
  AND "timestamp" <= '2026-04-08 18:00:00'
ORDER BY "timestamp";
```

These are likely DOCSIS QoS management plane counters (SNMP MIB `docsQosServiceFlowOctets`), not actual user data counters. **Use ByteBlower for throughput numbers.**

## What the Database IS Good For

- **Latency histograms** — `dp_flow_queue_latency_bin_pkt_count` (16 bins with msec edges, per direction/sf_index)
- **Max latency** — `dp_flow_queue_latency_max_usec`
- **AQM drops** — `dp_flow_aqm_dropped_packets`
- **Congestion marking** — `dp_flow_aqm_marked_congested_packets`
- **Sanctioned packets** — `dp_flow_sanctioned_packets`
- **SFID mapping** — `vcmts_sfid_info` maps MAC → SFID → service flow name (us/ds, Classic/LL/AQP)

## Useful Queries

```sql
-- Look up SFIDs for a modem (use colon-separated MAC format)
SELECT DISTINCT sfid, name FROM vcmts_sfid_info
WHERE mac = '0c:b9:37:64:3a:b0' ORDER BY name;

-- Latency bin data for a modem during a test
SELECT direction, sf_index, bin_num, lower_edge_msec, upper_edge_msec, "timestamp", value
FROM dp_flow_queue_latency_bin_pkt_count
WHERE cm_mac_addr = '0c:b9:37:64:3a:b0'
  AND "timestamp" >= '2026-04-08 17:57:00'
  AND "timestamp" <= '2026-04-08 17:59:00'
ORDER BY direction, sf_index, bin_num, "timestamp";

-- Max latency during a test window
SELECT direction, sf_index, MAX(value) as max_latency_usec
FROM dp_flow_queue_latency_max_usec
WHERE cm_mac_addr = '0c:b9:37:64:3a:b0'
  AND "timestamp" >= '2026-04-08 17:57:00'
  AND "timestamp" <= '2026-04-08 17:59:00'
GROUP BY direction, sf_index
ORDER BY direction, sf_index;

-- AQM drops during a test
SELECT direction, sf_index, MAX(value) - MIN(value) as dropped_pkts
FROM dp_flow_aqm_dropped_packets
WHERE cm_mac_addr = '0c:b9:37:64:3a:b0'
  AND "timestamp" >= '2026-04-08 17:57:00'
  AND "timestamp" <= '2026-04-08 17:59:00'
GROUP BY direction, sf_index
ORDER BY direction, sf_index;
```

## MAC Address Format

The database stores MACs in colon-separated lowercase format: `0c:b9:37:64:3a:b0`

Cisco notation `0cb9.3764.3ab0` needs to be converted. The `modem_metrics.py` tool handles this automatically.

## Polling Interval

vCMTS metrics are polled every **~15 seconds** (samples appear at ~30s intervals in the DB). When querying deltas for a test window, account for this by widening the time range by ±30s to capture the bracketing samples.

## Tables Reference

| Category | Table | Time Column | Notes |
|----------|-------|-------------|-------|
| vCMTS | channel_utilization | timestamp | No MAC column |
| vCMTS | cm_reg_status_config | timestamp | MAC col: `cm_mac`, no value |
| vCMTS | dp_flow_aqm_dropped_packets | timestamp | MAC col: `cm_mac_addr` |
| vCMTS | dp_flow_aqm_marked_congested_packets | timestamp | MAC col: `cm_mac_addr` |
| vCMTS | dp_flow_queue_latency_bin_pkt_count | timestamp | Has `bin_num`, `lower/upper_edge_msec` |
| vCMTS | dp_flow_queue_latency_max_usec | timestamp | Value in microseconds |
| vCMTS | dp_flow_sanctioned_packets | timestamp | MAC col: `cm_mac_addr` |
| vCMTS | ksamis1_delta_packets_dropped | timestamp | MAC col: `cm_mac_addr` |
| vCMTS | ksamis1_service_time_created | timestamp | MAC col: `cm_mac_addr` |
| vCMTS | qos_service_flow_packets | timestamp | ⚠️ Mgmt plane only |
| vCMTS | qos_service_flow_octets | timestamp | ⚠️ Mgmt plane only |
| CM | flow_stats | time | Keyed by SFID |
| CM | histogram_stats | time | 16 latency bins, keyed by SFID |
| CM | agg_flow_stats | time | Keyed by SFID |
| CM | congestion_stats | time | ECN/CE counters, keyed by SFID |
| CM | vcmts_sfid_info | time | SFID → MAC + name mapping |
