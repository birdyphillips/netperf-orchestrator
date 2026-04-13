# modem_metrics.py
cd "C:\Users\p3135123\OneDrive - Charter Communications\Access_Engineering_Project\modem_metrics"
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python modem_metrics.py vcmts-snapshot --since "2026-04-09 15:04:11.423" --until "2026-04-09 15:05:21.549" --cm-mac e0db.d161.3d18

# HSI016_DS_Classic
python modem_metrics.py vcmts-snapshot --utc --since "2026-04-09T15:04:11.423" --until "2026-04-09T15:05:21.549" --cm-mac e0db.d161.3d18 -o ".\vcmts_snapshot\HSI016_DS_Classic"
# HSI016_US_Classic
python modem_metrics.py vcmts-snapshot --utc --since "2026-04-09T15:02:07.302" --until "2026-04-09T15:03:17.352" --cm-mac e0db.d161.3d18 -o ".\vcmts_snapshot\HSI016_US_Classic"

# HSI018_DS_Classic
python modem_metrics.py vcmts-snapshot --utc --since "2026-04-08T14:47:54.951" --until "2026-04-08T14:49:06.036" --cm-mac 0cb9.3764.3ab0 -o ".\vcmts_snapshot\HSI018_DS_Classic"
# HSI018_US_Classic
python modem_metrics.py vcmts-snapshot --utc --since "2026-04-08T15:11:15.922" --until "2026-04-08T15:12:25.959" --cm-mac 0cb9.3764.3ab0 -o ".\vcmts_snapshot\HSI018_US_Classic"

# HSI021_DS_Classic
python modem_metrics.py vcmts-snapshot --utc --since "2026-04-09T15:08:29.296" --until "2026-04-09T15:09:40.616" --cm-mac 206a.9492.23b8 -o ".\vcmts_snapshot\HSI021_DS_Classic"
# HSI021_US_Classic
python modem_metrics.py vcmts-snapshot --utc --since "2026-04-09T15:06:26.162" --until "2026-04-09T15:07:38.173" --cm-mac 206a.9492.23b8 -o ".\vcmts_snapshot\HSI021_US_Classic"

# HSI029_DS_Classic
python modem_metrics.py vcmts-snapshot --utc --since "2026-04-08T17:59:43.320" --until "2026-04-08T18:00:53.344" --cm-mac 802b.f9fa.ee17 -o ".\vcmts_snapshot\HSI029_DS_Classic"
# HSI029_US_Classic
python modem_metrics.py vcmts-snapshot --utc --since "2026-04-08T17:57:30.327" --until "2026-04-08T17:58:40.530" --cm-mac 802b.f9fa.ee17 -o ".\vcmts_snapshot\HSI029_US_Classic"



# Full snapshot with deltas (CSV + Excel)
python modem_metrics.py vcmts-snapshot --since "2026-04-09T15:02:07.302" --until "2026-04-09 15:05:21.549"

# With a specific modem MAC filter
python modem_metrics.py vcmts-snapshot --since "2026-04-09 15:04:11.423" --until "2026-04-09T15:03:17.352" --cm-mac 

# Query individual tables within that window
python modem_metrics.py query flow_stats --since "2026-04-09 15:04:11.423" -n 100
python modem_metrics.py query channel_utilization --since "2026-04-09 15:04:11.423" -n 100
python modem_metrics.py query qos_service_flow_packets --since "2026-04-09 15:04:11.423" -n 100
python modem_metrics.py query dp_flow_aqm_dropped_packets --since "2026-04-09 15:04:11.423" -n 100

# Raw SQL for the exact window
python modem_metrics.py sql "SELECT * FROM flow_stats WHERE time >= '2026-04-09 15:04:11.423' AND time <= '2026-04-09 15:05:21.549' ORDER BY time"
python modem_metrics.py sql "SELECT * FROM channel_utilization WHERE timestamp >= '2026-04-09 15:04:11.423' AND timestamp <= '2026-04-09 15:05:21.549' ORDER BY timestamp"





CLI tool for querying the `modem_metrics` PostgreSQL database.

## Querying with Timestamps

### Timestamp Columns

| Table Group | Time Column |
|---|---|
| CM Metrics (`flow_stats`, `histogram_stats`, `vcmts_sfid_info`, `agg_flow_stats`, `congestion_stats`) | `time` |
| vCMTS Metrics (all others) | `timestamp` |

### `--since` — Filter rows after a timestamp

Use `--since` with the `query` command to return only rows at or after the given timestamp:

```bash
# Rows from a specific date onward
python modem_metrics.py query flow_stats --since "2024-01-01"

# Rows from a precise time onward
python modem_metrics.py query channel_utilization --since "2024-06-15 08:00:00"
```

### `--since` / `--until` — Time-windowed snapshots

The `vcmts-snapshot` command computes deltas across all vCMTS and CM metrics tables between two timestamps:

```bash
python modem_metrics.py vcmts-snapshot --since "2024-06-15 08:00:00" --until "2024-06-15 09:00:00"
```

Filter to a single modem:

```bash
python modem_metrics.py vcmts-snapshot \
    --since "2024-06-15 08:00:00" \
    --until "2024-06-15 09:00:00" \
    --cm-mac 0cb9.3764.3ab0
```

Output goes to `./vcmts_snapshot/` (CSV + Excel) by default. Override with `-o`:

```bash
python modem_metrics.py vcmts-snapshot --since "2024-06-15 08:00:00" --until "2024-06-15 09:00:00" -o ./my_output
```

### Combining timestamps with other filters

```bash
# Rows since a date for a specific MAC and direction
python modem_metrics.py query qos_service_flow_packets \
    --since "2024-06-15" --cm-mac 0cb9.3764.3ab0 --direction upstream

# Custom ORDER BY and limit
python modem_metrics.py query flow_stats --since "2024-01-01" -n 50 -o "time ASC"

# Output as CSV
python modem_metrics.py query flow_stats --since "2024-01-01" --csv
```

### Arbitrary SQL with timestamps

```bash
python modem_metrics.py sql "SELECT * FROM flow_stats WHERE time >= '2024-06-15' ORDER BY time DESC LIMIT 5"
```

## Other Commands

```bash
python modem_metrics.py tables              # List all tables
python modem_metrics.py describe flow_stats  # Show table schema
python modem_metrics.py count flow_stats     # Row count
```

## Requirements

- Python 3.7+
- `psycopg2`
- `openpyxl` (for Excel export in `vcmts-snapshot`)
