"""
metrics_pdf_report.py
=====================
Generates a PDF report from a CM Collector session directory.
Supports both iCMTS (snmp_us + snmp_ds) and vCMTS (snmp_us + kafka) sessions.

Usage:
    python metrics_pdf_report.py                        # auto-finds latest session in results/
    python metrics_pdf_report.py 206a949223b8           # specific MAC (latest session)
    python metrics_pdf_report.py path/to/session/dir    # specific session directory
    python metrics_pdf_report.py path/to/snmp_us_*.csv  # specific US CSV

Requirements:
    pip install pandas matplotlib
"""
import os
import sys
import glob
import re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------
CHART_COLORS = ['#1a73e8', '#34a853', '#fa7b17', '#ea4335', '#a142f4', '#24c1e0', '#f538a0']
BG_DARK      = '#0d1b2a'
BG_PANEL     = '#112240'
GRID_COLOR   = '#1e3a5f'
TEXT_COLOR   = '#e8eaed'
SUBTEXT      = '#e8eaed'
ACCENT       = '#1a73e8'

MODEM_NAMES  = {
    '0cb9379c64b4': 'Lab CM (iCMTS)',
    '206a949223b8': 'Lab CM (vCMTS)',
}

# ---------------------------------------------------------------------------
# Session discovery — returns a session dict
# ---------------------------------------------------------------------------
def _session_from_dir(d):
    """Inspect a directory and return a session dict, or None if not a valid session."""
    us_files    = sorted(glob.glob(os.path.join(d, 'snmp_us_*.csv')))
    ds_files    = sorted(glob.glob(os.path.join(d, 'snmp_ds_*.csv')))
    kafka_files = sorted(glob.glob(os.path.join(d, 'kafka_*.csv')))
    if not us_files:
        return None

    us_path    = us_files[-1]
    ds_path    = ds_files[-1] if ds_files else None
    kafka_path = kafka_files[-1] if kafka_files else None

    # Determine type and MAC from directory name or filename
    mac_m = re.search(r'([0-9a-f]{12})', os.path.basename(us_path))
    mac   = mac_m.group(1) if mac_m else 'unknown'

    # vcmts: has kafka  |  icmts: no kafka
    if kafka_path:
        cmts_type = 'vcmts'
    elif us_path:
        cmts_type = 'icmts'
    else:
        return None

    # For icmts with no separate ds file, DS SFIDs live in the snmp_us file (sf_direction=1)
    if cmts_type == 'icmts' and not ds_path:
        ds_path = us_path

    return {
        'cmts_type':   cmts_type,
        'mac':         mac,
        'us_path':     us_path,
        'ds_path':     ds_path,
        'kafka_path':  kafka_path,
        'session_dir': d,
    }


def find_session(arg=None):
    """Locate a session and return its session dict."""

    def _latest_session(mac_glob):
        dirs = sorted(glob.glob(os.path.join(HERE, 'results', mac_glob, '*')))
        for d in reversed(dirs):
            if os.path.isdir(d):
                s = _session_from_dir(d)
                if s:
                    return s
        return None

    if arg:
        # Explicit CSV file — derive session dir from it
        if arg.endswith('.csv'):
            path = arg if os.path.isabs(arg) else os.path.join(HERE, arg)
            s = _session_from_dir(os.path.dirname(path))
            if s:
                return s
            print(f'Could not build session from: {path}')
            sys.exit(1)

        # Session directory
        if os.path.isdir(arg):
            s = _session_from_dir(arg)
            if s:
                return s
            print(f'No valid session files found in {arg}')
            sys.exit(1)

        # MAC address
        mac = re.sub(r'[:\-.]', '', arg).lower()
        s = _latest_session(f'{mac}_*')
        if s:
            return s
        print(f'No session found for MAC {mac}')
        sys.exit(1)

    # Auto-find latest session across all MACs
    dirs = sorted(glob.glob(os.path.join(HERE, 'results', '*', '*')))
    for d in reversed(dirs):
        if os.path.isdir(d):
            s = _session_from_dir(d)
            if s:
                return s

    print('No valid session found under results/')
    sys.exit(1)

# ---------------------------------------------------------------------------
# Chart helpers
# ---------------------------------------------------------------------------
def fmt_ax(ax):
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', color=TEXT_COLOR)
    ax.grid(True, color=GRID_COLOR, linewidth=0.7, linestyle='--', alpha=0.8)
    ax.set_axisbelow(True)

def style_ax(ax):
    ax.set_facecolor(BG_PANEL)
    ax.tick_params(colors=TEXT_COLOR, labelsize=9)
    ax.xaxis.label.set_color(SUBTEXT)
    ax.yaxis.label.set_color(SUBTEXT)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID_COLOR)

def add_header(fig, title, subtitle=None):
    hax = fig.add_axes([0, 0.91, 1, 0.09])
    hax.set_facecolor(ACCENT)
    hax.axis('off')
    hax.text(0.5, 0.62, title,
             transform=hax.transAxes, fontsize=16, fontweight='bold',
             color='white', ha='center', va='center', fontfamily='DejaVu Sans')
    if subtitle:
        lines = subtitle.split('\n')
        if len(lines) > 1:
            hax.text(0.5, 0.22, lines[0],
                     transform=hax.transAxes, fontsize=7.5,
                     color=TEXT_COLOR, ha='center', va='center', fontstyle='italic')
            hax.text(0.5, 0.02, lines[1],
                     transform=hax.transAxes, fontsize=7.5,
                     color=TEXT_COLOR, ha='center', va='center', fontstyle='italic')
        else:
            hax.text(0.5, 0.15, subtitle,
                     transform=hax.transAxes, fontsize=8,
                     color=TEXT_COLOR, ha='center', va='center', fontstyle='italic')

def add_footer(fig, mac_fmt, modem_name, session_start, session_end, cmts_type='iCMTS'):
    fax = fig.add_axes([0, 0, 1, 0.04])
    fax.set_facecolor('#0a1628')
    fax.axis('off')
    fax.text(0.5, 0.5,
             f'{cmts_type.upper()} SNMP Report  |  {modem_name} ({mac_fmt})  |  {session_start} — {session_end}  |  aphillips — Charter Access Engineering',
             transform=fax.transAxes, fontsize=7, color='#445566',
             ha='center', va='center')

def make_fig():
    fig, ax = plt.subplots(figsize=(11, 5.8), subplot_kw={'facecolor': BG_PANEL})
    fig.patch.set_facecolor(BG_DARK)
    fig.subplots_adjust(top=0.88, bottom=0.18, left=0.11, right=0.97)
    style_ax(ax)
    return fig, ax

def save_page(pdf, fig, ax, header_title, subtitle, mac_fmt, modem_name, session_start, session_end, cmts_type='iCMTS'):
    add_header(fig, header_title, subtitle)
    add_footer(fig, mac_fmt, modem_name, session_start, session_end, cmts_type)
    pdf.savefig(fig, facecolor=fig.get_facecolor())
    plt.close(fig)

def _smooth_xy(x, y):
    """Smooth (x, y) using Pchip interpolation — monotone, no overshoot, no negatives.
    Works well with as few as 3 points. Returns original if scipy unavailable.
    """
    try:
        from scipy.interpolate import PchipInterpolator
    except ImportError:
        return x, y
    import numpy as np

    if hasattr(x, 'iloc'):
        if hasattr(x.iloc[0], 'timestamp'):
            xn = np.array([v.timestamp() for v in x])
        else:
            xn = np.array(x, dtype=float)
    else:
        xn = np.array(x, dtype=float)

    yn = pd.to_numeric(y, errors='coerce').values.astype(float)
    mask = ~np.isnan(yn)
    xc, yc = xn[mask], yn[mask]
    # also drop non-finite x
    finite = np.isfinite(xc)
    xc, yc = xc[finite], yc[finite]

    # sort by x, then average duplicate x values
    order = np.argsort(xc)
    xc, yc = xc[order], yc[order]
    unique_x, inv = np.unique(xc, return_inverse=True)
    unique_y = np.array([yc[inv == i].mean() for i in range(len(unique_x))])
    xc, yc = unique_x, unique_y

    if len(xc) < 3:
        return x, y

    xs = np.linspace(xc[0], xc[-1], max(len(xc) * 12, 120))
    ys = PchipInterpolator(xc, yc)(xs)
    ys = np.clip(ys, 0, None)  # never go below zero

    if hasattr(x, 'iloc') and hasattr(x.iloc[0], 'timestamp'):
        xs = pd.to_datetime(xs, unit='s', utc=True).tz_convert(None)

    return xs, ys


def plot_line(ax, df, y_col, group_col, ylabel, poll_col='poll_index'):
    """Smooth Pchip curve through every poll point, raw dots overlaid."""
    x_col = 'captured_utc' if 'captured_utc' in df.columns else poll_col
    for i, (name, grp) in enumerate(df.groupby(group_col)):
        color = CHART_COLORS[i % len(CHART_COLORS)]
        rx = grp[x_col]
        ry = pd.to_numeric(grp[y_col], errors='coerce')
        sx, sy = _smooth_xy(rx, ry)
        ax.plot(sx, sy, linewidth=2, color=color, label=str(name))
        ax.fill_between(sx, sy, alpha=0.10, color=color)
        ax.plot(rx, ry, marker='o', markersize=5, linewidth=0, color=color,
                markerfacecolor='white', markeredgecolor=color, markeredgewidth=1.8)
    ax.set_ylabel(ylabel, color=SUBTEXT, fontsize=10, fontweight='bold')
    ax.set_xlabel('Time (UTC)', color=SUBTEXT, fontsize=10)
    ax.legend(fontsize=8, facecolor=BG_DARK, edgecolor=GRID_COLOR,
              labelcolor=TEXT_COLOR, framealpha=0.9)
    fmt_ax(ax)

def plot_dual(ax, df, col_a, col_b, label_a, label_b, group_col, ylabel):
    """Two metrics per group — smooth Pchip curves, solid for col_a, dashed for col_b."""
    for i, (name, grp) in enumerate(df.groupby(group_col)):
        c  = CHART_COLORS[i % len(CHART_COLORS)]
        rx = grp['captured_utc']
        ra = pd.to_numeric(grp[col_a], errors='coerce')
        rb = pd.to_numeric(grp[col_b], errors='coerce')
        sx_a, sa = _smooth_xy(rx, ra)
        sx_b, sb = _smooth_xy(rx, rb)
        ax.plot(sx_a, sa, linewidth=2,   color=c, label=f'{name} {label_a}')
        ax.plot(sx_b, sb, linewidth=1.5, color=c, label=f'{name} {label_b}',
                linestyle='--', alpha=0.8)
        ax.plot(rx, ra, marker='o', markersize=4, linewidth=0, color=c,
                markerfacecolor='white', markeredgecolor=c, markeredgewidth=1.5)
        ax.plot(rx, rb, marker='x', markersize=4, linewidth=0, color=c, alpha=0.8)
    ax.set_ylabel(ylabel, color=SUBTEXT, fontsize=10, fontweight='bold')
    ax.set_xlabel('Time (UTC)', color=SUBTEXT, fontsize=10)
    ax.legend(fontsize=7, facecolor=BG_DARK, edgecolor=GRID_COLOR,
              labelcolor=TEXT_COLOR, framealpha=0.9, ncol=2)
    fmt_ax(ax)

# ---------------------------------------------------------------------------
# Page builders — Cover + TOC
# ---------------------------------------------------------------------------
def page_cover(pdf, mac_fmt, modem_name, session_start, session_end,
               duration_str, total_polls, us_sfids, ds_sfids, cmts_type='icmts', session_name=None):
    fig = plt.figure(figsize=(11, 8.5))
    fig.patch.set_facecolor(BG_PANEL)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor(BG_PANEL)
    ax.axis('off')

    title_str = 'vCMTS SNMP SESSION REPORT' if cmts_type == 'vcmts' else 'iCMTS SNMP SESSION REPORT'
    sub_str   = 'Charter Communications  •  Access Engineering  •  vCMTS EFT' if cmts_type == 'vcmts' \
                else 'Charter Communications  •  Access Engineering  •  iCMTS EFT'

    ax.text(0.5, 0.935, title_str,
            transform=ax.transAxes, fontsize=26, fontweight='bold',
            color='white', ha='center', va='center', fontfamily='DejaVu Sans')
    ax.text(0.5, 0.865, sub_str,
            transform=ax.transAxes, fontsize=12, color=TEXT_COLOR,
            ha='center', va='center', fontfamily='DejaVu Sans', fontstyle='italic')
    if session_name:
        ax.text(0.5, 0.815, session_name,
                transform=ax.transAxes, fontsize=14, fontweight='bold',
                color=ACCENT, ha='center', va='center', fontfamily='DejaVu Sans')
    ax.axhline(y=0.79, xmin=0.05, xmax=0.95, color=ACCENT, linewidth=1.5)

    ds_label = 'Kafka (DS)' if cmts_type == 'vcmts' else ', '.join(str(s) for s in sorted(ds_sfids))
    labels = [
        ('Modem',         modem_name),
        ('Modem MAC',     mac_fmt),
        ('CMTS Type',     cmts_type.upper()),
        ('Session Start', session_start),
        ('Session End',   session_end),
        ('Duration',      duration_str),
        ('Total Polls',   str(total_polls)),
        ('US SFIDs',      ', '.join(str(s) for s in sorted(us_sfids))),
        ('DS SFIDs',      ds_label),
    ]
    y = 0.72
    for label, value in labels:
        ax.text(0.12, y, f'{label}:', transform=ax.transAxes,
                fontsize=11, color=SUBTEXT, fontweight='bold', va='center')
        ax.text(0.38, y, value, transform=ax.transAxes,
                fontsize=11, color='white', va='center', fontfamily='monospace')
        y -= 0.062

    ax.text(0.5, 0.02,
            f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}   |   aphillips — Charter Access Engineering',
            transform=ax.transAxes, fontsize=8, color='#445566', ha='center', va='center')

    pdf.savefig(fig, facecolor=fig.get_facecolor())
    plt.close(fig)


def page_toc(pdf, mac_fmt, modem_name, session_start, session_end, contents, cmts_type='icmts'):
    fig = plt.figure(figsize=(11, 8.5))
    fig.patch.set_facecolor(BG_PANEL)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor(BG_PANEL)
    ax.axis('off')

    ax.text(0.5, 0.935, 'TABLE OF CONTENTS',
            transform=ax.transAxes, fontsize=22, fontweight='bold',
            color='white', ha='center', va='center', fontfamily='DejaVu Sans')
    ax.axhline(y=0.88, xmin=0.03, xmax=0.97, color=ACCENT, linewidth=1)

    # Two-column layout
    half     = (len(contents) + 1) // 2
    col_defs = [(0.03, 0.50), (0.52, 0.99)]  # (x_start, divider_x) per column
    gap      = min(0.075, 0.78 / max(half, 1))

    for col_idx, entries in enumerate([contents[:half], contents[half:]]):
        x0 = col_defs[col_idx][0]
        pg_x    = x0 + 0.04
        title_x = x0 + 0.09
        y = 0.84
        for i, (page, title, desc) in enumerate(entries):
            row_color = '#112240' if i % 2 == 0 else '#0d1b2a'
            ax.axhspan(y - gap * 0.4, y + gap * 0.55,
                       xmin=col_defs[col_idx][0], xmax=col_defs[col_idx][1],
                       facecolor=row_color, alpha=1.0)
            ax.text(pg_x, y + 0.005, f'pg {page}',
                    transform=ax.transAxes, fontsize=8, fontweight='bold',
                    color=ACCENT, va='center', ha='center',
                    bbox=dict(boxstyle='round,pad=0.25', facecolor='#0d2a4a',
                              edgecolor=ACCENT, linewidth=0.8))
            ax.text(title_x, y + 0.005, title,
                    transform=ax.transAxes, fontsize=9, fontweight='bold',
                    color=TEXT_COLOR, va='center', fontfamily='DejaVu Sans')
            ax.text(title_x, y - gap * 0.38, desc,
                    transform=ax.transAxes, fontsize=7,
                    color=SUBTEXT, va='center', fontstyle='italic')
            ax.axhline(y=y - gap * 0.4,
                       xmin=col_defs[col_idx][0], xmax=col_defs[col_idx][1],
                       color=GRID_COLOR, linewidth=0.5, linestyle=':')
            y -= gap

    # Vertical divider between columns
    ax.axvline(x=0.505, ymin=0.06, ymax=0.88, color=GRID_COLOR, linewidth=0.8, linestyle='--')

    label = cmts_type.upper()
    ax.text(0.5, 0.02,
            f'{label} SNMP Report  |  {modem_name} ({mac_fmt})  |  {session_start} — {session_end}',
            transform=ax.transAxes, fontsize=8, color='#445566', ha='center', va='center')

    pdf.savefig(fig, facecolor=fig.get_facecolor())
    plt.close(fig)

# ---------------------------------------------------------------------------
# ThousandEyes dedicated page
# ---------------------------------------------------------------------------
def page_thousandeyes(pdf, te_dir, **m):
    """Full-page ThousandEyes results — one page per iteration JSON found."""
    te_results = _load_te_results(te_dir)
    if not te_results:
        return

    for te in te_results:
        iteration  = te.get('iteration', 1)
        unit_id    = te.get('unit_id', 'N/A')
        test_group = te.get('test_group', 'N/A')
        timestamp  = te.get('timestamp', '')[:19].replace('T', ' ')
        results    = te.get('results', {})
        summary    = te.get('summary', {})

        ds   = results.get('http_get_mt', {})
        us   = results.get('http_post_mt', {})
        jit  = results.get('udp_jitter', {})

        fig = plt.figure(figsize=(11, 8.5))
        fig.patch.set_facecolor(BG_DARK)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_facecolor(BG_DARK)
        ax.axis('off')

        # Header bar
        hax = fig.add_axes([0, 0.91, 1, 0.09])
        hax.set_facecolor('#34a853')
        hax.axis('off')
        hax.text(0.5, 0.62, 'THOUSANDEYES INSTANT TEST RESULTS',
                 transform=hax.transAxes, fontsize=16, fontweight='bold',
                 color='white', ha='center', va='center')
        hax.text(0.5, 0.18, f'{test_group}  |  Unit {unit_id}  |  Iteration {iteration}  |  {timestamp}',
                 transform=hax.transAxes, fontsize=8, color=TEXT_COLOR,
                 ha='center', va='center', fontstyle='italic')

        y = 0.84
        def _section(title, color=ACCENT):
            nonlocal y
            ax.axhline(y=y + 0.005, xmin=0.04, xmax=0.96, color=color, linewidth=1.2)
            ax.text(0.05, y - 0.012, title, transform=ax.transAxes,
                    fontsize=11, fontweight='bold', color=color, va='top')
            y -= 0.045

        def _row(label, raw, converted, unit_raw='', unit_conv=''):
            nonlocal y
            ax.text(0.07,  y, label,     transform=ax.transAxes, fontsize=9,  color=SUBTEXT,    va='top')
            ax.text(0.42,  y, f'{raw} {unit_raw}',   transform=ax.transAxes, fontsize=9,  color=TEXT_COLOR, va='top', fontfamily='monospace')
            ax.text(0.68,  y, f'{converted} {unit_conv}', transform=ax.transAxes, fontsize=10, color='white',    va='top', fontweight='bold', fontfamily='monospace')
            y -= 0.038

        def _meta(label, value):
            nonlocal y
            ax.text(0.07, y, label, transform=ax.transAxes, fontsize=8.5, color=SUBTEXT,    va='top')
            ax.text(0.28, y, value, transform=ax.transAxes, fontsize=8.5, color=TEXT_COLOR, va='top')
            y -= 0.030

        # Column headers
        ax.text(0.42, y, 'Raw Value',  transform=ax.transAxes, fontsize=8, color='#778899', va='top', fontstyle='italic')
        ax.text(0.68, y, 'Result',     transform=ax.transAxes, fontsize=8, color='#778899', va='top', fontstyle='italic')
        y -= 0.032

        # --- Downstream ---
        if ds:
            bps = ds.get('bytes_sec', 0)
            mbps = bps * 8 / 1_000_000
            gbps = bps * 8 / 1_000_000_000
            _section('DOWNSTREAM THROUGHPUT  (http_get_mt)', '#1a73e8')
            _meta('Target', ds.get('target', 'N/A'))
            _meta('MAC', ds.get('mac', 'N/A'))
            _meta('UTC Time', ds.get('utc_datetime', 'N/A'))
            y -= 0.008
            _row('Throughput', f'{bps:,} bytes/sec', f'{mbps:.2f} Mbps  /  {gbps:.4f} Gbps')
            y -= 0.010

        # --- Upstream ---
        if us:
            bps = us.get('bytes_sec', 0)
            mbps = bps * 8 / 1_000_000
            gbps = bps * 8 / 1_000_000_000
            _section('UPSTREAM THROUGHPUT  (http_post_mt)', '#fa7b17')
            _meta('Target', us.get('target', 'N/A'))
            _meta('MAC', us.get('mac', 'N/A'))
            _meta('UTC Time', us.get('utc_datetime', 'N/A'))
            y -= 0.008
            _row('Throughput', f'{bps:,} bytes/sec', f'{mbps:.2f} Mbps  /  {gbps:.4f} Gbps')
            y -= 0.010

        # --- Jitter / Latency ---
        if jit:
            lat_us  = jit.get('latency', 0)
            dj_us   = jit.get('down_jitter', 0)
            uj_us   = jit.get('up_jitter', 0)
            _section('UDP JITTER / LATENCY  (udp_jitter)', '#34a853')
            _meta('Target', jit.get('target', 'N/A'))
            _meta('MAC', jit.get('mac', 'N/A'))
            _meta('UTC Time', jit.get('utc_datetime', 'N/A'))
            y -= 0.008
            _row('Latency',     f'{lat_us} µs', f'{lat_us / 1000:.3f} ms')
            _row('Down Jitter', f'{dj_us} µs',  f'{dj_us  / 1000:.3f} ms')
            _row('Up Jitter',   f'{uj_us} µs',  f'{uj_us  / 1000:.3f} ms')
            y -= 0.010

        # --- Summary table ---
        _section('SUMMARY', ACCENT)
        col_labels = ['Metric', 'Raw Value', 'Mbps', 'Gbps', 'ms']
        col_widths = [0.28, 0.20, 0.14, 0.14, 0.14]
        table_rows = []
        if ds:
            b = ds.get('bytes_sec', 0)
            table_rows.append(['DS Throughput (TCP)', f'{b:,} B/s',
                                f'{b*8/1e6:.2f}', f'{b*8/1e9:.4f}', '—'])
        if us:
            b = us.get('bytes_sec', 0)
            table_rows.append(['US Throughput (TCP)', f'{b:,} B/s',
                                f'{b*8/1e6:.2f}', f'{b*8/1e9:.4f}', '—'])
        if jit:
            table_rows.append(['Latency',     f'{jit.get("latency",0)} µs',     '—', '—', f'{jit.get("latency",0)/1000:.3f}'])
            table_rows.append(['Down Jitter', f'{jit.get("down_jitter",0)} µs', '—', '—', f'{jit.get("down_jitter",0)/1000:.3f}'])
            table_rows.append(['Up Jitter',   f'{jit.get("up_jitter",0)} µs',   '—', '—', f'{jit.get("up_jitter",0)/1000:.3f}'])

        if table_rows:
            tbl_ax = fig.add_axes([0.04, 0.04, 0.92, max(0.02, y - 0.06)])
            tbl_ax.set_facecolor(BG_PANEL)
            tbl_ax.axis('off')
            tbl = tbl_ax.table(
                cellText=table_rows,
                colLabels=col_labels,
                colWidths=col_widths,
                loc='center', cellLoc='center',
            )
            tbl.auto_set_font_size(False)
            tbl.set_fontsize(9)
            tbl.scale(1, 1.8)
            for col in range(len(col_labels)):
                cell = tbl[0, col]
                cell.set_facecolor('#34a853')
                cell.set_text_props(color='white', fontweight='bold')
            for row_i in range(len(table_rows)):
                bg = BG_PANEL if row_i % 2 == 0 else BG_DARK
                for col in range(len(col_labels)):
                    cell = tbl[row_i + 1, col]
                    cell.set_facecolor(bg)
                    cell.set_text_props(color=TEXT_COLOR)
                    cell.set_edgecolor(GRID_COLOR)

        # Footer
        fax = fig.add_axes([0, 0, 1, 0.04])
        fax.set_facecolor('#0a1628')
        fax.axis('off')
        fax.text(0.5, 0.5,
                 f'ThousandEyes Report  |  {m["modem_name"]} ({m["mac_fmt"]})  |  {m["session_start"]} — {m["session_end"]}  |  aphillips — Charter Access Engineering',
                 transform=fax.transAxes, fontsize=7, color='#445566', ha='center', va='center')

        pdf.savefig(fig, facecolor=fig.get_facecolor())
        plt.close(fig)



def _calc_percentile(deltas, pct):
    total = sum(deltas)
    if total == 0:
        return 0.0
    target, cumulative = total * pct, 0
    for i, count in enumerate(deltas):
        cumulative += count
        if cumulative >= target:
            return i + 1  # bin number (1-indexed)
    return len(deltas)


def _calc_weighted_avg(deltas):
    total = sum(deltas)
    if total == 0:
        return 0.0
    return sum((i + 1) * v for i, v in enumerate(deltas)) / total


def _peak_mbps_kafka(grp):
    """Peak throughput from Kafka: max single-poll delta_octets / interval."""
    if 'delta_octets' not in grp.columns:
        return 0.0
    ts_ms = pd.to_numeric(grp['kafka_timestamp_ms'], errors='coerce')
    octets = pd.to_numeric(grp['delta_octets'], errors='coerce').clip(lower=0)
    intervals = ts_ms.diff() / 1000  # ms → s
    valid = (intervals > 0) & octets.notna()
    if not valid.any():
        return 0.0
    mbps_per_poll = octets[valid] * 8 / intervals[valid] / 1_000_000
    return float(mbps_per_poll.max())


def _peak_mbps_snmp(grp, poll_interval_s=15):
    """Peak throughput from SNMP: max per-poll delta of flow_octets."""
    if 'flow_octets' not in grp.columns:
        return 0.0
    octs = pd.to_numeric(grp['flow_octets'], errors='coerce')
    ts = grp['captured_utc']
    intervals = ts.diff().dt.total_seconds()
    deltas = octs.diff().clip(lower=0)
    valid = (intervals > 0) & deltas.notna()
    if not valid.any():
        return 0.0
    mbps_per_poll = deltas[valid] * 8 / intervals[valid] / 1_000_000
    return float(mbps_per_poll.max())


def _load_te_results(session_dir):
    """Load ThousandEyes JSON results from session dir. Returns list of result dicts."""
    import json
    te_files = sorted(glob.glob(os.path.join(session_dir, 'ThousandEyes_*.json')))
    # Also check one level up (parent dir)
    if not te_files:
        parent = os.path.dirname(session_dir)
        te_files = sorted(glob.glob(os.path.join(parent, 'ThousandEyes_*.json')))
    results = []
    for f in te_files:
        try:
            with open(f) as fh:
                results.append(json.load(fh))
        except Exception:
            pass
    return results


def page_summary(pdf, us, ds, k_us, k_ds, **m):
    """Summary page: CMTS poll-based throughput & latency table + ThousandEyes results."""
    cmts_type = m.get('cmts_type', 'icmts')
    sfid_map  = m.get('sfid_map', {})
    session_dir = m.get('session_dir', '')
    _sp = {k: m[k] for k in ('mac_fmt', 'modem_name', 'session_start', 'session_end')}
    _sp['cmts_type'] = cmts_type

    # Build per-SFID summary rows — throughput = PEAK poll, not session average
    rows = []  # (sfid_label, direction, source, peak_mbps, avg_lat_ms, max_lat_ms,
               #  p50_bin, p99_bin, p999_bin, aqm_drops, ce_marked, loss_pct)

    # SNMP US — peak per-poll throughput
    if us is not None and not us.empty:
        for sfid, grp in us.groupby('sfid'):
            grp = grp.sort_values('captured_utc')
            lbl = sfid_map.get(str(sfid), grp['sfid_label'].iloc[0] if 'sfid_label' in grp.columns else str(sfid))
            tp = _peak_mbps_snmp(grp)
            lat_max = pd.to_numeric(grp.get('lat_max_usec', pd.Series()), errors='coerce').max()
            lat_max_ms = lat_max / 1000 if pd.notna(lat_max) else 0
            bin_cols = [f'lat_bin{i}' for i in range(1, 17)]
            present  = [c for c in bin_cols if c in grp.columns]
            if present:
                last = grp.iloc[-1]
                deltas = [int(pd.to_numeric(last.get(c, 0), errors='coerce') or 0) if pd.notna(pd.to_numeric(last.get(c, 0), errors='coerce')) else 0 for c in present]
                p50  = _calc_percentile(deltas, 0.50)
                p99  = _calc_percentile(deltas, 0.99)
                p999 = _calc_percentile(deltas, 0.999)
                wavg = _calc_weighted_avg(deltas)
            else:
                p50 = p99 = p999 = wavg = 0
            aqm  = pd.to_numeric(grp.get('cong_aqm_drop',  pd.Series(dtype=float)), errors='coerce').sum()
            ce   = pd.to_numeric(grp.get('cong_ce_marked', pd.Series(dtype=float)), errors='coerce').sum()
            rows.append((lbl, 'US', 'SNMP', round(tp, 1), round(wavg, 3),
                         round(lat_max_ms, 3), p50, p99, p999,
                         int(aqm or 0), int(ce or 0), 0.0))

    # Kafka US + DS — peak per-poll throughput
    for kdf, direction, source in [(k_us, 'US', 'Kafka'), (k_ds, 'DS', 'Kafka')]:
        if kdf is None or kdf.empty:
            continue
        grp_col = 'sfid_label' if 'sfid_label' in kdf.columns else 'sfid'
        for sfid, grp in kdf.groupby(grp_col):
            grp = grp.sort_values('captured_utc')
            tp = _peak_mbps_kafka(grp)
            lat_avg = pd.to_numeric(grp.get('lat_avg_usec', pd.Series()), errors='coerce') / 1000
            avg_lat_ms = lat_avg[lat_avg > 0].mean() if not lat_avg[lat_avg > 0].empty else 0
            lat_max = pd.to_numeric(grp.get('lat_max_usec', pd.Series()), errors='coerce').max()
            lat_max_ms = lat_max / 1000 if pd.notna(lat_max) else 0
            bin_cols = [f'lat_bin{i}' for i in range(1, 17)]
            present  = [c for c in bin_cols if c in grp.columns]
            if present:
                last = grp.iloc[-1]
                deltas = [int(pd.to_numeric(last.get(c, 0), errors='coerce') or 0) if pd.notna(pd.to_numeric(last.get(c, 0), errors='coerce')) else 0 for c in present]
                p50  = _calc_percentile(deltas, 0.50)
                p99  = _calc_percentile(deltas, 0.99)
                p999 = _calc_percentile(deltas, 0.999)
                wavg = _calc_weighted_avg(deltas)
            else:
                p50 = p99 = p999 = wavg = avg_lat_ms
            aqm_raw = pd.to_numeric(grp.get('cong_aqm_drop', pd.Series(dtype=float)), errors='coerce').dropna()
            aqm = max(aqm_raw.max() - aqm_raw.min(), 0) if not aqm_raw.empty else 0
            ce_raw = pd.to_numeric(grp.get('cong_ce_marked', pd.Series(dtype=float)), errors='coerce').dropna()
            ce = max(ce_raw.max() - ce_raw.min(), 0) if not ce_raw.empty else 0
            pkts_pass = pd.to_numeric(grp.get('delta_pkts',         pd.Series(dtype=float)), errors='coerce').sum()
            pkts_drop = pd.to_numeric(grp.get('delta_pkts_dropped', pd.Series(dtype=float)), errors='coerce').sum()
            total_pkts = pkts_pass + pkts_drop
            loss_pct = (pkts_drop / total_pkts * 100) if total_pkts > 0 else 0.0
            rows.append((str(sfid), direction, source, round(tp, 1), round(avg_lat_ms, 3),
                         round(lat_max_ms, 3), p50, p99, p999,
                         int(aqm or 0), int(ce or 0), round(loss_pct, 3)))

    if not rows:
        return

    # --- ThousandEyes results ---
    te_results = _load_te_results(session_dir)
    te_rows = []  # (test_name, direction, mbps, latency_ms, jitter_ms)
    for te in te_results:
        for test_name, data in te.get('results', {}).items():
            if test_name == 'http_get_mt':
                bps = data.get('bytes_sec', 0)
                mbps = round(bps * 8 / 1_000_000, 2)
                te_rows.append(('http_get_mt (DS)', 'DS', f'{mbps} Mbps', '—', '—'))
            elif test_name == 'http_post_mt':
                bps = data.get('bytes_sec', 0)
                mbps = round(bps * 8 / 1_000_000, 2)
                te_rows.append(('http_post_mt (US)', 'US', f'{mbps} Mbps', '—', '—'))
            elif test_name == 'udp_jitter':
                lat_ms = round(data.get('latency', 0) / 1000, 3)
                dj_ms  = round(data.get('down_jitter', 0) / 1000, 3)
                uj_ms  = round(data.get('up_jitter', 0) / 1000, 3)
                te_rows.append(('udp_jitter', 'DS/US', '—', f'{lat_ms} ms', f'↓{dj_ms} ↑{uj_ms} ms'))

    # --- Layout: CMTS table top, TE table bottom (if present) ---
    fig = plt.figure(figsize=(11, 8.5))
    fig.patch.set_facecolor(BG_DARK)

    # Determine vertical split
    te_table_h = 0.22 if te_rows else 0
    cmts_top   = 0.08 + te_table_h
    cmts_h     = 0.78 - te_table_h

    ax = fig.add_axes([0.03, cmts_top, 0.94, cmts_h])
    ax.set_facecolor(BG_PANEL)
    ax.axis('off')

    col_labels = ['SFID / Service Class', 'Dir', 'Src', 'Peak\nMbps', 'WAvg\n(ms)', 'Max\n(ms)',
                  'P50\nbin', 'P99\nbin', 'P99.9\nbin', 'AQM\nDrop', 'CE\nMark', 'Loss%']
    col_widths = [0.20, 0.05, 0.06, 0.07, 0.07, 0.07, 0.06, 0.06, 0.07, 0.07, 0.07, 0.06]

    table_data = [[str(v) for v in r] for r in rows]

    tbl = ax.table(
        cellText=table_data,
        colLabels=col_labels,
        colWidths=col_widths,
        loc='center',
        cellLoc='center',
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8)
    tbl.scale(1, 1.6)

    for col in range(len(col_labels)):
        cell = tbl[0, col]
        cell.set_facecolor(ACCENT)
        cell.set_text_props(color='white', fontweight='bold')

    for row_i in range(len(rows)):
        bg = BG_PANEL if row_i % 2 == 0 else BG_DARK
        for col in range(len(col_labels)):
            cell = tbl[row_i + 1, col]
            cell.set_facecolor(bg)
            cell.set_text_props(color=TEXT_COLOR)
            cell.set_edgecolor(GRID_COLOR)

    # --- ThousandEyes table ---
    if te_rows:
        te_ax = fig.add_axes([0.03, 0.04, 0.94, te_table_h - 0.02])
        te_ax.set_facecolor(BG_PANEL)
        te_ax.axis('off')
        te_col_labels = ['ThousandEyes Test', 'Dir', 'Throughput', 'Latency', 'Jitter']
        te_col_widths = [0.28, 0.08, 0.20, 0.20, 0.24]
        te_tbl = te_ax.table(
            cellText=te_rows,
            colLabels=te_col_labels,
            colWidths=te_col_widths,
            loc='center',
            cellLoc='center',
        )
        te_tbl.auto_set_font_size(False)
        te_tbl.set_fontsize(8)
        te_tbl.scale(1, 1.5)
        for col in range(len(te_col_labels)):
            cell = te_tbl[0, col]
            cell.set_facecolor('#34a853')
            cell.set_text_props(color='white', fontweight='bold')
        for row_i in range(len(te_rows)):
            bg = BG_PANEL if row_i % 2 == 0 else BG_DARK
            for col in range(len(te_col_labels)):
                cell = te_tbl[row_i + 1, col]
                cell.set_facecolor(bg)
                cell.set_text_props(color=TEXT_COLOR)
                cell.set_edgecolor(GRID_COLOR)

    save_page(pdf, fig, ax, 'SESSION SUMMARY — THROUGHPUT & LATENCY',
              f'{m["modem_name"]} ({m["mac_fmt"]})  |  Peak Mbps from polls  |  Weighted Avg latency, P50/P99/P99.9 bin, AQM drops',
              **_sp)


# ---------------------------------------------------------------------------
# US chart pages
# ---------------------------------------------------------------------------
def _meta(mac_fmt, modem_name, session_start, session_end):
    return mac_fmt, modem_name, session_start, session_end


def _delta_mb(df, col):
    """Return df with col replaced by per-sfid poll-to-poll throughput in Mbps.
    Uses actual captured_utc interval per poll; drops first row per SFID (no valid interval).
    Retains _interval_s column for downstream total-GB calculation.
    """
    df = df.copy().sort_values(['sfid', 'captured_utc'])
    df[col] = pd.to_numeric(df[col], errors='coerce')
    df['_interval_s'] = df.groupby('sfid')['captured_utc'].transform(
        lambda s: s.diff().dt.total_seconds())
    df['_delta'] = df.groupby('sfid')[col].diff().clip(lower=0)
    df = df[df['_interval_s'] > 0].copy()
    df[col] = df['_delta'] * 8 / df['_interval_s'] / 1e6
    df = df.drop(columns=['_delta'])
    return df


def _total_gb_label(df, col):
    """Two-line subtitle string: total GB per sfid_label over session.
    col is already Mbps; multiply by _interval_s to get Mb, divide by 1000 for GB.
    """
    df = df.copy()
    df[col] = pd.to_numeric(df[col], errors='coerce')
    label_map = df.groupby('sfid')['sfid_label'].first()
    totals = (df.groupby('sfid').apply(
        lambda g: (g[col] * g['_interval_s']).sum() / 1000
    ) if '_interval_s' in df.columns else df.groupby('sfid')[col].sum() * 15 / 1000)
    parts = [f'{label_map.get(s, s)}: {v:.2f} GB' for s, v in totals.items()]
    half = (len(parts) + 1) // 2
    line1 = '  |  '.join(parts[:half])
    line2 = '  |  '.join(parts[half:])
    return f'{line1}\n{line2}' if line2 else line1


def _delta_col(df, col):
    """Return df copy with col replaced by per-sfid poll-to-poll delta (clipped ≥ 0).
    Always groups by 'sfid' (stable numeric key) so label changes don't break diffs.
    """
    df = df.copy().sort_values(['sfid', 'captured_utc'])
    df[col] = pd.to_numeric(df[col], errors='coerce')
    df[col] = df.groupby('sfid')[col].diff().clip(lower=0)
    return df


def page_us_flow_stats(pdf, us, **m):
    """US flow pkts, octets, policed drop/delay, AQM drop."""
    _sp = {k: m[k] for k in ('mac_fmt','modem_name','session_start','session_end')}
    _sp['cmts_type'] = m.get('cmts_type', 'icmts')

    if 'flow_octets' in us.columns and not us['flow_octets'].isna().all():
        us_d = _delta_mb(us, 'flow_octets')
        fig, ax = make_fig()
        plot_line(ax, us_d, 'flow_octets', 'sfid_label', 'Throughput (Mbps)')
        save_page(pdf, fig, ax, 'US FLOW THROUGHPUT — SNMP (Mbps)',
                  f'{m["modem_name"]} ({m["mac_fmt"]})  |  {_total_gb_label(us_d, "flow_octets")}', **_sp)

    if all(c in us.columns for c in ('flow_policed_drop', 'flow_policed_delay')):
        us_pd = _delta_col(_delta_col(us, 'flow_policed_drop'), 'flow_policed_delay')
        fig, ax = make_fig()
        plot_dual(ax, us_pd, 'flow_policed_drop', 'flow_policed_delay',
                  'drop', 'delay', 'sfid_label', 'Packets (delta)')
        save_page(pdf, fig, ax, 'US POLICED DROP & DELAY (SNMP)',
                  f'{m["modem_name"]} ({m["mac_fmt"]})  |  US Service Flows — per-poll delta', **_sp)

    if 'flow_aqm_drop' in us.columns and not us['flow_aqm_drop'].isna().all():
        us_aqm = _delta_col(us, 'flow_aqm_drop')
        fig, ax = make_fig()
        plot_line(ax, us_aqm, 'flow_aqm_drop', 'sfid_label', 'Packets (delta)')
        save_page(pdf, fig, ax, 'US AQM DROPPED PACKETS (SNMP)',
                  f'{m["modem_name"]} ({m["mac_fmt"]})  |  US Service Flows — per-poll delta', **_sp)


def page_us_latency_avg(pdf, us, **m):
    """US weighted average latency (ms) per poll derived from bin deltas and edge values."""
    bin_cols  = [f'lat_bin{i}'      for i in range(1, 17)]
    edge_cols = [f'lat_edge_bin{i}' for i in range(1, 16)]
    present_bins  = [c for c in bin_cols  if c in us.columns]
    present_edges = [c for c in edge_cols if c in us.columns]
    if not present_bins or not present_edges:
        return

    us = us.copy().sort_values(['sfid', 'captured_utc'])
    for c in present_bins:
        us[c] = pd.to_numeric(us[c], errors='coerce')
        us[c] = us.groupby('sfid')[c].diff().clip(lower=0)

    # Build midpoints from edges: [0, e1, e2, ..., e15, e15*2] → midpoint of each bin
    def _wavg_row(row):
        edges = [pd.to_numeric(row.get(e, None), errors='coerce') for e in present_edges]
        edges = [e for e in edges if pd.notna(e)]
        if not edges:
            return float('nan')
        boundaries = [0] + edges + [edges[-1] * 2]
        midpoints  = [(boundaries[i] + boundaries[i+1]) / 2 for i in range(len(present_bins))]
        counts = [float(row.get(c, 0) or 0) for c in present_bins]
        total  = sum(counts)
        if total == 0:
            return float('nan')
        return sum(m * c for m, c in zip(midpoints, counts)) / total / 1000  # usec → ms

    us['_lat_avg_ms'] = us.apply(_wavg_row, axis=1)
    us = us.dropna(subset=['_lat_avg_ms'])
    if us.empty or us['_lat_avg_ms'].eq(0).all():
        return

    _sp = {k: m[k] for k in ('mac_fmt','modem_name','session_start','session_end')}
    _sp['cmts_type'] = m.get('cmts_type', 'icmts')
    fig, ax = make_fig()
    plot_line(ax, us, '_lat_avg_ms', 'sfid_label', 'Latency (ms)')
    save_page(pdf, fig, ax, 'US LATENCY AVG (ms) — SNMP',
              f'{m["modem_name"]} ({m["mac_fmt"]})  |  Weighted avg from bin deltas per poll', **_sp)



def _get_edge_labels(grp, n_bins):
    """Return n_bins x-axis label strings using lat_edge_bin upper edges.
    Kafka: lat_edge_bin1..16 = upper bound of each bin → labels '<e1', 'e1–e2', ...
    SNMP:  lat_edge_bin1..15 = boundaries between bins → same logic, last bin '>e15'.
    Falls back to bin numbers if no edge columns present.
    """
    # Try 16 edges (Kafka per-bin upper bounds) then 15 (SNMP boundaries)
    edge_cols_16 = [f'lat_edge_bin{i}' for i in range(1, 17)]
    edge_cols_15 = [f'lat_edge_bin{i}' for i in range(1, 16)]
    present_16 = [c for c in edge_cols_16 if c in grp.columns]
    present_15 = [c for c in edge_cols_15 if c in grp.columns]
    present = present_16 if len(present_16) >= len(present_15) else present_15
    if not present:
        return [str(i) for i in range(1, n_bins + 1)]
    edge_row = grp[present].dropna(how='all')
    if edge_row.empty:
        return [str(i) for i in range(1, n_bins + 1)]
    edges = [pd.to_numeric(edge_row[c].iloc[0], errors='coerce') for c in present]
    edges = [e for e in edges if pd.notna(e) and e < float('inf')]
    if not edges:
        return [str(i) for i in range(1, n_bins + 1)]
    def _fmt(v):
        return str(int(v)) if v == int(v) else f'{v:.4g}'
    labels = [f'<{_fmt(edges[0])}'] if edges else ['<?']
    for i in range(len(edges) - 1):
        labels.append(f'{_fmt(edges[i])}–{_fmt(edges[i+1])}')
    labels.append(f'>{_fmt(edges[-1])}')
    while len(labels) < n_bins:
        labels.append(str(len(labels) + 1))
    return labels[:n_bins]


def _plot_bin_timeseries(pdf, df, direction, group_col, bin_cols, bar_color, source='SNMP', **m):  # noqa: E501
    """One chart per SFID: bar chart of total bin counts over session, x-axis = bin edge ranges."""
    _sp = {k: m[k] for k in ('mac_fmt','modem_name','session_start','session_end')}
    _sp['cmts_type'] = m.get('cmts_type', 'icmts')
    n_bins = len(bin_cols)
    x = list(range(1, n_bins + 1))
    # Group by sfid_label for display but use sfid for SNMP last-minus-first delta
    for sfid_lbl, grp in df.groupby(group_col):
        # Resolve stable sfid for this label group
        sfid_key = grp['sfid'].iloc[0] if 'sfid' in grp.columns else sfid_lbl
        sfid_rows = df[df['sfid'] == sfid_key].sort_values('captured_utc') \
                    if 'sfid' in df.columns else grp.sort_values('captured_utc')
        grp = sfid_rows.copy()
        if grp.empty:
            continue
        # Kafka bins are per-poll deltas — sum all non-NaN rows
        # SNMP bins are cumulative — last minus first (using sfid-resolved rows)
        if source == 'Kafka':
            totals = [max(pd.to_numeric(grp[c], errors='coerce').fillna(0).sum(), 0)
                      for c in bin_cols]
        else:
            totals = [max((pd.to_numeric(grp[c].iloc[-1], errors='coerce') or 0) -
                          (pd.to_numeric(grp[c].iloc[0], errors='coerce') or 0), 0)
                      for c in bin_cols]
        edge_labels = _get_edge_labels(grp, n_bins)
        colors = CHART_COLORS[:n_bins] if n_bins <= len(CHART_COLORS) \
                 else [CHART_COLORS[i % len(CHART_COLORS)] for i in range(n_bins)]
        fig, ax = make_fig()
        ax.bar(x, totals, color=colors, edgecolor=BG_DARK, linewidth=0.5, width=0.7)
        ax.set_xticks(x)
        ax.set_xticklabels([str(b) for b in x], color=TEXT_COLOR, fontsize=8)
        ax.set_ylabel('Packets (total delta)', color=SUBTEXT, fontsize=10, fontweight='bold')
        ax.set_xlabel('Bin', color=SUBTEXT, fontsize=10)
        ax.grid(True, color=GRID_COLOR, linewidth=0.7, linestyle='--', alpha=0.8, axis='y')
        ax.set_axisbelow(True)
        ax.tick_params(colors=TEXT_COLOR)
        for spine in ax.spines.values():
            spine.set_edgecolor(GRID_COLOR)
        # Side legend showing bin number → edge range (only when real edges available)
        if edge_labels[0] != '1':
            from matplotlib.patches import Patch
            legend_handles = [Patch(facecolor=colors[i], edgecolor=BG_DARK,
                                    label=f'Bin {x[i]}: {edge_labels[i]}') for i in range(n_bins)]
            ax.legend(handles=legend_handles, loc='upper left', bbox_to_anchor=(1.01, 1),
                      borderaxespad=0, fontsize=7, framealpha=0.85,
                      facecolor=BG_DARK, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR)
            fig.subplots_adjust(right=0.72)
        save_page(pdf, fig, ax,
                  f'{direction} LATENCY BINS ({source}) — {sfid_lbl}',
                  f'{m["modem_name"]} ({m["mac_fmt"]})  |  last poll − first poll delta per bin',
                  **_sp)


def page_us_latency_histogram(pdf, us, **m):
    """US latency bin time-series — one chart per SFID."""
    bin_cols = [f'lat_bin{i}' for i in range(1, 17)]
    present  = [c for c in bin_cols if c in us.columns]
    if not present:
        return
    group_col = 'sfid_label'
    _plot_bin_timeseries(pdf, us, 'US', group_col, present, ACCENT, **m)


def page_us_congestion(pdf, us, **m):
    """US congestion — AQM drop, CE marked, ECT0/ECT1 — per-poll deltas grouped by sfid."""
    cong_cols = ['cong_aqm_drop', 'cong_ce_marked', 'cong_ect0', 'cong_ect1',
                 'cong_scn_marked', 'cong_sanctioned']
    present = [c for c in cong_cols if c in us.columns and not us[c].isna().all()]
    if not present:
        return

    _sp = {k: m[k] for k in ('mac_fmt','modem_name','session_start','session_end')}
    _sp['cmts_type'] = m.get('cmts_type', 'icmts')

    # Diff all congestion counters by sfid so every flow is represented correctly
    us_d = us.copy().sort_values(['sfid', 'captured_utc'])
    for c in present:
        us_d[c] = pd.to_numeric(us_d[c], errors='coerce')
        us_d[c] = us_d.groupby('sfid')[c].diff().clip(lower=0)

    if 'cong_aqm_drop' in present and 'cong_ce_marked' in present:
        fig, ax = make_fig()
        plot_dual(ax, us_d, 'cong_aqm_drop', 'cong_ce_marked',
                  'AQM drop', 'CE marked', 'sfid_label', 'Packets (delta)')
        save_page(pdf, fig, ax, 'US CONGESTION — AQM DROPS & CE MARKED (SNMP)',
                  f'{m["modem_name"]} ({m["mac_fmt"]})  |  per-poll delta per SFID', **_sp)

    if 'cong_ect0' in present and 'cong_ect1' in present:
        fig, ax = make_fig()
        plot_dual(ax, us_d, 'cong_ect0', 'cong_ect1',
                  'ECT(0)', 'ECT(1)', 'sfid_label', 'Packets (delta)')
        save_page(pdf, fig, ax, 'US ECT(0) & ECT(1) PACKETS (SNMP)',
                  f'{m["modem_name"]} ({m["mac_fmt"]})  |  per-poll delta per SFID', **_sp)


def page_us_param_set(pdf, us, **m):
    """US param set — max rate, priority, buffer targets."""
    rate_col = 'ps_max_rate_64' if ('ps_max_rate_64' in us.columns and
                                     not us['ps_max_rate_64'].isna().all()) else 'ps_max_rate'
    if rate_col not in us.columns or us[rate_col].isna().all():
        return

    us = us.copy()
    us[rate_col] = pd.to_numeric(us[rate_col], errors='coerce') / 1_000_000  # bps → Mbps

    _sp = {k: m[k] for k in ('mac_fmt','modem_name','session_start','session_end')}
    _sp['cmts_type'] = m.get('cmts_type', 'icmts')

    fig, ax = make_fig()
    plot_line(ax, us, rate_col, 'sfid_label', 'Mbps')
    save_page(pdf, fig, ax, 'US PARAM SET — MAX RATE (SNMP)',
              f'{m["modem_name"]} ({m["mac_fmt"]})  |  Active param set (type 2)', **_sp)



# ---------------------------------------------------------------------------
# DS chart pages
# ---------------------------------------------------------------------------
def page_ds_flow_stats(pdf, ds, **m):
    """DS flow octets, policed drop/delay, AQM drop."""
    _sp = {k: m[k] for k in ('mac_fmt','modem_name','session_start','session_end')}
    _sp['cmts_type'] = m.get('cmts_type', 'icmts')

    if 'flow_octets' in ds.columns and not ds['flow_octets'].isna().all():
        ds_d = _delta_mb(ds, 'flow_octets')
        fig, ax = make_fig()
        plot_line(ax, ds_d, 'flow_octets', 'sfid_label', 'Throughput (Mbps)')
        save_page(pdf, fig, ax, 'DS FLOW THROUGHPUT — SNMP (Mbps)',
                  f'{m["modem_name"]} ({m["mac_fmt"]})  |  {_total_gb_label(ds_d, "flow_octets")}', **_sp)

    if all(c in ds.columns for c in ('flow_policed_drop', 'flow_policed_delay')):
        fig, ax = make_fig()
        plot_dual(ax, ds, 'flow_policed_drop', 'flow_policed_delay',
                  'drop', 'delay', 'sfid_label', 'Packets')
        save_page(pdf, fig, ax, 'DS POLICED DROP & DELAY (SNMP)',
                  f'{m["modem_name"]} ({m["mac_fmt"]})  |  DS Service Flows', **_sp)

    if 'flow_aqm_drop' in ds.columns and not ds['flow_aqm_drop'].isna().all():
        fig, ax = make_fig()
        plot_line(ax, ds, 'flow_aqm_drop', 'sfid_label', 'Packets')
        save_page(pdf, fig, ax, 'DS AQM DROPPED PACKETS (SNMP)',
                  f'{m["modem_name"]} ({m["mac_fmt"]})  |  DS Service Flows', **_sp)


def page_ds_congestion(pdf, ds, **m):
    """DS congestion — AQM drop, CE marked, ECT0/ECT1 — per-poll deltas grouped by sfid."""
    cong_cols = ['cong_aqm_drop', 'cong_ce_marked', 'cong_ect0', 'cong_ect1']
    present   = [c for c in cong_cols if c in ds.columns and not ds[c].isna().all()]
    if not present:
        return

    _sp = {k: m[k] for k in ('mac_fmt','modem_name','session_start','session_end')}
    _sp['cmts_type'] = m.get('cmts_type', 'icmts')

    ds_d = ds.copy().sort_values(['sfid', 'captured_utc'])
    for c in present:
        ds_d[c] = pd.to_numeric(ds_d[c], errors='coerce')
        ds_d[c] = ds_d.groupby('sfid')[c].diff().clip(lower=0)

    if 'cong_aqm_drop' in present and 'cong_ce_marked' in present:
        fig, ax = make_fig()
        plot_dual(ax, ds_d, 'cong_aqm_drop', 'cong_ce_marked',
                  'AQM drop', 'CE marked', 'sfid_label', 'Packets (delta)')
        save_page(pdf, fig, ax, 'DS CONGESTION — AQM DROPS & CE MARKED (SNMP)',
                  f'{m["modem_name"]} ({m["mac_fmt"]})  |  per-poll delta per SFID', **_sp)

    if 'cong_ect0' in present and 'cong_ect1' in present:
        fig, ax = make_fig()
        plot_dual(ax, ds_d, 'cong_ect0', 'cong_ect1',
                  'ECT(0)', 'ECT(1)', 'sfid_label', 'Packets (delta)')
        save_page(pdf, fig, ax, 'DS ECT(0) & ECT(1) PACKETS (SNMP)',
                  f'{m["modem_name"]} ({m["mac_fmt"]})  |  per-poll delta per SFID', **_sp)


def page_ds_latency(pdf, ds, **m):
    """DS latency bin time-series — one chart per SFID."""
    bin_cols = [f'lat_bin{i}' for i in range(1, 17)]
    present  = [c for c in bin_cols if c in ds.columns]
    if not present:
        return
    _plot_bin_timeseries(pdf, ds, 'DS', 'sfid_label', present, '#34a853', **m)

# ---------------------------------------------------------------------------
# Kafka chart pages (vcmts DS + US from Kafka)
# ---------------------------------------------------------------------------
def page_kafka_throughput(pdf, kdf, direction, **m):
    """Delta octets → Mbps over time, grouped by sfid_label."""
    col = 'delta_octets'
    if col not in kdf.columns:
        return
    grp_col = 'sfid_label' if 'sfid_label' in kdf.columns else 'sfid'
    kdf = kdf.copy().sort_values(['sfid', 'captured_utc'])
    kdf['_ts_ms'] = pd.to_numeric(kdf['kafka_timestamp_ms'], errors='coerce')
    kdf['_interval_s'] = kdf.groupby('sfid')['_ts_ms'].transform(lambda s: s.diff() / 1000)
    kdf['mbps'] = kdf.apply(
        lambda r: pd.to_numeric(r[col], errors='coerce') * 8 / r['_interval_s'] / 1_000_000
                  if pd.notna(r['_interval_s']) and r['_interval_s'] > 0 else float('nan'), axis=1
    ).clip(lower=0)
    kdf = kdf[kdf['mbps'].notna()]
    label = direction.upper()
    fig, ax = make_fig()
    grp_col = 'sfid_label' if 'sfid_label' in kdf.columns else 'sfid'
    plot_line(ax, kdf, 'mbps', grp_col, 'Throughput (Mbps)')
    save_page(pdf, fig, ax, f'{label} THROUGHPUT — KAFKA (Mbps)',
              f'{m["modem_name"]} ({m["mac_fmt"]})  |  Kafka delta_octets → Mbps',
              **{k: m[k] for k in ('mac_fmt','modem_name','session_start','session_end')},
              cmts_type=m.get('cmts_type', 'vcmts'))


def page_kafka_latency_avg(pdf, kdf, direction, **m):
    """Average latency (ms) over time per flow.
    Kafka lat_avg_usec is in microseconds — divide by 1000 for ms."""
    col = 'lat_avg_usec'
    if col not in kdf.columns:
        return
    kdf = kdf.copy().sort_values(['sfid', 'captured_utc'])
    kdf[col] = pd.to_numeric(kdf[col], errors='coerce').fillna(0) / 1000  # µs → ms
    label   = direction.upper()
    grp_col = 'sfid_label' if 'sfid_label' in kdf.columns else 'sfid'
    fig, ax = make_fig()
    plot_line(ax, kdf, col, grp_col, 'Latency (ms)')
    save_page(pdf, fig, ax, f'{label} LATENCY AVG (ms)',
              f'{m["modem_name"]} ({m["mac_fmt"]})  |  Kafka lat_avg_usec ÷ 1000 → ms',
              **{k: m[k] for k in ('mac_fmt','modem_name','session_start','session_end')},
              cmts_type=m.get('cmts_type', 'vcmts'))


def page_kafka_latency_histogram(pdf, kdf, direction, **m):
    """Latency bin time-series per sfid_label (Kafka)."""
    bin_cols = [f'lat_bin{i}' for i in range(1, 17)]
    present  = [c for c in bin_cols if c in kdf.columns]
    if not present:
        return
    grp_col = 'sfid_label' if 'sfid_label' in kdf.columns else 'sfid'
    _m = dict(m)
    _m.setdefault('cmts_type', 'vcmts')
    _plot_bin_timeseries(pdf, kdf, direction.upper(), grp_col, present, ACCENT, source='Kafka', **_m)


# ---------------------------------------------------------------------------
# Additional chart styles
# ---------------------------------------------------------------------------

def page_step_line(pdf, df, y_col, group_col, ylabel, title, subtitle, source_cols=None, **m):
    """Step-line chart — flat between polls, honest representation of discrete SNMP samples."""
    _sp = {k: m[k] for k in ('mac_fmt','modem_name','session_start','session_end')}
    _sp['cmts_type'] = m.get('cmts_type', 'icmts')
    x_col = 'captured_utc' if 'captured_utc' in df.columns else 'poll_index'
    has_data = df[y_col].notna() & (df[y_col] != 0)
    if not has_data.any():
        return
    fig, ax = make_fig()
    for i, (name, grp) in enumerate(df.groupby(group_col)):
        grp = grp.sort_values(x_col)
        c = CHART_COLORS[i % len(CHART_COLORS)]
        ax.step(grp[x_col], grp[y_col], where='post', linewidth=2, color=c, label=str(name))
        ax.fill_between(grp[x_col], grp[y_col], step='post', alpha=0.08, color=c)
        ax.plot(grp[x_col], grp[y_col], marker='o', markersize=4, linewidth=0,
                color=c, markerfacecolor='white', markeredgecolor=c, markeredgewidth=1.5)
    ax.set_ylabel(ylabel, color=SUBTEXT, fontsize=10, fontweight='bold')
    ax.set_xlabel('Time (UTC)', color=SUBTEXT, fontsize=10)
    ax.legend(fontsize=8, facecolor=BG_DARK, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR, framealpha=0.9)
    fmt_ax(ax)
    save_page(pdf, fig, ax, title, subtitle, **_sp)


def page_area_stack(pdf, df, y_col, group_col, ylabel, title, subtitle, **m):
    """Stacked area chart — total bandwidth visible across all SFIDs."""
    _sp = {k: m[k] for k in ('mac_fmt','modem_name','session_start','session_end')}
    _sp['cmts_type'] = m.get('cmts_type', 'icmts')
    x_col = 'captured_utc' if 'captured_utc' in df.columns else 'poll_index'
    groups = [(name, grp.sort_values(x_col)) for name, grp in df.groupby(group_col)
              if grp[y_col].notna().any() and grp[y_col].sum() > 0]
    if not groups:
        return
    # Align all groups to common time index
    import numpy as np
    all_times = sorted(set(t for _, g in groups for t in g[x_col]))
    ys = []
    for name, grp in groups:
        s = grp.set_index(x_col)[y_col].reindex(all_times).fillna(0)
        ys.append(s.values)
    fig, ax = make_fig()
    labels = [str(name) for name, _ in groups]
    colors = [CHART_COLORS[i % len(CHART_COLORS)] for i in range(len(groups))]
    ax.stackplot(all_times, ys, labels=labels, colors=colors, alpha=0.75)
    ax.set_ylabel(ylabel, color=SUBTEXT, fontsize=10, fontweight='bold')
    ax.set_xlabel('Time (UTC)', color=SUBTEXT, fontsize=10)
    ax.legend(fontsize=8, facecolor=BG_DARK, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR,
              framealpha=0.9, loc='upper left')
    fmt_ax(ax)
    save_page(pdf, fig, ax, title, subtitle, **_sp)


def page_latency_heatmap(pdf, df, direction, group_col, bin_cols, source='SNMP', **m):
    """Heatmap: x=time, y=bin, color=packet count — shows bin distribution shift over session."""
    import numpy as np
    _sp = {k: m[k] for k in ('mac_fmt','modem_name','session_start','session_end')}
    _sp['cmts_type'] = m.get('cmts_type', 'icmts')
    has_bins = df[bin_cols].notna().any(axis=1)
    for sfid, grp in df[has_bins].groupby(group_col):
        grp = grp.sort_values('captured_utc').copy()
        if grp.empty:
            continue
        mat = grp[bin_cols].apply(pd.to_numeric, errors='coerce').fillna(0).values.T  # bins × time
        if mat.sum() == 0:
            continue
        edge_labels = _get_edge_labels(grp, len(bin_cols))
        fig, ax = make_fig()
        im = ax.imshow(mat, aspect='auto', origin='lower',
                       cmap='YlOrRd', interpolation='nearest')
        ax.set_yticks(range(len(bin_cols)))
        ax.set_yticklabels(edge_labels, color=TEXT_COLOR, fontsize=7)
        # x-axis: poll timestamps
        times = grp['captured_utc'].dt.strftime('%H:%M:%S').tolist()
        step = max(1, len(times) // 8)
        ax.set_xticks(range(0, len(times), step))
        ax.set_xticklabels(times[::step], color=TEXT_COLOR, fontsize=7, rotation=30, ha='right')
        ax.set_ylabel('Latency Bin', color=SUBTEXT, fontsize=10, fontweight='bold')
        ax.set_xlabel('Time (UTC)', color=SUBTEXT, fontsize=10)
        cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
        cbar.ax.yaxis.set_tick_params(color=TEXT_COLOR, labelsize=7)
        cbar.set_label('Packet Count', color=SUBTEXT, fontsize=8)
        save_page(pdf, fig, ax,
                  f'{direction} LATENCY HEATMAP ({source}) — {sfid}',
                  f'{m["modem_name"]} ({m["mac_fmt"]})  |  bin packet count over time',
                  **_sp)


def page_latency_scatter(pdf, df, direction, group_col, source='SNMP', **m):
    """Scatter: each poll as a dot, x=time, y=latency avg, size=packet count."""
    _sp = {k: m[k] for k in ('mac_fmt','modem_name','session_start','session_end')}
    _sp['cmts_type'] = m.get('cmts_type', 'icmts')
    lat_col = 'lat_avg_usec' if 'lat_avg_usec' in df.columns else '_lat_avg_ms'
    pkt_col = 'flow_pkts' if 'flow_pkts' in df.columns else None
    if lat_col not in df.columns or df[lat_col].isna().all():
        return
    df = df.copy()
    df[lat_col] = pd.to_numeric(df[lat_col], errors='coerce')
    if lat_col == 'lat_avg_usec' and source == 'SNMP':
        df[lat_col] = df[lat_col] / 1000  # µs → ms
    elif lat_col == 'lat_avg_usec':  # Kafka: µs → ms
        df[lat_col] = df[lat_col] / 1000
    has_data = df[lat_col].notna() & (df[lat_col] > 0)
    if not has_data.any():
        return
    fig, ax = make_fig()
    for i, (name, grp) in enumerate(df[has_data].groupby(group_col)):
        c = CHART_COLORS[i % len(CHART_COLORS)]
        if pkt_col and pkt_col in grp.columns:
            pkts = pd.to_numeric(grp[pkt_col], errors='coerce').fillna(1).clip(lower=1)
            sizes = (pkts / pkts.max() * 180).clip(lower=20)
        else:
            sizes = 60
        ax.scatter(grp['captured_utc'], grp[lat_col], s=sizes, color=c,
                   alpha=0.8, edgecolors='white', linewidths=0.5, label=str(name))
    ax.set_ylabel('Latency (ms)', color=SUBTEXT, fontsize=10, fontweight='bold')
    ax.set_xlabel('Time (UTC)', color=SUBTEXT, fontsize=10)
    ax.legend(fontsize=8, facecolor=BG_DARK, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR, framealpha=0.9)
    fmt_ax(ax)
    save_page(pdf, fig, ax,
              f'{direction} LATENCY SCATTER ({source})',
              f'{m["modem_name"]} ({m["mac_fmt"]})  |  dot size = packet count per poll',
              **_sp)


def page_latency_violin(pdf, df, direction, group_col, bin_cols, source='SNMP', **m):
    """Violin/box: latency distribution per SFID — samples weighted by per-poll bin deltas."""
    import numpy as np
    _sp = {k: m[k] for k in ('mac_fmt','modem_name','session_start','session_end')}
    _sp['cmts_type'] = m.get('cmts_type', 'icmts')

    # Diff bin counters by stable sfid key to get per-poll packet deltas for every flow
    diff_key = 'sfid' if 'sfid' in df.columns else group_col
    df = df.copy().sort_values([diff_key, 'captured_utc'])
    for c in bin_cols:
        df[c] = pd.to_numeric(df[c], errors='coerce')
        df[c] = df.groupby(diff_key)[c].diff().clip(lower=0)

    samples_by_sfid = {}
    for sfid, grp in df.groupby(group_col):
        edge_labels = _get_edge_labels(grp, len(bin_cols))
        usec_to_ms = 1000.0  # both SNMP and Kafka lat_avg_usec are in µs
        midpoints = []
        for lbl in edge_labels:
            try:
                if lbl.startswith('<'):
                    midpoints.append(float(lbl[1:]) / 2 / usec_to_ms)
                elif lbl.startswith('>'):
                    midpoints.append(float(lbl[1:]) * 1.5 / usec_to_ms)
                elif '–' in lbl:
                    a, b = lbl.split('–')
                    midpoints.append((float(a) + float(b)) / 2 / usec_to_ms)
                else:
                    midpoints.append(float(lbl) / usec_to_ms)
            except ValueError:
                midpoints.append(float(len(midpoints) + 1))
        # Expand per-poll delta counts into sample list
        expanded = []
        for _, row in grp.iterrows():
            for j, bc in enumerate(bin_cols):
                _v = pd.to_numeric(row.get(bc, 0), errors='coerce')
                cnt = 0 if pd.isna(_v) else int(_v)
                if cnt > 0 and j < len(midpoints):
                    expanded.extend([midpoints[j]] * min(cnt, 500))
        samples_by_sfid[str(sfid)] = expanded if expanded else [0.0]
    if not samples_by_sfid:
        return
    fig, ax = make_fig()
    labels = list(samples_by_sfid.keys())
    data   = [samples_by_sfid[k] for k in labels]
    parts  = ax.violinplot(data, positions=range(len(labels)), showmedians=True, showextrema=True)
    for i, pc in enumerate(parts['bodies']):
        pc.set_facecolor(CHART_COLORS[i % len(CHART_COLORS)])
        pc.set_alpha(0.7)
    for part in ('cmedians', 'cmins', 'cmaxes', 'cbars'):
        if part in parts:
            parts[part].set_color(TEXT_COLOR)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, color=TEXT_COLOR, fontsize=8, rotation=15, ha='right')
    ax.set_ylabel('Latency (ms)', color=SUBTEXT, fontsize=10, fontweight='bold')
    ax.set_xlabel('Service Flow', color=SUBTEXT, fontsize=10)
    fmt_ax(ax)
    save_page(pdf, fig, ax,
              f'{direction} LATENCY DISTRIBUTION — VIOLIN ({source})',
              f'{m["modem_name"]} ({m["mac_fmt"]})  |  distribution across all polls',
              **_sp)


def page_latency_percentile(pdf, df, direction, group_col, source='SNMP', **m):
    """CDF chart (SNMP): x=latency (ms), y=percentile (0–100%)  — one curve per SFID.
    For non-SNMP sources falls back to the original time-series P50/P99 chart."""
    import numpy as np
    bin_cols  = [f'lat_bin{i}'      for i in range(1, 17)]
    edge_cols = [f'lat_edge_bin{i}' for i in range(1, 16)]
    present_bins  = [c for c in bin_cols  if c in df.columns]
    present_edges = [c for c in edge_cols if c in df.columns]
    if not present_bins:
        return
    _sp = {k: m[k] for k in ('mac_fmt','modem_name','session_start','session_end')}
    _sp['cmts_type'] = m.get('cmts_type', 'icmts')

    # ------------------------------------------------------------------ SNMP CDF
    if source == 'SNMP':
        diff_key = 'sfid' if 'sfid' in df.columns else group_col
        df = df.copy().sort_values([diff_key, 'captured_utc'])
        if df.empty:
            return

        # Diff bin counters by stable sfid key → per-poll deltas, then sum across all polls
        for c in present_bins:
            df[c] = pd.to_numeric(df[c], errors='coerce')
            df[c] = df.groupby(diff_key)[c].diff().clip(lower=0)

        fig, ax = make_fig()
        # Remove time-axis formatter — x is latency, not datetime
        ax.xaxis.set_major_formatter(plt.ScalarFormatter())
        ax.xaxis.set_major_locator(plt.AutoLocator())
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=0, ha='center', color=TEXT_COLOR)

        for i, (sfid, grp) in enumerate(df.groupby(group_col)):
            # Build bin midpoints (ms) from edge columns
            edges_row = grp[present_edges].dropna(how='all') if present_edges else pd.DataFrame()
            if not edges_row.empty:
                edges = [float(edges_row[c].iloc[0]) for c in present_edges
                         if pd.to_numeric(edges_row[c].iloc[0], errors='coerce') > 0]
            else:
                edges = list(range(1, len(present_bins) + 1))
            boundaries = [0] + edges + [edges[-1] * 2 if edges else len(present_bins) + 1]
            # boundaries has len(edges)+2 entries; midpoints only up to min(len(present_bins), len(boundaries)-1)
            n_mid = min(len(present_bins), len(boundaries) - 1)
            midpoints_ms = [(boundaries[j] + boundaries[j + 1]) / 2 / 1000.0
                            for j in range(n_mid)]
            # Pad with extrapolated values if fewer midpoints than bins
            while len(midpoints_ms) < len(present_bins):
                midpoints_ms.append(midpoints_ms[-1] * 2 if midpoints_ms else float(len(midpoints_ms) + 1))

            # Sum all per-poll deltas across the session for each bin
            totals = grp[present_bins].sum()
            counts = [float(totals.get(c, 0) or 0) for c in present_bins]
            grand_total = sum(counts)
            c = CHART_COLORS[i % len(CHART_COLORS)]
            if grand_total == 0:
                ax.plot([], [], linewidth=2.5, color=c, label=f'{sfid} (no data)')
                continue

            lat_pts = [0.0] + midpoints_ms
            cdf_pts = [0.0]
            cumul = 0.0
            for cnt in counts:
                cumul += cnt
                cdf_pts.append(cumul / grand_total)

            lat_arr = np.array(lat_pts)
            cdf_arr = np.array(cdf_pts)

            # Smooth CDF curve
            sx, sy = _smooth_xy(pd.Series(lat_arr), pd.Series(cdf_arr))
            sy = np.clip(sy, 1e-6, 1 - 1e-6)
            ax.plot(sx, sy, linewidth=2.5, color=c, label=str(sfid))
            ax.fill_between(sx, sy, alpha=0.08, color=c)
            # Raw dots at each bin midpoint
            ax.plot(lat_arr[1:], np.clip(cdf_arr[1:], 1e-6, 1 - 1e-6), marker='o', markersize=4, linewidth=0,
                    color=c, markerfacecolor='white', markeredgecolor=c, markeredgewidth=1.5)

            # Annotate key percentile markers
            for pct_label, pct_val in [('P50', 0.50), ('P90', 0.90), ('P99', 0.99), ('P99.99', 0.9999)]:
                idx = np.searchsorted(cdf_arr, pct_val)
                if idx == 0 or idx >= len(lat_arr):
                    continue
                lo_lat, hi_lat = lat_arr[idx - 1], lat_arr[idx]
                lo_pct, hi_pct = cdf_arr[idx - 1], cdf_arr[idx]
                lat_at_pct = hi_lat if hi_pct == lo_pct else \
                    lo_lat + (pct_val - lo_pct) / (hi_pct - lo_pct) * (hi_lat - lo_lat)
                ax.plot(lat_at_pct, pct_val, marker='D', markersize=5, color=c,
                        markerfacecolor=c, markeredgecolor='white', markeredgewidth=0.8,
                        zorder=5)
                ax.annotate(f'{pct_label}\n{lat_at_pct:.2f}ms',
                            xy=(lat_at_pct, pct_val),
                            xytext=(6, 0), textcoords='offset points',
                            fontsize=6.5, color=c, va='center')

        ax.set_ylim(0.50, 0.9999)
        pct_ticks = [50, 90, 99, 99.99]
        ax.set_yscale('logit')
        ax.set_yticks([p / 100 for p in pct_ticks])
        ax.set_yticklabels(['P50', 'P90', 'P99', 'P99.99'], color=TEXT_COLOR, fontsize=8)
        ax.yaxis.set_minor_locator(plt.NullLocator())
        ax.set_xlabel('Latency (ms)', color=SUBTEXT, fontsize=10, fontweight='bold')
        ax.set_ylabel('Percentile', color=SUBTEXT, fontsize=10, fontweight='bold')
        ax.legend(fontsize=8, facecolor=BG_DARK, edgecolor=GRID_COLOR,
                  labelcolor=TEXT_COLOR, framealpha=0.9)
        ax.grid(True, color=GRID_COLOR, linewidth=0.7, linestyle='--', alpha=0.8)
        ax.set_axisbelow(True)
        save_page(pdf, fig, ax,
                  f'{direction} LATENCY CDF — P50 to P99.99 ({source})',
                  f'{m["modem_name"]} ({m["mac_fmt"]})  |  x=latency (ms)  y=percentile  |  aggregated across all polls',
                  **_sp)
        return

    # -------------------------------------------------------- non-SNMP: same CDF chart
    diff_key = 'sfid' if 'sfid' in df.columns else group_col
    df = df.copy().sort_values([diff_key, 'captured_utc'])
    if df.empty:
        return

    # Kafka bin counters are already per-poll deltas — diff by sfid anyway to be safe
    for c in present_bins:
        df[c] = pd.to_numeric(df[c], errors='coerce')
        df[c] = df.groupby(diff_key)[c].diff().clip(lower=0)

    # Kafka uses lat_edge_bin1..16 (16 edges, one per bin upper bound)
    edge_cols_16 = [f'lat_edge_bin{i}' for i in range(1, 17)]
    present_edges_kafka = [c for c in edge_cols_16 if c in df.columns]

    fig, ax = make_fig()
    ax.xaxis.set_major_formatter(plt.ScalarFormatter())
    ax.xaxis.set_major_locator(plt.AutoLocator())
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=0, ha='center', color=TEXT_COLOR)

    for i, (sfid, grp) in enumerate(df.groupby(group_col)):
        edges_row = grp[present_edges_kafka].dropna(how='all') if present_edges_kafka else pd.DataFrame()
        if not edges_row.empty:
            edges = [float(edges_row[c].iloc[0]) for c in present_edges_kafka
                     if pd.to_numeric(edges_row[c].iloc[0], errors='coerce') > 0]
        else:
            edges = list(range(1, len(present_bins) + 1))
        # Kafka edges are already ms (upper bound per bin); cap inf edge before building midpoints
        boundaries = [0] + [e for e in edges if np.isfinite(e)]
        if len(boundaries) < 2:
            boundaries = [0] + list(range(1, len(present_bins) + 2))
        last_finite = boundaries[-1]
        boundaries.append(last_finite * 2)
        n_mid = min(len(present_bins), len(boundaries) - 1)
        midpoints_ms = [(boundaries[j] + boundaries[j + 1]) / 2 for j in range(n_mid)]
        while len(midpoints_ms) < len(present_bins):
            midpoints_ms.append(midpoints_ms[-1] * 2 if midpoints_ms else float(len(midpoints_ms) + 1))

        totals = grp[present_bins].sum()
        counts = [float(totals.get(c, 0) or 0) for c in present_bins]
        grand_total = sum(counts)
        c = CHART_COLORS[i % len(CHART_COLORS)]
        if grand_total == 0:
            ax.plot([], [], linewidth=2.5, color=c, label=f'{sfid} (no data)')
            continue

        lat_pts = [0.0] + midpoints_ms
        cdf_pts = [0.0]
        cumul = 0.0
        for cnt in counts:
            cumul += cnt
            cdf_pts.append(cumul / grand_total)

        lat_arr = np.array(lat_pts)
        cdf_arr = np.array(cdf_pts)

        sx, sy = _smooth_xy(pd.Series(lat_arr), pd.Series(cdf_arr))
        sy = np.clip(sy, 1e-6, 1 - 1e-6)
        ax.plot(sx, sy, linewidth=2.5, color=c, label=str(sfid))
        ax.fill_between(sx, sy, alpha=0.08, color=c)
        ax.plot(lat_arr[1:], np.clip(cdf_arr[1:], 1e-6, 1 - 1e-6), marker='o', markersize=4, linewidth=0,
                color=c, markerfacecolor='white', markeredgecolor=c, markeredgewidth=1.5)

        for pct_label, pct_val in [('P50', 0.50), ('P90', 0.90), ('P99', 0.99), ('P99.99', 0.9999)]:
            idx = np.searchsorted(cdf_arr, pct_val)
            if idx == 0 or idx >= len(lat_arr):
                continue
            lo_lat, hi_lat = lat_arr[idx - 1], lat_arr[idx]
            lo_pct, hi_pct = cdf_arr[idx - 1], cdf_arr[idx]
            lat_at_pct = lo_lat if hi_pct == lo_pct else \
                lo_lat + (pct_val - lo_pct) / (hi_pct - lo_pct) * (hi_lat - lo_lat)
            ax.plot(lat_at_pct, pct_val, marker='D', markersize=5, color=c,
                    markerfacecolor=c, markeredgecolor='white', markeredgewidth=0.8, zorder=5)
            ax.annotate(f'{pct_label}\n{lat_at_pct:.2f}ms',
                        xy=(lat_at_pct, pct_val),
                        xytext=(6, 0), textcoords='offset points',
                        fontsize=6.5, color=c, va='center')

    ax.set_ylim(0.50, 0.9999)
    pct_ticks = [50, 90, 99, 99.99]
    ax.set_yscale('logit')
    ax.set_yticks([p / 100 for p in pct_ticks])
    ax.set_yticklabels(['P50', 'P90', 'P99', 'P99.99'], color=TEXT_COLOR, fontsize=8)
    ax.yaxis.set_minor_locator(plt.NullLocator())
    ax.set_xlabel('Latency (ms)', color=SUBTEXT, fontsize=10, fontweight='bold')
    ax.set_ylabel('Percentile', color=SUBTEXT, fontsize=10, fontweight='bold')
    ax.legend(fontsize=8, facecolor=BG_DARK, edgecolor=GRID_COLOR,
              labelcolor=TEXT_COLOR, framealpha=0.9)
    ax.grid(True, color=GRID_COLOR, linewidth=0.7, linestyle='--', alpha=0.8)
    ax.set_axisbelow(True)
    save_page(pdf, fig, ax,
              f'{direction} LATENCY CDF — P50 to P99.99 ({source})',
              f'{m["modem_name"]} ({m["mac_fmt"]})  |  x=latency (ms)  y=percentile  |  aggregated across all polls',
              **_sp)


# ---------------------------------------------------------------------------
# Shared dual-panel figure builder
# ---------------------------------------------------------------------------
def _dual_panel_fig(pdf, group_col,
                    top_df, top_col, top_ylabel, top_fmt, top_accent,
                    bot_df, bot_col, bot_ylabel, bot_fmt, bot_accent,
                    header_title, subtitle, _sp):
    """Render a mirrored dual-panel glow chart and save to pdf.
    top panel grows upward; bottom panel is y-inverted (spikes grow downward).
    """
    import matplotlib.ticker as mticker
    BG_CARD = '#112844'
    GLOW_A  = [0.08, 0.18, 1.0]
    GLOW_W  = [8,    3,    1.8]

    def _glow(ax, x, y, color, label=None):
        sx, sy = _smooth_xy(pd.Series(list(x)), pd.Series(list(y)))
        for alpha, lw in zip(GLOW_A, GLOW_W):
            ax.plot(sx, sy, color=color, linewidth=lw, alpha=alpha,
                    solid_capstyle='round', solid_joinstyle='round')
        ax.plot(list(x), list(y), 'o', color=color, markersize=5,
                markerfacecolor='white', markeredgecolor=color,
                markeredgewidth=1.4, zorder=5, label=label)
        ax.fill_between(sx, sy, 0, alpha=0.20, color=color, zorder=1)

    fig, (ax_top, ax_bot) = plt.subplots(
        2, 1, figsize=(11, 8.5), dpi=150, sharex=True,
        gridspec_kw={'hspace': 0.0, 'height_ratios': [1, 1]})
    fig.patch.set_facecolor(BG_DARK)
    ax_top.set_facecolor(BG_PANEL)
    ax_bot.set_facecolor(BG_PANEL)

    for i, (name, grp) in enumerate(top_df.groupby(group_col)):
        _glow(ax_top, grp['captured_utc'], grp[top_col], CHART_COLORS[i % len(CHART_COLORS)], label=str(name))
    ax_top.set_ylabel(top_ylabel, color=SUBTEXT, fontsize=10, fontweight='bold')
    ax_top.yaxis.set_major_formatter(mticker.StrMethodFormatter(top_fmt))
    ax_top.tick_params(axis='y', colors=SUBTEXT, labelsize=8)
    ax_top.tick_params(axis='x', bottom=False, labelbottom=False)
    ax_top.spines['top'].set_visible(False)
    ax_top.spines['right'].set_visible(False)
    ax_top.spines['bottom'].set_edgecolor(top_accent)
    ax_top.spines['bottom'].set_linewidth(1.5)
    ax_top.spines['left'].set_edgecolor(top_accent)
    ax_top.spines['left'].set_linewidth(1.2)
    ax_top.grid(True, color=GRID_COLOR, linewidth=0.5, linestyle='--', alpha=0.6)
    ax_top.set_axisbelow(True)
    handles, labels = ax_top.get_legend_handles_labels()
    ax_top.legend(handles, labels, title='SFID', loc='upper right',
                  frameon=True, facecolor=BG_CARD, edgecolor=top_accent,
                  labelcolor=TEXT_COLOR, fontsize=8, title_fontsize=9)

    for i, (name, grp) in enumerate(bot_df.groupby(group_col)):
        _glow(ax_bot, grp['captured_utc'], grp[bot_col], CHART_COLORS[i % len(CHART_COLORS)], label=str(name))
    ax_bot.invert_yaxis()
    ax_bot.set_ylabel(bot_ylabel, color=SUBTEXT, fontsize=10, fontweight='bold')
    ax_bot.yaxis.set_major_formatter(mticker.StrMethodFormatter(bot_fmt))
    ax_bot.tick_params(axis='y', colors=SUBTEXT, labelsize=8)
    ax_bot.spines['bottom'].set_visible(False)
    ax_bot.spines['right'].set_visible(False)
    ax_bot.spines['top'].set_edgecolor(bot_accent)
    ax_bot.spines['top'].set_linewidth(1.5)
    ax_bot.spines['left'].set_edgecolor(bot_accent)
    ax_bot.spines['left'].set_linewidth(1.2)
    ax_bot.grid(True, color=GRID_COLOR, linewidth=0.5, linestyle='--', alpha=0.6)
    ax_bot.set_axisbelow(True)
    ax_bot.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax_bot.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.setp(ax_bot.xaxis.get_majorticklabels(), rotation=30, ha='right', color=SUBTEXT, fontsize=8)
    ax_bot.set_xlabel('Time (UTC)', color=SUBTEXT, fontsize=10)

    fig.subplots_adjust(top=0.88, bottom=0.10, left=0.09, right=0.97, hspace=0.0)
    add_header(fig, header_title, subtitle)
    add_footer(fig, **_sp)
    pdf.savefig(fig, facecolor=fig.get_facecolor())
    plt.close(fig)


def _compute_throughput_mbps(df, group_col):
    """Add throughput_mbps column from flow_octets deltas; returns modified copy."""
    import numpy as np
    diff_col = 'sfid' if 'sfid' in df.columns else group_col
    df = df.copy().sort_values([diff_col, 'captured_utc'])
    df['flow_octets'] = pd.to_numeric(df.get('flow_octets', pd.Series(dtype=float)), errors='coerce')
    df['_interval_s'] = df.groupby(diff_col)['captured_utc'].transform(
        lambda s: s.diff().dt.total_seconds())
    df['_delta_oct'] = df.groupby(diff_col)['flow_octets'].diff().clip(lower=0)
    df['throughput_mbps'] = df.apply(
        lambda r: r['_delta_oct'] * 8 / r['_interval_s'] / 1e6
                  if pd.notna(r['_interval_s']) and r['_interval_s'] > 0 else np.nan, axis=1)
    return df


def _compute_latency_ms(df, group_col):
    """Add _lat_ms column from bin-weighted average or lat_avg_usec; returns modified copy.
    Always diffs bin counters by the stable 'sfid' column so that sfid_label label
    changes mid-session (e.g. late SCN resolution) don't break the per-SFID diff.
    """
    import numpy as np
    bin_cols  = [f'lat_bin{i}'      for i in range(1, 17)]
    edge_cols = [f'lat_edge_bin{i}' for i in range(1, 16)]
    present_bins  = [c for c in bin_cols  if c in df.columns]
    present_edges = [c for c in edge_cols if c in df.columns]
    df = df.copy().sort_values(['sfid', 'captured_utc'] if 'sfid' in df.columns
                               else [group_col, 'captured_utc'])
    # Use 'sfid' for the diff grouping — it is the stable numeric key.
    # sfid_label can change within a session if SCN resolves late, which would
    # cause groupby(sfid_label).diff() to emit NaN at every label-change boundary.
    diff_col = 'sfid' if 'sfid' in df.columns else group_col
    if present_bins:
        for c in present_bins:
            df[c] = pd.to_numeric(df[c], errors='coerce')
            df[c] = df.groupby(diff_col)[c].diff().clip(lower=0)
        def _wavg(row):
            edges = [pd.to_numeric(row.get(e), errors='coerce') for e in present_edges]
            edges = [e for e in edges if pd.notna(e)]
            if not edges:
                return np.nan
            boundaries = [0] + edges + [edges[-1] * 2]
            midpoints  = [(boundaries[i] + boundaries[i + 1]) / 2
                          for i in range(len(present_bins))]
            counts = [float(row.get(c, 0) or 0) for c in present_bins]
            total  = sum(counts)
            return np.nan if total == 0 \
                else sum(mp * ct for mp, ct in zip(midpoints, counts)) / total / 1000
        df['_lat_ms'] = df.apply(_wavg, axis=1)
    elif 'lat_avg_usec' in df.columns:
        df['_lat_ms'] = pd.to_numeric(df['lat_avg_usec'], errors='coerce') / 1000
    else:
        df['_lat_ms'] = float('nan')
    return df


def page_throughput_latency_correlation(pdf, df, direction, source='SNMP', **m):
    """Mirrored dual-panel: throughput (Mbps) above, latency (ms) inverted below."""
    _sp = {k: m[k] for k in ('mac_fmt', 'modem_name', 'session_start', 'session_end')}
    _sp['cmts_type'] = m.get('cmts_type', 'icmts')
    group_col = 'sfid_label' if 'sfid_label' in df.columns else 'sfid'
    # Sort by sfid+time before any per-SFID computation so both helpers see consistent order
    sort_key = ['sfid', 'captured_utc'] if 'sfid' in df.columns else [group_col, 'captured_utc']
    df = df.copy().sort_values(sort_key)
    df = _compute_throughput_mbps(df, group_col)
    df = _compute_latency_ms(df, group_col)
    tp_df  = df.dropna(subset=['throughput_mbps'])
    lat_df = df.dropna(subset=['_lat_ms'])
    if tp_df.empty and lat_df.empty:
        return
    dir_label = direction.upper()
    _dual_panel_fig(
        pdf, group_col,
        tp_df,  'throughput_mbps', 'Throughput (Mbps)', '{x:,.1f}', ACCENT,
        lat_df, '_lat_ms',         'Latency (ms)',       '{x:,.2f}', '#00c6ff',
        f'{dir_label} THROUGHPUT & LATENCY CORRELATION ({source})',
        f'{m["modem_name"]} ({m["mac_fmt"]})  |  Throughput above  |  Latency inverted below',
        _sp,
    )


def page_policed_drops_throughput_correlation(pdf, df, direction, **m):
    """Mirrored dual-panel: throughput (Mbps) above, policed drops (delta pkts) inverted below."""
    _sp = {k: m[k] for k in ('mac_fmt', 'modem_name', 'session_start', 'session_end')}
    _sp['cmts_type'] = m.get('cmts_type', 'icmts')
    group_col = 'sfid_label' if 'sfid_label' in df.columns else 'sfid'
    if 'flow_policed_drop' not in df.columns or df['flow_policed_drop'].isna().all():
        return
    diff_col = 'sfid' if 'sfid' in df.columns else group_col
    df = df.copy().sort_values([diff_col, 'captured_utc'])
    df = _compute_throughput_mbps(df, group_col)
    df['flow_policed_drop'] = pd.to_numeric(df['flow_policed_drop'], errors='coerce')
    df['_policed_delta'] = df.groupby(diff_col)['flow_policed_drop'].diff().clip(lower=0)
    tp_df   = df.dropna(subset=['throughput_mbps'])
    drop_df = df.dropna(subset=['_policed_delta'])
    if tp_df.empty or drop_df.empty:
        return
    dir_label = direction.upper()
    _dual_panel_fig(
        pdf, group_col,
        tp_df,   'throughput_mbps', 'Throughput (Mbps)',      '{x:,.1f}', ACCENT,
        drop_df, '_policed_delta',  'Policed Drops (pkts/Δ)', '{x:,.0f}', '#fa7b17',
        f'{dir_label} POLICED DROPS vs THROUGHPUT (SNMP)',
        f'{m["modem_name"]} ({m["mac_fmt"]})  |  Throughput above  |  Policed drop delta inverted below',
        _sp,
    )


def page_aqm_latency_correlation(pdf, df, direction, source='SNMP', **m):
    """Mirrored dual-panel: AQM drops (delta pkts) above, latency (ms) inverted below."""
    _sp = {k: m[k] for k in ('mac_fmt', 'modem_name', 'session_start', 'session_end')}
    _sp['cmts_type'] = m.get('cmts_type', 'icmts')
    group_col = 'sfid_label' if 'sfid_label' in df.columns else 'sfid'
    aqm_col = 'cong_aqm_drop'
    if aqm_col not in df.columns or df[aqm_col].isna().all():
        return
    diff_col = 'sfid' if 'sfid' in df.columns else group_col
    df = df.copy().sort_values([diff_col, 'captured_utc'])
    df = _compute_latency_ms(df, group_col)
    df[aqm_col] = pd.to_numeric(df[aqm_col], errors='coerce')
    df['_aqm_delta'] = df.groupby(diff_col)[aqm_col].diff().clip(lower=0)
    aqm_df = df.dropna(subset=['_aqm_delta'])
    lat_df = df.dropna(subset=['_lat_ms'])
    if aqm_df.empty or lat_df.empty:
        return
    dir_label = direction.upper()
    _dual_panel_fig(
        pdf, group_col,
        aqm_df, '_aqm_delta', 'AQM Drops (pkts/Δ)', '{x:,.0f}', '#ea4335',
        lat_df, '_lat_ms',    'Latency (ms)',        '{x:,.2f}', '#00c6ff',
        f'{dir_label} AQM DROPS vs LATENCY ({source})',
        f'{m["modem_name"]} ({m["mac_fmt"]})  |  AQM drop delta above  |  Latency inverted below',
        _sp,
    )


def page_kafka_congestion(pdf, kdf, direction, **m):
    """AQM drop and marked packets over time per flow."""
    drop_col   = 'cong_aqm_drop'
    marked_col = 'cong_ce_marked'
    if drop_col not in kdf.columns and marked_col not in kdf.columns:
        return
    label   = direction.upper()
    grp_col = 'sfid_label' if 'sfid_label' in kdf.columns else 'sfid'
    _sp     = {k: m[k] for k in ('mac_fmt','modem_name','session_start','session_end')}
    _sp['cmts_type'] = m.get('cmts_type', 'vcmts')

    if drop_col in kdf.columns and not kdf[drop_col].isna().all():
        fig, ax = make_fig()
        plot_line(ax, kdf, drop_col, grp_col, 'Packets')
        save_page(pdf, fig, ax, f'{label} AQM DROPPED PACKETS',
                  f'{m["modem_name"]} ({m["mac_fmt"]})  |  Kafka aqm_drop_pkts', **_sp)

    if marked_col in kdf.columns and not kdf[marked_col].isna().all():
        fig, ax = make_fig()
        plot_line(ax, kdf, marked_col, grp_col, 'Packets')
        save_page(pdf, fig, ax, f'{label} AQM MARKED PACKETS',
                  f'{m["modem_name"]} ({m["mac_fmt"]})  |  Kafka aqm_marked_pkts', **_sp)


# SFIDs that are OID artefacts / aggregate counters — never real service flows
_SFID_BLOCKLIST = {'0', '123', '0123'}


def _is_real_sfid(sfid_str):
    """Return True if sfid_str is a plausible service-flow ID (not a blocklisted artefact)."""
    return sfid_str.strip() not in _SFID_BLOCKLIST


# ---------------------------------------------------------------------------
# CSV loaders
# ---------------------------------------------------------------------------
def _load_csv(path, direction=None):
    """Read SNMP CSV skipping comment lines, parse captured_utc, coerce numerics.
    direction: 2=upstream, 1=downstream, None=all rows (no filter).
    """
    df = pd.read_csv(path, comment='#', parse_dates=['captured_utc'])
    skip = {'captured_utc', 'target_ip', 'target_label', 'cmts_type',
            'sfid', 'ps_scn', 'lat_bin_scn'}
    for c in df.columns:
        if c not in skip:
            df[c] = pd.to_numeric(df[c], errors='coerce')
    df['sfid'] = df['sfid'].astype(str)

    # Filter by direction when requested
    if direction is not None and 'sf_direction' in df.columns:
        df = df[df['sf_direction'] == direction].copy()

    # Drop blocklisted artefact SFIDs
    df = df[df['sfid'].apply(_is_real_sfid)].copy()

    # Build display label: "sfid (scn)" when SCN present, else "sfid (unknown)"
    if 'ps_scn' in df.columns or 'lat_bin_scn' in df.columns:
        scn = df.get('ps_scn', df.get('lat_bin_scn', pd.Series(dtype=str)))
        if 'lat_bin_scn' in df.columns:
            scn = scn.where(scn.notna() & (scn.astype(str).str.strip() != '') & (scn.astype(str) != 'nan'),
                            df['lat_bin_scn'])
        scn = scn.astype(str).str.strip('"').str.strip()
        has_scn = scn.notna() & (scn != '') & (scn != 'nan')
        df['sfid_label'] = df['sfid'] + ' (unknown)'
        df.loc[has_scn, 'sfid_label'] = df.loc[has_scn, 'sfid'] + ' (' + scn[has_scn] + ')'
    else:
        df['sfid_label'] = df['sfid'] + ' (unknown)'
    return df.sort_values('captured_utc').reset_index(drop=True)


# Kafka metric column → SNMP-equivalent name used by chart functions
_KAFKA_COL_MAP = {
    'total_octets':   'flow_octets',
    'total_pkts':     'flow_pkts',
    'aqm_drop_pkts':  'cong_aqm_drop',
    'aqm_marked_pkts':'cong_ce_marked',
    'sanctioned_pkts':'cong_sanctioned',
    'lat_max_usec':   'lat_max_usec',
    'lat_avg_usec':   'lat_avg_usec',
    **{f'lat_bin{str(i).zfill(2)}': f'lat_bin{i}' for i in range(1, 17)},
    **{f'lat_bin_edge{str(i).zfill(2)}': f'lat_edge_bin{i}' for i in range(1, 17)},
}


def _load_kafka_csv(path):
    """Load Kafka pivot CSV and return (us_df, ds_df) with SNMP-compatible column names."""
    df = pd.read_csv(path, comment='#', parse_dates=['captured_utc'])
    num_skip = {'captured_utc', 'dir', 'sfIndex', 'sfid', 'scn',
                'mdName', 'node', 'pod', 'cluster'}
    for c in df.columns:
        if c not in num_skip:
            df[c] = pd.to_numeric(df[c], errors='coerce')

    # Use sfIndex when sfid column is blank/NaN; strip trailing .0 from numeric reads
    def _clean_sfid(v):
        s = str(v).strip()
        if s in ('', 'nan', 'None'):
            return ''
        try:
            return str(int(float(s)))
        except (ValueError, OverflowError):
            return s
    df['sfid'] = df['sfid'].apply(_clean_sfid)
    df['sfid'] = df['sfid'].where(df['sfid'] != '', df['sfIndex'].apply(_clean_sfid))

    # Drop blocklisted artefact SFIDs
    df = df[df['sfid'].apply(_is_real_sfid)].copy()

    # Use scn as label where available: "sfid (scn)", fall back to "sfid (unknown)"
    df['sfid_label'] = df.apply(
        lambda r: f"{r['sfid']} ({r['scn']})" if pd.notna(r.get('scn')) and str(r.get('scn', '')).strip()
                  else f"{r['sfid']} (unknown)", axis=1)

    # Rename to SNMP-compatible names
    df = df.rename(columns=_KAFKA_COL_MAP)
    df = df.sort_values('captured_utc').reset_index(drop=True)

    us = df[df['dir'] == 'upstream'].copy()
    ds = df[df['dir'] == 'downstream'].copy()
    return us, ds


def _load_cmts_lookup(session_dir, mac=None):
    """Parse modem_summary.json and return {sfid_str: 'sfid (scn)'} map."""
    import json
    path = os.path.join(session_dir, 'modem_summary.json')
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    return {str(entry['sfid']): f"{entry['sfid']} ({entry['scn']})"
            for entry in data.get('sfids', []) if entry.get('scn')}


def _apply_kafka_sfid_labels(kdf, sfid_map):
    """Enrich sfid_label from lookup map where the CSV scn was missing."""
    if kdf is None or kdf.empty or not sfid_map:
        return kdf
    kdf = kdf.copy()
    # Only apply map entry when sfid_label still ends with '(unknown)'
    def _enrich(row):
        sfid = str(row.get('sfid', ''))
        if sfid in sfid_map and str(row.get('sfid_label', '')).endswith('(unknown)'):
            return sfid_map[sfid]
        return row.get('sfid_label', sfid)
    kdf['sfid_label'] = kdf.apply(_enrich, axis=1)
    return kdf


def main():
    # argv: [script, [session_dir_or_mac], [--name "session name"]]
    args = sys.argv[1:]
    session_arg = None
    session_name = None

    i = 0
    while i < len(args):
        if args[i] == '--name' and i + 1 < len(args):
            session_name = args[i + 1]
            i += 2
        else:
            session_arg = args[i]
            i += 1

    sess      = find_session(session_arg)
    cmts_type = sess['cmts_type']

    if session_name is None:
        if sys.stdin.isatty():
            session_name = input('Session name (e.g. "Netflix L4S Gaming Test") [Enter for default]: ').strip()
        if not session_name:
            # Derive name from session directory — e.g.
            # .../HSI021_Thousandeyes_ThousandEyes_20260820_192209/ThousandEyes
            # → "HSI021_Thousandeyes — ThousandEyes"
            # .../HSI029_ByteBlower_DS_Classic_20260820/DS_Classic
            # → "HSI029_ByteBlower — DS_Classic"
            sdir = sess['session_dir']
            scenario  = os.path.basename(sdir.rstrip('/'))
            parent    = os.path.basename(os.path.dirname(sdir.rstrip('/')))
            # Strip trailing timestamp (16-digit _YYYYMMDD_HHMMSS)
            parent_clean = re.sub(r'_\d{8}_\d{6}$', '', parent)
            if scenario and scenario != parent_clean:
                session_name = f'{parent_clean} — {scenario}'
            else:
                session_name = parent_clean or f'{cmts_type.upper()} SNMP Telemetry Report'
    mac       = sess['mac']
    mac_fmt   = ':'.join(mac[i:i+2] for i in range(0, 12, 2)).upper()
    modem_name = MODEM_NAMES.get(mac, mac_fmt)

    print(f'Session: {sess["session_dir"]}  [{cmts_type}]')

    # --- load data ---
    us = _load_csv(sess['us_path'], direction=2)
    # DS SNMP always comes from snmp_us file (sf_direction=1) — true for both vcmts and icmts
    ds_snmp = _load_csv(sess['us_path'], direction=1) if sess['us_path'] else None
    if cmts_type == 'vcmts':
        k_us, k_ds = _load_kafka_csv(sess['kafka_path'])
        sfid_map = _load_cmts_lookup(sess['session_dir'])
        k_us = _apply_kafka_sfid_labels(k_us, sfid_map)
        k_ds = _apply_kafka_sfid_labels(k_ds, sfid_map)
        ds = k_ds
    else:
        # ds_path may be the same file as us_path — direction filter separates them
        ds   = ds_snmp
        k_us = k_ds = None

    # --- session metadata ---
    all_times     = pd.concat([us['captured_utc'],
                                ds['captured_utc'] if ds is not None else pd.Series(dtype='datetime64[ns]')]).dropna()
    session_start = all_times.min().strftime('%Y-%m-%d %H:%M UTC')
    session_end   = all_times.max().strftime('%Y-%m-%d %H:%M UTC')
    duration_secs = int((all_times.max() - all_times.min()).total_seconds())
    hours, rem    = divmod(duration_secs, 3600)
    duration_str  = f'{hours}h {rem // 60}m'
    total_polls   = us['poll_index'].nunique() if 'poll_index' in us.columns else len(us)

    us_sfids = sorted(us['sfid_label'].unique(), key=lambda x: str(x))
    ds_sfids = sorted(ds['sfid_label'].unique(), key=lambda x: str(x)) \
               if ds is not None and not ds.empty else []

    m = dict(mac_fmt=mac_fmt, modem_name=modem_name,
             session_start=session_start, session_end=session_end,
             cmts_type=cmts_type,
             session_dir=sess['session_dir'],
             sfid_map=sfid_map if cmts_type == 'vcmts' else {})
    # --- build TOC ---
    if cmts_type == 'vcmts':
        toc = [
            ('3',  'ThousandEyes Results',             'DS/US throughput, latency and jitter per iteration'),
            ('4',  'US Flow Throughput (SNMP)',         'Per-poll delta octets → Mbps per US service flow'),
            ('5',  'US Latency Avg (SNMP)',             'Weighted avg latency from bin deltas per poll'),
            ('6',  'US Throughput & Latency Corr.',     'Mirrored chart: throughput above, latency inverted below'),
            ('7',  'US AQM Drops vs Latency',           'AQM drop delta above, latency inverted below'),
            ('8',  'US Latency Scatter (SNMP)',         'Per-poll latency scatter per US SFID'),
            ('9',  'US Latency CDF (SNMP)',             'CDF: x=latency (ms), y=percentile P50–P99.99 per SFID'),
            ('10', 'US Latency Bins (SNMP)',            'Last − first poll bin delta per US SFID'),
            ('11', 'US Latency Violin (SNMP)',          'Latency distribution violin per US SFID'),
            ('12', 'US Congestion AQM & CE (SNMP)',     'AQM drops and CE marked packets per US flow'),
            ('13', 'US Param Set Max Rate (SNMP)',      'Active param set max rate (Mbps) per US flow'),
            ('14', 'DS Throughput (Kafka)',             'Kafka delta_octets → Mbps per DS flow'),
            ('15', 'DS Latency Avg (Kafka)',            'Kafka average latency per DS flow over time'),
            ('16', 'DS Throughput & Latency Corr.',     'Mirrored chart: throughput above, latency inverted below'),
            ('17', 'DS AQM Drops vs Latency',           'AQM drop delta above, latency inverted below'),
            ('18', 'DS Latency Scatter (Kafka)',        'Per-poll latency scatter per DS SFID'),
            ('19', 'DS Latency CDF (Kafka)',            'CDF: x=latency (ms), y=percentile P50–P99.99 per SFID'),
            ('20', 'DS Latency Bins (Kafka)',           'Kafka last − first bin delta per DS SFID'),
            ('21', 'DS Latency Violin (Kafka)',         'Latency distribution violin per DS SFID'),
            ('22', 'DS Congestion (Kafka)',             'Kafka AQM drop and marked packets per DS flow'),
            ('23', 'Session Summary',                  'Peak throughput, latency, P50/P99, AQM drops per SFID'),
        ]
    else:
        toc = [
            ('3',  'ThousandEyes Results',             'DS/US throughput, latency and jitter per iteration'),
            ('4',  'US Flow Throughput (SNMP)',         'Per-poll delta octets → Mbps per US service flow'),
            ('5',  'US Latency Avg (SNMP)',             'Weighted avg latency from bin deltas per poll'),
            ('6',  'US Throughput & Latency Corr.',     'Mirrored chart: throughput above, latency inverted below'),
            ('7',  'US Policed Drops vs Throughput',    'Throughput above, policed drop delta inverted below'),
            ('8',  'US AQM Drops vs Latency',           'AQM drop delta above, latency inverted below'),
            ('9',  'US Latency Scatter (SNMP)',         'Per-poll latency scatter per US SFID'),
            ('10', 'US Latency CDF (SNMP)',             'CDF: x=latency (ms), y=percentile P50–P99.99 per SFID'),
            ('11', 'US Latency Bins (SNMP)',            'Last − first poll bin delta per US SFID'),
            ('12', 'US Latency Violin (SNMP)',          'Latency distribution violin per US SFID'),
            ('13', 'US Congestion AQM & CE (SNMP)',     'AQM drops and CE marked packets per US flow'),
            ('14', 'US ECT(0) & ECT(1) (SNMP)',        'ECN capable transport packet counts per US flow'),
            ('15', 'US Param Set Max Rate (SNMP)',      'Active param set max rate (Mbps) per US flow'),
            ('16', 'DS Flow Throughput (SNMP)',         'Per-poll delta octets → Mbps per DS service flow'),
            ('17', 'DS Policed Drop & Delay (SNMP)',    'Policed drop and delay packet counts per DS flow'),
            ('18', 'DS AQM Dropped Packets (SNMP)',     'AQM drop counters per DS service flow'),
            ('19', 'DS Congestion AQM & CE (SNMP)',     'AQM drops and CE marked packets per DS flow'),
            ('20', 'DS Throughput & Latency Corr.',     'Mirrored chart: throughput above, latency inverted below'),
            ('21', 'DS Policed Drops vs Throughput',    'Throughput above, policed drop delta inverted below'),
            ('22', 'DS AQM Drops vs Latency',           'AQM drop delta above, latency inverted below'),
            ('23', 'DS Latency Bins (SNMP)',            'Last − first poll bin delta per DS SFID'),
            ('24', 'Session Summary',                  'Peak throughput, latency, P50/P99, AQM drops per SFID'),
        ]

    safe_name = re.sub(r'[^\w\-]', '_', session_name).strip('_')
    safe_name = re.sub(r'_+', '_', safe_name)  # collapse multiple underscores
    out_path = os.path.join(sess['session_dir'], f'report_{cmts_type}_{mac}_{safe_name}.pdf')

    with PdfPages(out_path) as pdf:
        page_cover(pdf, mac_fmt, modem_name, session_start, session_end,
                   duration_str, total_polls, us_sfids, ds_sfids,
                   cmts_type=cmts_type, session_name=session_name)
        page_toc(pdf, mac_fmt, modem_name, session_start, session_end, toc, cmts_type=cmts_type)

        # ThousandEyes dedicated page(s)
        page_thousandeyes(pdf, sess['session_dir'], **m)

        # US pages (SNMP — same for both types)
        page_us_flow_stats(pdf, us, **m)

        page_us_latency_avg(pdf, us, **m)
        page_throughput_latency_correlation(pdf, us, 'US', source='SNMP', **m)
        page_policed_drops_throughput_correlation(pdf, us, 'US', **m)
        page_aqm_latency_correlation(pdf, us, 'US', source='SNMP', **m)
        page_latency_scatter(pdf, us, 'US', 'sfid_label', source='SNMP', **m)
        page_latency_percentile(pdf, us, 'US', 'sfid_label', source='SNMP', **m)
        page_us_latency_histogram(pdf, us, **m)
        page_latency_violin(pdf, us, 'US', 'sfid_label',
                            [c for c in [f'lat_bin{i}' for i in range(1,17)] if c in us.columns],
                            source='SNMP', **m)
        page_us_congestion(pdf, us, **m)
        page_us_param_set(pdf, us, **m)

        if cmts_type == 'vcmts':
            # DS Kafka charts only
            page_kafka_throughput(pdf, k_ds, 'downstream', **m)
            page_kafka_latency_avg(pdf, k_ds, 'downstream', **m)
            page_throughput_latency_correlation(pdf, k_ds, 'DS', source='Kafka', **m)
            page_aqm_latency_correlation(pdf, k_ds, 'DS', source='Kafka', **m)
            page_latency_scatter(pdf, k_ds, 'DS', 'sfid_label', source='Kafka', **m)
            page_latency_percentile(pdf, k_ds, 'DS', 'sfid_label', source='Kafka', **m)
            page_kafka_latency_histogram(pdf, k_ds, 'downstream', **m)
            page_latency_violin(pdf, k_ds, 'DS', 'sfid_label',
                                [c for c in [f'lat_bin{i}' for i in range(1,17)] if c in k_ds.columns],
                                source='Kafka', **m)
            page_kafka_congestion(pdf, k_ds, 'downstream', **m)
        else:
            # DS from SNMP
            page_ds_flow_stats(pdf, ds, **m)
            page_ds_congestion(pdf, ds, **m)
            page_throughput_latency_correlation(pdf, ds, 'DS', source='SNMP', **m)
            page_policed_drops_throughput_correlation(pdf, ds, 'DS', **m)
            page_aqm_latency_correlation(pdf, ds, 'DS', source='SNMP', **m)
            page_ds_latency(pdf, ds, **m)
            page_latency_violin(pdf, ds, 'DS', 'sfid_label',
                                [c for c in [f'lat_bin{i}' for i in range(1,17)] if c in ds.columns],
                                source='SNMP', **m)
            page_latency_percentile(pdf, ds, 'DS', 'sfid_label', source='SNMP', **m)

        page_summary(pdf, us,
                     ds if cmts_type != 'vcmts' else None,
                     None,
                     k_ds if cmts_type == 'vcmts' else None,
                     **m)

        d = pdf.infodict()
        d['Title']   = f'{cmts_type.upper()} SNMP Report — {modem_name} ({mac_fmt})'
        d['Author']  = 'aphillips — Charter Access Engineering'
        d['Subject'] = session_name

    print(f'PDF saved: {out_path}')

    # HTML report disabled
    # try:
    #     from metrics_html_report import generate_html_report
    #     generate_html_report(sess, session_name)
    # except Exception as e:
    #     print(f'[HTML report] skipped: {e}')


if __name__ == '__main__':
    main()
