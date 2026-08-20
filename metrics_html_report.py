"""
metrics_html_report.py
======================
Generates an interactive HTML report from a CM Collector session directory.
All charts use Plotly — hover for values, zoom, pan, toggle series.

Usage:
    python metrics_html_report.py                        # auto-finds latest session
    python metrics_html_report.py 206a949223b8           # specific MAC
    python metrics_html_report.py path/to/session/dir    # specific session directory
"""
import os
import sys
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from metrics_pdf_report import (
    find_session, _load_csv, _load_kafka_csv, _apply_kafka_sfid_labels,
    _load_cmts_lookup, _delta_mb, _delta_col, _get_edge_labels,
)

# ---------------------------------------------------------------------------
# Theme — matches PDF dark theme
# ---------------------------------------------------------------------------
COLORS   = ['#1a73e8', '#34a853', '#fa7b17', '#ea4335', '#a142f4', '#24c1e0', '#f538a0']
BG       = '#0d1b2a'
BG_PANEL = '#112240'
GRID     = '#1e3a5f'
TEXT     = '#e8eaed'
SUBTEXT  = '#8ab4f8'

LAYOUT = dict(
    paper_bgcolor=BG, plot_bgcolor=BG_PANEL,
    font=dict(color=TEXT, size=11),
    legend=dict(bgcolor=BG_PANEL, bordercolor=GRID, borderwidth=1),
    xaxis=dict(gridcolor=GRID, zerolinecolor=GRID),
    yaxis=dict(gridcolor=GRID, zerolinecolor=GRID),
    hovermode='x unified',
    margin=dict(l=60, r=40, t=60, b=60),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _apply(fig, title='', height=480):
    fig.update_layout(**LAYOUT, title=dict(text=title, font=dict(size=14, color=TEXT)), height=height)
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID)
    return fig


def _color(i):
    return COLORS[i % len(COLORS)]


def _section(title):
    return f'<h2 style="color:{SUBTEXT};font-family:monospace;margin:32px 0 8px">{title}</h2>'


# ---------------------------------------------------------------------------
# Chart builders — each returns a Plotly Figure
# ---------------------------------------------------------------------------
def fig_throughput(df, direction, source):
    """Line chart: Mbps over time per sfid_label."""
    fig = go.Figure()
    grp_col = 'sfid_label'
    x_col   = 'captured_utc'
    if 'delta_octets' in df.columns and df['delta_octets'].notna().any():
        df = df.copy()
        df['_ts_ms'] = pd.to_numeric(df['kafka_timestamp_ms'], errors='coerce')
        df['_iv']    = df.groupby(grp_col)['_ts_ms'].transform(lambda s: s.diff() / 1000).clip(lower=1)
        df['mbps']   = pd.to_numeric(df['delta_octets'], errors='coerce').clip(lower=0) * 8 / df['_iv'] / 1e6
        y_col = 'mbps'
    elif 'flow_octets' in df.columns:
        df = _delta_mb(df, 'flow_octets')
        y_col = 'flow_octets'
    else:
        return None
    active = df.groupby(grp_col)[y_col].sum()
    active = active[active > 0].index
    df = df[df[grp_col].isin(active)]
    if df.empty:
        return None
    for i, (name, grp) in enumerate(df.groupby(grp_col)):
        grp = grp.sort_values(x_col)
        c   = _color(i)
        fig.add_trace(go.Scatter(
            x=grp[x_col], y=grp[y_col], name=str(name), mode='lines+markers',
            line=dict(color=c, width=2), marker=dict(size=5, color=c),
            hovertemplate='%{x}<br>%{y:.2f} Mbps<extra>' + str(name) + '</extra>',
        ))
    return _apply(fig, f'{direction} THROUGHPUT — {source} (Mbps)')


def fig_latency_avg(df, direction, source):
    """Line chart: avg latency ms over time."""
    fig  = go.Figure()
    col  = 'lat_avg_usec'
    x_col = 'captured_utc'
    grp_col = 'sfid_label'
    if col not in df.columns or df[col].isna().all():
        return None
    df = df.copy()
    df[col] = pd.to_numeric(df[col], errors='coerce') / 1000
    active = df.groupby(grp_col)[col].sum()
    active = active[active > 0].index
    df = df[df[grp_col].isin(active)]
    if df.empty:
        return None
    for i, (name, grp) in enumerate(df.groupby(grp_col)):
        grp = grp.sort_values(x_col)
        c   = _color(i)
        fig.add_trace(go.Scatter(
            x=grp[x_col], y=grp[col], name=str(name), mode='lines+markers',
            line=dict(color=c, width=2), marker=dict(size=5, color=c),
            hovertemplate='%{x}<br>%{y:.3f} ms<extra>' + str(name) + '</extra>',
        ))
    return _apply(fig, f'{direction} LATENCY AVG — {source} (ms)')


def fig_latency_percentile(df, direction, source):
    """P50 + P99 latency ms over time per sfid."""
    bin_cols = [f'lat_bin{i}' for i in range(1, 17)]
    present  = [c for c in bin_cols if c in df.columns]
    if not present:
        return None
    has_bins = df[present].notna().any(axis=1)
    df = df[has_bins].copy().sort_values('captured_utc')
    if df.empty:
        return None

    def _pct(row, edges, pct):
        counts = [float(pd.to_numeric(row.get(c, 0), errors='coerce') or 0) for c in present]
        total  = sum(counts)
        if total == 0:
            return float('nan')
        target, cumul = total * pct, 0
        for i, cnt in enumerate(counts):
            cumul += cnt
            if cumul >= target:
                lo = edges[i] if i < len(edges) else edges[-1]
                hi = edges[i+1] if i+1 < len(edges) else edges[-1]*2
                return (lo + hi) / 2
        return edges[-1] if edges else float('nan')

    fig = go.Figure()
    for idx, (sfid, grp) in enumerate(df.groupby('sfid_label')):
        elabels = _get_edge_labels(grp, len(present))
        edges   = [0.0]
        for lbl in elabels:
            try:
                if lbl.startswith('<'):    edges.append(float(lbl[1:]))
                elif lbl.startswith('>'): edges.append(float(lbl[1:])*2)
                elif '\u2013' in lbl:     edges.append(float(lbl.split('\u2013')[1]))
                else:                     edges.append(float(lbl))
            except ValueError:            edges.append(edges[-1]+1)
        rows = [{'t': row['captured_utc'],
                 'p50': _pct(row, edges, 0.50),
                 'p99': _pct(row, edges, 0.99)} for _, row in grp.iterrows()]
        rdf = pd.DataFrame(rows).dropna(subset=['p50','p99'], how='all').sort_values('t')
        c   = _color(idx)
        fig.add_trace(go.Scatter(
            x=rdf['t'], y=rdf['p50'], name=f'{sfid} P50', mode='lines+markers',
            line=dict(color=c, width=2), marker=dict(size=5),
            hovertemplate='%{x}<br>P50: %{y:.3f} ms<extra>' + str(sfid) + '</extra>',
        ))
        fig.add_trace(go.Scatter(
            x=rdf['t'], y=rdf['p99'], name=f'{sfid} P99', mode='lines+markers',
            line=dict(color=c, width=2, dash='dash'), marker=dict(size=5),
            hovertemplate='%{x}<br>P99: %{y:.3f} ms<extra>' + str(sfid) + '</extra>',
            fill='tonexty', fillcolor=c.replace(')', ',0.07)').replace('rgb', 'rgba').replace('#', 'rgba(').replace('rgba(', 'rgba(') if False else 'rgba(0,0,0,0)',
        ))
    return _apply(fig, f'{direction} P50 & P99 LATENCY — {source} (ms)')


def fig_latency_histogram(df, direction, source):
    """Bar chart per sfid: bin delta counts with edge labels as hover."""
    bin_cols = [f'lat_bin{i}' for i in range(1, 17)]
    present  = [c for c in bin_cols if c in df.columns]
    if not present:
        return None
    has_bins = df[present].notna().any(axis=1)
    df = df[has_bins].copy()
    if df.empty:
        return None
    groups = list(df.groupby('sfid_label'))
    n = len(groups)
    if n == 0:
        return None
    fig = make_subplots(rows=n, cols=1, subplot_titles=[str(s) for s, _ in groups],
                        vertical_spacing=0.08)
    x = list(range(1, len(present)+1))
    for row_i, (sfid, grp) in enumerate(groups, 1):
        grp = grp.sort_values('captured_utc')
        totals = [max((pd.to_numeric(grp[c].iloc[-1], errors='coerce') or 0) -
                      (pd.to_numeric(grp[c].iloc[0],  errors='coerce') or 0), 0)
                  for c in present]
        elabels = _get_edge_labels(grp, len(present))
        c = _color(row_i - 1)
        fig.add_trace(go.Bar(
            x=x, y=totals, name=str(sfid),
            marker_color=c, marker_line_color=BG, marker_line_width=0.5,
            customdata=elabels,
            hovertemplate='Bin %{x} (%{customdata})<br>Packets: %{y:,}<extra>' + str(sfid) + '</extra>',
        ), row=row_i, col=1)
    _apply(fig, f'{direction} LATENCY BINS — {source}', height=320*n)
    fig.update_xaxes(title_text='Bin', gridcolor=GRID)
    fig.update_yaxes(title_text='Packets (delta)', gridcolor=GRID)
    return fig


def fig_latency_heatmap(df, direction, source):
    """Heatmap: x=time, y=bin, color=packet count per sfid."""
    bin_cols = [f'lat_bin{i}' for i in range(1, 17)]
    present  = [c for c in bin_cols if c in df.columns]
    if not present:
        return None
    has_bins = df[present].notna().any(axis=1)
    df = df[has_bins].copy()
    groups = [(s, g) for s, g in df.groupby('sfid_label')
              if g[present].fillna(0).sum().sum() > 0]
    if not groups:
        return None
    n = len(groups)
    fig = make_subplots(rows=n, cols=1, subplot_titles=[str(s) for s, _ in groups],
                        vertical_spacing=0.1)
    for row_i, (sfid, grp) in enumerate(groups, 1):
        grp = grp.sort_values('captured_utc')
        mat = grp[present].apply(pd.to_numeric, errors='coerce').fillna(0).values.T
        times   = grp['captured_utc'].dt.strftime('%H:%M:%S').tolist()
        elabels = _get_edge_labels(grp, len(present))
        fig.add_trace(go.Heatmap(
            z=mat, x=times, y=elabels,
            colorscale='YlOrRd', showscale=True,
            hovertemplate='Time: %{x}<br>Bin: %{y}<br>Packets: %{z:,}<extra>' + str(sfid) + '</extra>',
            name=str(sfid),
        ), row=row_i, col=1)
    _apply(fig, f'{direction} LATENCY HEATMAP — {source}', height=350*n)
    return fig


def fig_scatter_latency(df, direction, source):
    """Scatter: x=time, y=latency ms, dot size=packet count."""
    lat_col = 'lat_avg_usec'
    pkt_col = 'flow_pkts'
    if lat_col not in df.columns or df[lat_col].isna().all():
        return None
    df = df.copy()
    df[lat_col] = pd.to_numeric(df[lat_col], errors='coerce') / 1000
    has = df[lat_col].notna() & (df[lat_col] > 0)
    if not has.any():
        return None
    df = df[has].copy()
    active = df.groupby('sfid_label')[lat_col].sum()
    active = active[active > 0].index
    df = df[df['sfid_label'].isin(active)]
    if df.empty:
        return None
    fig = go.Figure()
    for i, (name, grp) in enumerate(df.groupby('sfid_label')):
        grp = grp.sort_values('captured_utc')
        if pkt_col in grp.columns:
            pkts  = pd.to_numeric(grp[pkt_col], errors='coerce').fillna(1).clip(lower=1)
            sizes = (pkts / pkts.max() * 30 + 6).clip(upper=40)
        else:
            sizes = 12
        fig.add_trace(go.Scatter(
            x=grp['captured_utc'], y=grp[lat_col], name=str(name),
            mode='markers',
            marker=dict(size=sizes, color=_color(i), opacity=0.85,
                        line=dict(color='white', width=0.5)),
            hovertemplate='%{x}<br>Latency: %{y:.3f} ms<extra>' + str(name) + '</extra>',
        ))
    return _apply(fig, f'{direction} LATENCY SCATTER — {source} (dot size = pkt count)')


def fig_area_stack(df, direction, source):
    """Stacked area: total bandwidth across all sfids."""
    grp_col = 'sfid_label'
    x_col   = 'captured_utc'
    if 'delta_octets' in df.columns and df['delta_octets'].notna().any():
        df = df.copy()
        df['_ts_ms'] = pd.to_numeric(df['kafka_timestamp_ms'], errors='coerce')
        df['_iv']    = df.groupby(grp_col)['_ts_ms'].transform(lambda s: s.diff()/1000).clip(lower=1)
        df['mbps']   = pd.to_numeric(df['delta_octets'], errors='coerce').clip(lower=0)*8/df['_iv']/1e6
        y_col = 'mbps'
    elif 'flow_octets' in df.columns:
        df = _delta_mb(df, 'flow_octets')
        y_col = 'flow_octets'
    else:
        return None
    groups = [(n, g.sort_values(x_col)) for n, g in df.groupby(grp_col)
              if g[y_col].notna().any() and g[y_col].sum() > 0]
    if not groups:
        return None
    fig = go.Figure()
    for i, (name, grp) in enumerate(groups):
        fig.add_trace(go.Scatter(
            x=grp[x_col], y=grp[y_col], name=str(name),
            mode='lines', stackgroup='one',
            line=dict(color=_color(i), width=1),
            fillcolor=_color(i),
            hovertemplate='%{x}<br>%{y:.2f} Mbps<extra>' + str(name) + '</extra>',
        ))
    return _apply(fig, f'{direction} THROUGHPUT STACKED AREA — {source} (Mbps)')


def fig_congestion(df, direction, source):
    """AQM drop + CE marked over time."""
    drop_col   = 'cong_aqm_drop'
    marked_col = 'cong_ce_marked'
    cols = [c for c in [drop_col, marked_col] if c in df.columns and not df[c].isna().all()]
    if not cols:
        return None
    fig = go.Figure()
    grp_col = 'sfid_label'
    for i, (name, grp) in enumerate(df.groupby(grp_col)):
        grp = grp.sort_values('captured_utc')
        c   = _color(i)
        if drop_col in cols:
            fig.add_trace(go.Scatter(
                x=grp['captured_utc'], y=pd.to_numeric(grp[drop_col], errors='coerce'),
                name=f'{name} AQM drop', mode='lines+markers',
                line=dict(color=c, width=2),
                hovertemplate='%{x}<br>AQM drop: %{y:,}<extra>' + str(name) + '</extra>',
            ))
        if marked_col in cols:
            fig.add_trace(go.Scatter(
                x=grp['captured_utc'], y=pd.to_numeric(grp[marked_col], errors='coerce'),
                name=f'{name} CE marked', mode='lines+markers',
                line=dict(color=c, width=2, dash='dash'),
                hovertemplate='%{x}<br>CE marked: %{y:,}<extra>' + str(name) + '</extra>',
            ))
    return _apply(fig, f'{direction} CONGESTION — {source}')


# ---------------------------------------------------------------------------
# HTML assembly
# ---------------------------------------------------------------------------
def _fig_html(fig):
    if fig is None:
        return ''
    return pio.to_html(fig, full_html=False, include_plotlyjs=False,
                       config={'displayModeBar': True, 'scrollZoom': True})


def generate_html_report(sess, session_name='Report'):
    cmts_type = sess['cmts_type']
    mac       = sess['mac']
    mac_fmt   = ':'.join(mac[i:i+2] for i in range(0, 12, 2))

    # Load data
    us    = _load_csv(sess['us_path']) if sess.get('us_path') else pd.DataFrame()
    k_us  = pd.DataFrame()
    k_ds  = pd.DataFrame()
    ds    = pd.DataFrame()

    if cmts_type == 'vcmts' and sess.get('kafka_path'):
        k_us, k_ds = _load_kafka_csv(sess['kafka_path'])
        sfid_map   = _load_cmts_lookup(sess['session_dir'], mac)
        k_us = _apply_kafka_sfid_labels(k_us, sfid_map)
        k_ds = _apply_kafka_sfid_labels(k_ds, sfid_map)
    elif sess.get('ds_path'):
        ds = _load_csv(sess['ds_path'])

    out_path = os.path.join(
        sess['session_dir'],
        f'report_{cmts_type}_{mac}_{session_name.replace(" ","_")}.html'
    )

    sections = []

    def _add_section(title):
        sections.append(('header', title))

    def _add(title, fig):
        if fig:
            sections.append(('chart', _fig_html(fig)))

    # US SNMP
    if not us.empty:
        _add_section('&#9650; UPSTREAM — SNMP')
        _add('Throughput',          fig_throughput(us, 'US', 'SNMP'))
        _add('Throughput Stacked',  fig_area_stack(us, 'US', 'SNMP'))
        _add('Latency Avg',         fig_latency_avg(us, 'US', 'SNMP'))
        _add('P50 & P99',           fig_latency_percentile(us, 'US', 'SNMP'))
        _add('Latency Scatter',     fig_scatter_latency(us, 'US', 'SNMP'))
        _add('Latency Bins',        fig_latency_histogram(us, 'US', 'SNMP'))
        _add('Latency Heatmap',     fig_latency_heatmap(us, 'US', 'SNMP'))
        _add('Congestion',          fig_congestion(us, 'US', 'SNMP'))

    if not k_us.empty:
        _add_section('&#9650; UPSTREAM — KAFKA')
        _add('Throughput',          fig_throughput(k_us, 'US', 'Kafka'))
        _add('Throughput Stacked',  fig_area_stack(k_us, 'US', 'Kafka'))
        _add('Latency Avg',         fig_latency_avg(k_us, 'US', 'Kafka'))
        _add('P50 & P99',           fig_latency_percentile(k_us, 'US', 'Kafka'))
        _add('Latency Scatter',     fig_scatter_latency(k_us, 'US', 'Kafka'))
        _add('Latency Bins',        fig_latency_histogram(k_us, 'US', 'Kafka'))
        _add('Latency Heatmap',     fig_latency_heatmap(k_us, 'US', 'Kafka'))
        _add('Congestion',          fig_congestion(k_us, 'US', 'Kafka'))

    if not k_ds.empty:
        _add_section('&#9660; DOWNSTREAM — KAFKA')
        _add('Throughput',          fig_throughput(k_ds, 'DS', 'Kafka'))
        _add('Throughput Stacked',  fig_area_stack(k_ds, 'DS', 'Kafka'))
        _add('Latency Avg',         fig_latency_avg(k_ds, 'DS', 'Kafka'))
        _add('P50 & P99',           fig_latency_percentile(k_ds, 'DS', 'Kafka'))
        _add('Latency Scatter',     fig_scatter_latency(k_ds, 'DS', 'Kafka'))
        _add('Latency Bins',        fig_latency_histogram(k_ds, 'DS', 'Kafka'))
        _add('Latency Heatmap',     fig_latency_heatmap(k_ds, 'DS', 'Kafka'))
        _add('Congestion',          fig_congestion(k_ds, 'DS', 'Kafka'))

    if not ds.empty:
        _add_section('&#9660; DOWNSTREAM — SNMP')
        _add('Throughput',          fig_throughput(ds, 'DS', 'SNMP'))
        _add('Throughput Stacked',  fig_area_stack(ds, 'DS', 'SNMP'))
        _add('Latency Bins',        fig_latency_histogram(ds, 'DS', 'SNMP'))
        _add('Latency Heatmap',     fig_latency_heatmap(ds, 'DS', 'SNMP'))
        _add('Congestion',          fig_congestion(ds, 'DS', 'SNMP'))

    body = []
    for kind, content in sections:
        if kind == 'header':
            body.append(f'<h2 style="color:{SUBTEXT};font-family:monospace;margin:32px 0 8px">{content}</h2>')
        else:
            body.append(f'<div class="chart">{content}</div>')

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{session_name} — {mac_fmt}</title>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<style>
  body  {{ background:{BG}; color:{TEXT}; font-family:monospace; margin:0; padding:24px; }}
  h1    {{ color:{SUBTEXT}; border-bottom:1px solid {GRID}; padding-bottom:8px; }}
  h2    {{ color:{SUBTEXT}; margin-top:32px; }}
  .chart{{ background:{BG_PANEL}; border:1px solid {GRID}; border-radius:6px;
           padding:12px; margin-bottom:24px; }}
</style>
</head>
<body>
<h1>{session_name} &nbsp;|&nbsp; {mac_fmt} &nbsp;|&nbsp; {cmts_type.upper()}</h1>
{''.join(body)}
</body>
</html>"""

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'HTML saved: {out_path}')
    return out_path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    import re
    args         = sys.argv[1:]
    session_arg  = None
    session_name = None
    i = 0
    while i < len(args):
        if args[i] == '--name' and i + 1 < len(args):
            session_name = args[i+1]; i += 2
        else:
            session_arg = args[i]; i += 1

    sess = find_session(session_arg)
    if session_name is None:
        if sys.stdin.isatty():
            session_name = input('Session name [Enter for default]: ').strip()
        if not session_name:
            session_name = f'{sess["cmts_type"].upper()} Report'

    generate_html_report(sess, session_name)


if __name__ == '__main__':
    main()
