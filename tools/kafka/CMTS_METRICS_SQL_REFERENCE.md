# CMTS Metrics PostgreSQL Query Reference

## Connection

```bash
PGPASSWORD=postgres psql -h 172.30.80.33 -p 5433 -U postgres -d modem_metrics
```

One-liner format:
```bash
PGPASSWORD=postgres psql -h 172.30.80.33 -p 5433 -U postgres -d modem_metrics -c "SQL_HERE"
```

---

## Tables

| Table | Description |
|---|---|
| channel_utilization | DS/US channel utilization % |
| cm_reg_status_config | CM registration status |
| dp_flow_aqm_dropped_packets | AQM dropped packets per service flow |
| dp_flow_aqm_marked_congested_packets | AQM congestion-marked packets |
| dp_flow_queue_latency_bin_pkt_count | Latency histogram bins (16 bins) |
| dp_flow_queue_latency_max_usec | Max queue latency per interval |
| dp_flow_sanctioned_packets | Sanctioned packet counts |
| ksamis1_delta_packets_dropped | SAMIS delta dropped packets |
| ksamis1_service_time_created | Service flow creation time |
| qos_service_flow_packets | QoS service flow packet counts |

---

## Quick Checks

### List all tables
```sql
PGPASSWORD=postgres psql -h 172.30.80.33 -p 5433 -U postgres -d modem_metrics -c "\dt"
```

### Row counts per table
```sql
PGPASSWORD=postgres psql -h 172.30.80.33 -p 5433 -U postgres -d modem_metrics -c "
SELECT 'channel_utilization' as table_name, COUNT(*) FROM channel_utilization
UNION ALL SELECT 'cm_reg_status_config', COUNT(*) FROM cm_reg_status_config
UNION ALL SELECT 'dp_flow_aqm_dropped_packets', COUNT(*) FROM dp_flow_aqm_dropped_packets
UNION ALL SELECT 'dp_flow_aqm_marked_congested_packets', COUNT(*) FROM dp_flow_aqm_marked_congested_packets
UNION ALL SELECT 'dp_flow_queue_latency_bin_pkt_count', COUNT(*) FROM dp_flow_queue_latency_bin_pkt_count
UNION ALL SELECT 'dp_flow_queue_latency_max_usec', COUNT(*) FROM dp_flow_queue_latency_max_usec
UNION ALL SELECT 'dp_flow_sanctioned_packets', COUNT(*) FROM dp_flow_sanctioned_packets
UNION ALL SELECT 'ksamis1_delta_packets_dropped', COUNT(*) FROM ksamis1_delta_packets_dropped
UNION ALL SELECT 'ksamis1_service_time_created', COUNT(*) FROM ksamis1_service_time_created
UNION ALL SELECT 'qos_service_flow_packets', COUNT(*) FROM qos_service_flow_packets
ORDER BY table_name;"
```

### Time range per table
```sql
PGPASSWORD=postgres psql -h 172.30.80.33 -p 5433 -U postgres -d modem_metrics -c "
SELECT 'channel_utilization' as table_name, MIN(\"timestamp\"), MAX(\"timestamp\") FROM channel_utilization
UNION ALL SELECT 'cm_reg_status_config', MIN(\"timestamp\"), MAX(\"timestamp\") FROM cm_reg_status_config
UNION ALL SELECT 'dp_flow_aqm_dropped_packets', MIN(\"timestamp\"), MAX(\"timestamp\") FROM dp_flow_aqm_dropped_packets
UNION ALL SELECT 'dp_flow_aqm_marked_congested_packets', MIN(\"timestamp\"), MAX(\"timestamp\") FROM dp_flow_aqm_marked_congested_packets
UNION ALL SELECT 'dp_flow_queue_latency_bin_pkt_count', MIN(\"timestamp\"), MAX(\"timestamp\") FROM dp_flow_queue_latency_bin_pkt_count
UNION ALL SELECT 'dp_flow_queue_latency_max_usec', MIN(\"timestamp\"), MAX(\"timestamp\") FROM dp_flow_queue_latency_max_usec
UNION ALL SELECT 'dp_flow_sanctioned_packets', MIN(\"timestamp\"), MAX(\"timestamp\") FROM dp_flow_sanctioned_packets
UNION ALL SELECT 'ksamis1_delta_packets_dropped', MIN(\"timestamp\"), MAX(\"timestamp\") FROM ksamis1_delta_packets_dropped
UNION ALL SELECT 'ksamis1_service_time_created', MIN(\"timestamp\"), MAX(\"timestamp\") FROM ksamis1_service_time_created
UNION ALL SELECT 'qos_service_flow_packets', MIN(\"timestamp\"), MAX(\"timestamp\") FROM qos_service_flow_packets
ORDER BY table_name;"
```

---

## Summary Query (matches vcmts_snapshot summary.csv)

### Full summary — all service flows, both directions
```sql
PGPASSWORD=postgres psql -h 172.30.80.33 -p 5433 -U postgres -d modem_metrics -c "
WITH time_window AS (
    SELECT MIN(\"timestamp\") as t_start, MAX(\"timestamp\") as t_end,
           EXTRACT(EPOCH FROM MAX(\"timestamp\") - MIN(\"timestamp\")) as duration_s
    FROM qos_service_flow_packets
),
packets AS (
    SELECT direction, sf_index,
           SUM(value) as total_packets
    FROM qos_service_flow_packets, time_window
    WHERE \"timestamp\" BETWEEN t_start AND t_end
    GROUP BY directionection, sf_index
),
octets AS (
    SELECT direction, sf_index,
           SUM(value) as total_octets
    FROM qos_service_flow_packets q
    JOIN LATERAL (SELECT 1) x ON true, time_window
    GROUP BY directionection, sf_index
),
latency AS (
    SELECT direction, sf_index,
           AVG(value) / 1000.0 as avg_latency_ms,
           PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY value) / 1000.0 as p99_latency_ms,
           MAX(value) as max_latency_usec
    FROM dp_flow_queue_latency_max_usec, time_window
    WHERE \"timestamp\" BETWEEN t_start AND t_end AND value > 0
    GROUP BY directionection, sf_index
),
aqm AS (
    SELECT direction, sf_index,
           SUM(value) as aqm_dropped_pkts
    FROM dp_flow_aqm_dropped_packets, time_window
    WHERE \"timestamp\" BETWEEN t_start AND t_end
    GROUP BY directionection, sf_index
),
congested AS (
    SELECT direction, sf_index,
           SUM(value) as aqm_marked_congested_pkts
    FROM dp_flow_aqm_marked_congested_packets, time_window
    WHERE \"timestamp\" BETWEEN t_start AND t_end
    GROUP BY directionection, sf_index
),
sanctioned AS (
    SELECT direction, sf_index,
           SUM(value) as sanctioned_pkts
    FROM dp_flow_sanctioned_packets, time_window
    WHERE \"timestamp\" BETWEEN t_start AND t_end
    GROUP BY directionection, sf_index
),
dropped AS (
    SELECT direction, sf_index,
           SUM(value) as ksamis1_dropped_pkts
    FROM ksamis1_delta_packets_dropped, time_window
    WHERE \"timestamp\" BETWEEN t_start AND t_end
    GROUP BY directionection, sf_index
)
SELECT p.direction as direction, p.sf_index,
       p.total_packets,
       p.total_packets * 1000 as total_octets_est,
       p.total_packets * 8000 as total_bits_est,
       ROUND((p.total_packets * 8000 / tw.duration_s)::numeric, 2) as throughput_bps,
       ROUND((p.total_packets * 8 / tw.duration_s)::numeric, 4) as throughput_kbps,
       ROUND((p.total_packets * 8 / tw.duration_s / 1000)::numeric, 4) as throughput_mbps,
       ROUND(l.avg_latency_ms::numeric, 4) as avg_latency_ms,
       ROUND(l.p99_latency_ms::numeric, 4) as p99_latency_ms,
       l.max_latency_usec,
       COALESCE(a.aqm_dropped_pkts, 0) as aqm_dropped_pkts,
       COALESCE(c.aqm_marked_congested_pkts, 0) as aqm_marked_congested_pkts,
       COALESCE(s.sanctioned_pkts, 0) as sanctioned_pkts,
       COALESCE(d.ksamis1_dropped_pkts, 0) as ksamis1_dropped_pkts
FROM packets p
CROSS JOIN time_window tw
LEFT JOIN latency l ON p.direction = l.direction AND p.sf_index = l.sf_index
LEFT JOIN aqm a ON p.direction = a.direction AND p.sf_index = a.sf_index
LEFT JOIN congested c ON p.direction = c.direction AND p.sf_index = c.sf_index
LEFT JOIN sanctioned s ON p.direction = s.direction AND p.sf_index = s.sf_index
LEFT JOIN dropped d ON p.direction = d.direction AND p.sf_index = d.sf_index
ORDER BY p.direction, p.sf_index;"
```

---

## Per-Metric Queries

### Downstream latency max (all samples)
```sql
PGPASSWORD=postgres psql -h 172.30.80.33 -p 5433 -U postgres -d modem_metrics -c "
SELECT \"timestamp\", direction, sf_index, value as max_latency_usec, value/1000.0 as max_latency_ms
FROM dp_flow_queue_latency_max_usec
WHERE directionection = 'downstream'
ORDER BY \"timestamp\" DESC
LIMIT 20;"
```

### Upstream latency max
```sql
PGPASSWORD=postgres psql -h 172.30.80.33 -p 5433 -U postgres -d modem_metrics -c "
SELECT \"timestamp\", direction, sf_index, value as max_latency_usec, value/1000.0 as max_latency_ms
FROM dp_flow_queue_latency_max_usec
WHERE directionection = 'upstream'
ORDER BY \"timestamp\" DESC
LIMIT 20;"
```

### AQM drops over time
```sql
PGPASSWORD=postgres psql -h 172.30.80.33 -p 5433 -U postgres -d modem_metrics -c "
SELECT \"timestamp\", direction, sf_index, value as aqm_drops
FROM dp_flow_aqm_dropped_packets
WHERE value > 0
ORDER BY \"timestamp\" DESC
LIMIT 20;"
```

### Latency histogram bins (downstream, latest snapshot)
```sql
PGPASSWORD=postgres psql -h 172.30.80.33 -p 5433 -U postgres -d modem_metrics -c "
SELECT bin, edge_lower_msec, edge_upper_msec, value as pkt_count
FROM dp_flow_queue_latency_bin_pkt_count
WHERE directionection = 'downstream' AND sf_index = 1
  AND \"timestamp\" = (SELECT MAX(\"timestamp\") FROM dp_flow_queue_latency_bin_pkt_count)
ORDER BY bin;"
```

### QoS service flow packets — totals per direction
```sql
PGPASSWORD=postgres psql -h 172.30.80.33 -p 5433 -U postgres -d modem_metrics -c "
SELECT direction, sf_index, SUM(value) as total_packets
FROM qos_service_flow_packets
GROUP BY directionection, sf_index
ORDER BY directionection, sf_index;"
```

### Channel utilization
```sql
PGPASSWORD=postgres psql -h 172.30.80.33 -p 5433 -U postgres -d modem_metrics -c "
SELECT * FROM channel_utilization ORDER BY \"timestamp\" DESC LIMIT 10;"
```

### CM registration status
```sql
PGPASSWORD=postgres psql -h 172.30.80.33 -p 5433 -U postgres -d modem_metrics -c "
SELECT * FROM cm_reg_status_config ORDER BY \"timestamp\" DESC LIMIT 5;"
```

### Congestion marked packets
```sql
PGPASSWORD=postgres psql -h 172.30.80.33 -p 5433 -U postgres -d modem_metrics -c "
SELECT \"timestamp\", direction, sf_index, value as congestion_marked
FROM dp_flow_aqm_marked_congested_packets
WHERE value > 0
ORDER BY \"timestamp\" DESC
LIMIT 20;"
```

### Sanctioned packets
```sql
PGPASSWORD=postgres psql -h 172.30.80.33 -p 5433 -U postgres -d modem_metrics -c "
SELECT \"timestamp\", direction, sf_index, value as sanctioned
FROM dp_flow_sanctioned_packets
WHERE value > 0
ORDER BY \"timestamp\" DESC
LIMIT 20;"
```

---

## Time-Windowed Queries

### Latency stats for a specific time window
```sql
PGPASSWORD=postgres psql -h 172.30.80.33 -p 5433 -U postgres -d modem_metrics -c "
SELECT direction, sf_index,
       COUNT(*) as samples,
       ROUND(AVG(value)::numeric, 2) as avg_usec,
       ROUND((AVG(value)/1000)::numeric, 4) as avg_ms,
       ROUND(MAX(value)::numeric, 2) as max_usec,
       ROUND((MAX(value)/1000)::numeric, 4) as max_ms,
       ROUND((PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY value))::numeric, 2) as p99_usec
FROM dp_flow_queue_latency_max_usec
WHERE \"timestamp\" BETWEEN '2026-04-09 15:04:00' AND '2026-04-09 15:06:00'
  AND value > 0
GROUP BY directionection, sf_index
ORDER BY directionection, sf_index;"
```

### AQM drops in a time window
```sql
PGPASSWORD=postgres psql -h 172.30.80.33 -p 5433 -U postgres -d modem_metrics -c "
SELECT direction, sf_index,
       SUM(value) as total_aqm_drops,
       COUNT(*) as sample_count
FROM dp_flow_aqm_dropped_packets
WHERE \"timestamp\" BETWEEN '2026-04-09 15:04:00' AND '2026-04-09 15:06:00'
GROUP BY directionection, sf_index
ORDER BY directionection, sf_index;"
```

---

## Percentile Queries

### P50, P95, P99, P99.9 latency
```sql
PGPASSWORD=postgres psql -h 172.30.80.33 -p 5433 -U postgres -d modem_metrics -c "
SELECT direction, sf_index,
       ROUND((PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY value) / 1000)::numeric, 4) as p50_ms,
       ROUND((PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY value) / 1000)::numeric, 4) as p95_ms,
       ROUND((PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY value) / 1000)::numeric, 4) as p99_ms,
       ROUND((PERCENTILE_CONT(0.999) WITHIN GROUP (ORDER BY value) / 1000)::numeric, 4) as p999_ms,
       COUNT(*) as samples
FROM dp_flow_queue_latency_max_usec
WHERE value > 0
GROUP BY directionection, sf_index
ORDER BY directionection, sf_index;"
```

### P99 latency per 30s interval (time series)
```sql
PGPASSWORD=postgres psql -h 172.30.80.33 -p 5433 -U postgres -d modem_metrics -c "
SELECT date_trunc('minute', \"timestamp\") as interval,
       direction, sf_index,
       ROUND((MAX(value) / 1000)::numeric, 4) as max_latency_ms,
       ROUND((AVG(value) / 1000)::numeric, 4) as avg_latency_ms
FROM dp_flow_queue_latency_max_usec
WHERE directionection = 'downstream' AND value > 0
GROUP BY interval, direction, sf_index
ORDER BY interval DESC
LIMIT 20;"
```

---

## Filter by MAC / Cluster

### Summary by MAC and time window (matches vcmts_snapshot summary.csv)
```bash
PGPASSWORD=postgres psql -h 172.30.80.33 -p 5433 -U postgres -d modem_metrics -c "
SELECT q.directionection, q.sf_index,
       SUM(q.value) as total_packets,
       ROUND((AVG(CASE WHEN lat.value > 0 THEN lat.value END) / 1000)::numeric, 4) as avg_latency_ms,
       ROUND((MAX(lat.value) / 1000)::numeric, 4) as max_latency_ms,
       MAX(lat.value) as max_latency_usec,
       SUM(aqm.value) as aqm_dropped_pkts,
       SUM(cong.value) as aqm_marked_congested_pkts,
       SUM(sanc.value) as sanctioned_pkts,
       SUM(drp.value) as ksamis1_dropped_pkts
FROM qos_service_flow_packets q
LEFT JOIN dp_flow_queue_latency_max_usec lat ON q.directionection = lat.direction AND q.sf_index = lat.sf_index AND q.\"timestamp\" = lat.\"timestamp\" AND q.cm_mac_addr = lat.cm_mac_addr
LEFT JOIN dp_flow_aqm_dropped_packets aqm ON q.directionection = aqm.direction AND q.sf_index = aqm.sf_index AND q.\"timestamp\" = aqm.\"timestamp\" AND q.cm_mac_addr = aqm.cm_mac_addr
LEFT JOIN dp_flow_aqm_marked_congested_packets cong ON q.directionection = cong.direction AND q.sf_index = cong.sf_index AND q.\"timestamp\" = cong.\"timestamp\" AND q.cm_mac_addr = cong.cm_mac_addr
LEFT JOIN dp_flow_sanctioned_packets sanc ON q.directionection = sanc.directionection AND q.sf_index = sanc.sf_index AND q.\"timestamp\" = sanc.\"timestamp\" AND q.cm_mac_addr = sanc.cm_mac_addr
LEFT JOIN ksamis1_delta_packets_dropped drp ON q.directionection = drp.directionection AND q.sf_index = drp.sf_index AND q.\"timestamp\" = drp.\"timestamp\" AND q.cm_mac_addr = drp.cm_mac_addr
WHERE q.\"timestamp\" BETWEEN '2026-04-09 15:04:11.423' AND '2026-04-09 15:05:21.549'
  AND q.cm_mac_addr = 'e0:db:d1:61:3d:18'
GROUP BY q.directionection, q.sf_index
ORDER BY q.directionection, q.sf_index;"
```

### Latency over time by MAC
```bash
PGPASSWORD=postgres psql -h 172.30.80.33 -p 5433 -U postgres -d modem_metrics -c "
SELECT \"timestamp\", direction, sf_index, value as max_latency_usec, ROUND((value/1000)::numeric, 4) as max_latency_ms
FROM dp_flow_queue_latency_max_usec
WHERE \"timestamp\" BETWEEN '2026-04-09 15:04:11.423' AND '2026-04-09 15:05:21.549'
  AND cm_mac_addr = 'e0:db:d1:61:3d:18'
  AND value > 0
ORDER BY \"timestamp\", direction, sf_index;"
```

### AQM drops by MAC
```bash
PGPASSWORD=postgres psql -h 172.30.80.33 -p 5433 -U postgres -d modem_metrics -c "
SELECT \"timestamp\", direction, sf_index, value as aqm_drops
FROM dp_flow_aqm_dropped_packets
WHERE \"timestamp\" BETWEEN '2026-04-09 15:04:11.423' AND '2026-04-09 15:05:21.549'
  AND cm_mac_addr = 'e0:db:d1:61:3d:18'
  AND value > 0
ORDER BY \"timestamp\", direction, sf_index;"
```

### Latency bins by MAC
```bash
PGPASSWORD=postgres psql -h 172.30.80.33 -p 5433 -U postgres -d modem_metrics -c "
SELECT direction, sf_index, bin, edge_lower_msec, edge_upper_msec, SUM(value) as total_pkt_count
FROM dp_flow_queue_latency_bin_pkt_count
WHERE \"timestamp\" BETWEEN '2026-04-09 15:04:11.423' AND '2026-04-09 15:05:21.549'
  AND cm_mac_addr = 'e0:db:d1:61:3d:18'
GROUP BY directionection, sf_index, bin, edge_lower_msec, edge_upper_msec
ORDER BY directionection, sf_index, bin;"
```

### Percentiles by MAC
```bash
PGPASSWORD=postgres psql -h 172.30.80.33 -p 5433 -U postgres -d modem_metrics -c "
SELECT direction, sf_index,
       ROUND((PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY value) / 1000)::numeric, 4) as p50_ms,
       ROUND((PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY value) / 1000)::numeric, 4) as p95_ms,
       ROUND((PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY value) / 1000)::numeric, 4) as p99_ms,
       ROUND((PERCENTILE_CONT(0.999) WITHIN GROUP (ORDER BY value) / 1000)::numeric, 4) as p999_ms,
       COUNT(*) as samples
FROM dp_flow_queue_latency_max_usec
WHERE \"timestamp\" BETWEEN '2026-04-09 15:04:11.423' AND '2026-04-09 15:05:21.549'
  AND cm_mac_addr = 'e0:db:d1:61:3d:18'
  AND value > 0
GROUP BY directionection, sf_index
ORDER BY directionection, sf_index;"
```

### Throughput by MAC
```bash
PGPASSWORD=postgres psql -h 172.30.80.33 -p 5433 -U postgres -d modem_metrics -c "
SELECT direction, sf_index,
       SUM(value) as total_packets,
       ROUND((SUM(value) * 8000 / EXTRACT(EPOCH FROM ('2026-04-09 15:05:21.549'::timestamp - '2026-04-09 15:04:11.423'::timestamp)))::numeric, 2) as throughput_bps,
       ROUND((SUM(value) * 8 / EXTRACT(EPOCH FROM ('2026-04-09 15:05:21.549'::timestamp - '2026-04-09 15:04:11.423'::timestamp)) / 1000)::numeric, 4) as throughput_mbps
FROM qos_service_flow_packets
WHERE \"timestamp\" BETWEEN '2026-04-09 15:04:11.423' AND '2026-04-09 15:05:21.549'
  AND cm_mac_addr = 'e0:db:d1:61:3d:18'
GROUP BY directionection, sf_index
ORDER BY directionection, sf_index;"
```

### If tables have cm_mac_addr column
```sql
PGPASSWORD=postgres psql -h 172.30.80.33 -p 5433 -U postgres -d modem_metrics -c "
SELECT \"timestamp\", direction, sf_index, value
FROM dp_flow_queue_latency_max_usec
WHERE cm_mac_addr = '20:6a:94:92:23:b8'
  AND direction = 'downstream'
ORDER BY \"timestamp\" DESC
LIMIT 10;"
```

---

## Export to CSV

```bash
PGPASSWORD=postgres psql -h 172.30.80.33 -p 5433 -U postgres -d modem_metrics -c "
COPY (
    SELECT direction, sf_index, \"timestamp\", value as max_latency_usec
    FROM dp_flow_queue_latency_max_usec
    ORDER BY \"timestamp\"
) TO STDOUT WITH CSV HEADER" > latency_export.csv
```

---

## Delete / Cleanup

### Delete all data (reset)
```sql
PGPASSWORD=postgres psql -h 172.30.80.33 -p 5433 -U postgres -d modem_metrics -c "
TRUNCATE channel_utilization, cm_reg_status_config, dp_flow_aqm_dropped_packets,
         dp_flow_aqm_marked_congested_packets, dp_flow_queue_latency_bin_pkt_count,
         dp_flow_queue_latency_max_usec, dp_flow_sanctioned_packets,
         ksamis1_delta_packets_dropped, ksamis1_service_time_created,
         qos_service_flow_packets;"
```

### Delete data older than 7 days
```sql
PGPASSWORD=postgres psql -h 172.30.80.33 -p 5433 -U postgres -d modem_metrics -c "
DELETE FROM dp_flow_queue_latency_max_usec WHERE \"timestamp\" < NOW() - INTERVAL '7 days';
DELETE FROM dp_flow_aqm_dropped_packets WHERE \"timestamp\" < NOW() - INTERVAL '7 days';
DELETE FROM qos_service_flow_packets WHERE \"timestamp\" < NOW() - INTERVAL '7 days';"
```
