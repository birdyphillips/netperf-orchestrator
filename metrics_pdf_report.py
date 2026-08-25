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
    """Inspect a directory and return a session dict, or None if not a valid session.
    Also searches one subdirectory level deep to handle sessions where CSVs are
    nested under a subdirectory (e.g. ThousandEyes/raw_data/).
    """
    us_files    = sorted(glob.glob(os.path.join(d, 'snmp_us_*.csv')))
    ds_files    = sorted(glob.glob(os.path.join(d, 'snmp_ds_*.csv')))
    kafka_files = sorted(glob.glob(os.path.join(d, 'kafka_*.csv')))
    if not us_files:
        us_files    = sorted(glob.glob(os.path.join(d, '*', 'snmp_us_*.csv')))
        ds_files    = sorted(glob.glob(os.path.join(d, '*', 'snmp_ds_*.csv')))
        kafka_files = sorted(glob.glob(os.path.join(d, '*', 'kafka_*.csv')))
    if not us_files:
        us_files    = sorted(glob.glob(os.path.join(d, '*', '*', 'snmp_us_*.csv')))
        ds_files    = sorted(glob.glob(os.path.join(d, '*', '*', 'snmp_ds_*.csv')))
        kafka_files = sorted(glob.glob(os.path.join(d, '*', '*', 'kafka_*.csv')))
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
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
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


def plot_bar_grouped(ax, df, cols, labels, group_col, ylabel):
    """Grouped bar chart: x=poll time, one bar cluster per SFID, one bar per metric."""
    import numpy as np
    x_col = 'captured_utc' if 'captured_utc' in df.columns else 'poll_index'
    groups = list(df.groupby(group_col))
    n_metrics = len(cols)
    n_sfids   = len(groups)
    width     = 0.8 / max(n_metrics * n_sfids, 1)
    all_x     = sorted(df[x_col].unique())
    x_idx     = {t: i for i, t in enumerate(all_x)}
    x_pos     = np.arange(len(all_x))
    for si, (name, grp) in enumerate(groups):
        base_color = CHART_COLORS[si % len(CHART_COLORS)]
        for mi, (col, lbl) in enumerate(zip(cols, labels)):
            offset = (si * n_metrics + mi - (n_sfids * n_metrics - 1) / 2) * width
            heights = [float(pd.to_numeric(grp.loc[grp[x_col] == t, col].iloc[0], errors='coerce') or 0)
                       if t in grp[x_col].values else 0 for t in all_x]
            alpha = 1.0 - mi * 0.25
            ax.bar(x_pos + offset, heights, width=width * 0.9,
                   color=base_color, alpha=max(alpha, 0.45),
                   label=f'{name} {lbl}', edgecolor=BG_DARK, linewidth=0.4)
    ax.set_xticks(x_pos)
    ax.set_xticklabels([t.strftime('%H:%M:%S') if hasattr(t, 'strftime') else str(t)
                        for t in all_x], rotation=45, ha='right', color=TEXT_COLOR, fontsize=7)
    ax.set_ylabel(ylabel, color=SUBTEXT, fontsize=10, fontweight='bold')
    ax.set_xlabel('Time (UTC)', color=SUBTEXT, fontsize=10)
    ax.legend(fontsize=7, facecolor=BG_DARK, edgecolor=GRID_COLOR,
              labelcolor=TEXT_COLOR, framealpha=0.9, ncol=2)
    ax.set_ylim(bottom=0)
    ax.grid(True, color=GRID_COLOR, linewidth=0.7, linestyle='--', alpha=0.8, axis='y')
    ax.set_axisbelow(True)


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
    ax.set_ylim(bottom=0)
    if 'latency' in ylabel.lower() or 'ms' in ylabel.lower():
        from matplotlib.ticker import MultipleLocator
        ymax = ax.get_ylim()[1]
        step = 5 if ymax <= 100 else 10 if ymax <= 250 else 25 if ymax <= 500 else 50
        ax.yaxis.set_major_locator(MultipleLocator(step))
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
    ax.set_ylim(bottom=0)
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
    ax.axhline(y=0.885, xmin=0.03, xmax=0.97, color=ACCENT, linewidth=1)

    # Two-column layout — left col entries 0..half-1, right col entries half..
    half     = (len(contents) + 1) // 2
    col_defs = [(0.03, 0.495), (0.515, 0.97)]  # (x_left_edge, x_right_edge)
    gap      = min(0.072, 0.80 / max(half, 1))

    for col_idx, entries in enumerate([contents[:half], contents[half:]]):
        x0, x1  = col_defs[col_idx]
        pg_x    = x0 + 0.038
        title_x = x0 + 0.082
        y = 0.845
        for i, (page, title, desc) in enumerate(entries):
            row_color = '#112240' if i % 2 == 0 else '#0d1b2a'
            ax.axhspan(y - gap * 0.42, y + gap * 0.58,
                       xmin=x0, xmax=x1, facecolor=row_color, alpha=1.0)
            ax.text(pg_x, y + 0.004, f'pg {page}',
                    transform=ax.transAxes, fontsize=7.5, fontweight='bold',
                    color=ACCENT, va='center', ha='center',
                    bbox=dict(boxstyle='round,pad=0.22', facecolor='#0d2a4a',
                              edgecolor=ACCENT, linewidth=0.7))
            ax.text(title_x, y + 0.004, title,
                    transform=ax.transAxes, fontsize=8.5, fontweight='bold',
                    color=TEXT_COLOR, va='center', fontfamily='DejaVu Sans')
            ax.text(title_x, y - gap * 0.36, desc,
                    transform=ax.transAxes, fontsize=6.8,
                    color='#aabbcc', va='center', fontstyle='italic')
            ax.axhline(y=y - gap * 0.42,
                       xmin=x0, xmax=x1,
                       color=GRID_COLOR, linewidth=0.4, linestyle=':')
            y -= gap

    # Vertical divider
    ax.axvline(x=0.505, ymin=0.06, ymax=0.885, color=GRID_COLOR, linewidth=0.7, linestyle='--')

    label = cmts_type.upper()
    ax.text(0.5, 0.025,
            f'{label} SNMP Report  |  {modem_name} ({mac_fmt})  |  {session_start} — {session_end}',
            transform=ax.transAxes, fontsize=8, color='#445566', ha='center', va='center')

    pdf.savefig(fig, facecolor=fig.get_facecolor())
    plt.close(fig)

# ---------------------------------------------------------------------------
# ThousandEyes dedicated page
# ---------------------------------------------------------------------------
def page_thousandeyes(pdf, te_dir, **m):
    """Single PDF page: consolidated table of all iterations — DS/US throughput, latency, jitter."""
    te_results = _load_te_results(te_dir)
    if not te_results:
        return

    test_group = te_results[0].get('test_group', 'N/A')
    unit_id    = te_results[0].get('unit_id', 'N/A')
    target     = (te_results[0].get('results', {}).get('http_get_mt', {}).get('target', '') or
                  te_results[0].get('results', {}).get('udp_jitter', {}).get('target', 'N/A'))

    # Build one row per iteration
    table_rows = []
    for te in te_results:
        iteration = te.get('iteration', '?')
        ts        = te.get('timestamp', '')[:19].replace('T', ' ')
        res       = te.get('results', {})
        ds_r      = res.get('http_get_mt', {})
        us_r      = res.get('http_post_mt', {})
        jit_r     = res.get('udp_jitter', {})

        ds_mbps  = f"{ds_r['bytes_sec'] * 8 / 1e6:.1f}"  if ds_r.get('bytes_sec')  else '—'
        us_mbps  = f"{us_r['bytes_sec'] * 8 / 1e6:.1f}"  if us_r.get('bytes_sec')  else '—'
        lat_ms   = f"{jit_r['latency']   / 1000:.3f}"    if jit_r.get('latency')   else '—'
        dj_ms    = f"{jit_r['down_jitter'] / 1000:.3f}"  if jit_r.get('down_jitter') is not None else '—'
        uj_ms    = f"{jit_r['up_jitter']   / 1000:.3f}"  if jit_r.get('up_jitter')   is not None else '—'
        table_rows.append([str(iteration), ts, ds_mbps, us_mbps, lat_ms, dj_ms, uj_ms])

    # Compute averages across iterations
    def _avg(col_idx):
        vals = []
        for r in table_rows:
            try:
                vals.append(float(r[col_idx]))
            except (ValueError, TypeError):
                pass
        return f'{sum(vals)/len(vals):.3f}' if vals else '—'

    avg_row = ['AVG', '', _avg(2), _avg(3), _avg(4), _avg(5), _avg(6)]
    col_labels = ['Iter', 'Timestamp', 'DS Mbps\n(http_get_mt)', 'US Mbps\n(http_post_mt)',
                  'Latency\n(ms)', 'DS Jitter\n(ms)', 'US Jitter\n(ms)']
    col_widths = [0.06, 0.20, 0.16, 0.16, 0.14, 0.14, 0.14]

    fig = plt.figure(figsize=(11, 8.5))
    fig.patch.set_facecolor(BG_DARK)
    ax = fig.add_axes([0.03, 0.10, 0.94, 0.78])
    ax.set_facecolor(BG_PANEL)
    ax.axis('off')

    all_rows = table_rows + [avg_row]
    tbl = ax.table(
        cellText=all_rows,
        colLabels=col_labels,
        colWidths=col_widths,
        loc='center', cellLoc='center',
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    tbl.scale(1, 1.8)

    # Header row
    for col in range(len(col_labels)):
        cell = tbl[0, col]
        cell.set_facecolor('#34a853')
        cell.set_text_props(color='white', fontweight='bold')

    # Data rows
    for row_i in range(len(table_rows)):
        bg = BG_PANEL if row_i % 2 == 0 else BG_DARK
        for col in range(len(col_labels)):
            cell = tbl[row_i + 1, col]
            cell.set_facecolor(bg)
            cell.set_text_props(color=TEXT_COLOR)
            cell.set_edgecolor(GRID_COLOR)

    # Average row — highlighted
    avg_row_idx = len(table_rows) + 1
    for col in range(len(col_labels)):
        cell = tbl[avg_row_idx, col]
        cell.set_facecolor('#0d2a4a')
        cell.set_text_props(color=ACCENT, fontweight='bold')
        cell.set_edgecolor(ACCENT)

    # Header bar
    hax = fig.add_axes([0, 0.91, 1, 0.09])
    hax.set_facecolor('#34a853')
    hax.axis('off')
    hax.text(0.5, 0.65, 'THOUSANDEYES INSTANT TEST RESULTS',
             transform=hax.transAxes, fontsize=16, fontweight='bold',
             color='white', ha='center', va='center')
    hax.text(0.5, 0.18,
             f'{test_group}  |  Unit {unit_id}  |  Target: {target}  |  {len(te_results)} iteration(s)',
             transform=hax.transAxes, fontsize=8, color=TEXT_COLOR,
             ha='center', va='center', fontstyle='italic')

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


def _detect_result_type(session_dir):
    """Return ('thousandeyes'|'byteblower'|'iperf'|None) based on JSON files in session_dir."""
    import json
    # Check direct dir and one level up
    search_dirs = [session_dir, os.path.dirname(session_dir)]
    for d in search_dirs:
        for f in sorted(glob.glob(os.path.join(d, '*.json'))):
            base = os.path.basename(f).lower()
            if base == 'modem_summary.json':
                continue
            try:
                with open(f) as fh:
                    data = json.load(fh)
                # ThousandEyes: has 'results' with http_get_mt / http_post_mt / udp_jitter
                if 'results' in data and any(k in data['results']
                        for k in ('http_get_mt', 'http_post_mt', 'udp_jitter')):
                    return 'thousandeyes'
                # ByteBlower: has 'byteblower' or 'frames' key
                if any(k in data for k in ('byteblower', 'frames', 'ByteBlower')):
                    return 'byteblower'
                # iperf3: has 'start' with 'test_start' or 'intervals'
                if 'start' in data and 'intervals' in data:
                    return 'iperf'
            except Exception:
                pass
        # Also check subdirs one level deep for iteration folders
        for sub in glob.glob(os.path.join(d, '*', '*.json')):
            base = os.path.basename(sub).lower()
            if base == 'modem_summary.json':
                continue
            try:
                with open(sub) as fh:
                    data = json.load(fh)
                if 'results' in data and any(k in data['results']
                        for k in ('http_get_mt', 'http_post_mt', 'udp_jitter')):
                    return 'thousandeyes'
                if any(k in data for k in ('byteblower', 'frames', 'ByteBlower')):
                    return 'byteblower'
                if 'start' in data and 'intervals' in data:
                    return 'iperf'
            except Exception:
                pass
    return None


_RESULT_TYPE_TOC = {
    'thousandeyes': ('ThousandEyes Results',  'DS/US throughput, latency and jitter per iteration'),
    'byteblower':   ('ByteBlower Results',    'DS/US throughput, latency and frame-loss per flow'),
    'iperf':        ('iPerf3 Results',        'DS/US throughput and retransmit summary'),
    None:           ('External Test Results', 'No result JSON found in session directory'),
}


def _load_te_results(session_dir):
    """Load ThousandEyes JSON results from session dir. Returns list of result dicts sorted by iteration."""
    import json
    # Search: session_dir, iteration_*/ subdirs, one level up, parent iteration_*/ subdirs
    search_patterns = [
        os.path.join(session_dir, 'ThousandEyes_*.json'),
        os.path.join(session_dir, 'iteration_*', 'ThousandEyes_*.json'),
        os.path.join(session_dir, '*', 'ThousandEyes_*.json'),
        os.path.join(os.path.dirname(session_dir), 'ThousandEyes_*.json'),
    ]
    te_files = []
    for pattern in search_patterns:
        te_files.extend(glob.glob(pattern))
    te_files = sorted(set(te_files))
    results = []
    for f in te_files:
        try:
            with open(f) as fh:
                results.append(json.load(fh))
        except Exception:
            pass
    return sorted(results, key=lambda r: r.get('iteration', 0))


def page_summary(pdf, us, ds, k_us, k_ds, **m):
    """Summary page: per-SFID throughput, latency, and congestion counters with % rates."""
    cmts_type   = m.get('cmts_type', 'icmts')
    sfid_map    = m.get('sfid_map', {})
    session_dir = m.get('session_dir', '')
    _sp = {k: m[k] for k in ('mac_fmt', 'modem_name', 'session_start', 'session_end')}
    _sp['cmts_type'] = cmts_type

    def _safe_delta(series):
        """last - first for cumulative counters, clipped to 0."""
        s = pd.to_numeric(series, errors='coerce').dropna()
        return max(float(s.iloc[-1]) - float(s.iloc[0]), 0) if len(s) >= 2 else 0.0

    def _bin_stats(grp, present):
        """Session-total bin deltas (last - first per bin).
        Returns (wavg_ms, p50_ms, p99_ms, p999_ms, total_pkts) all in ms."""
        def _safe_int(v):
            x = pd.to_numeric(v, errors='coerce')
            return 0 if pd.isna(x) else int(x)
        deltas = [max(_safe_int(grp[c].iloc[-1]) - _safe_int(grp[c].iloc[0]), 0)
                  for c in present]
        total = sum(deltas)
        if total == 0:
            return 0.0, 0.0, 0.0, 0.0, 0

        # Build bin midpoints in ms from edge columns
        edge_cols_15 = [f'lat_edge_bin{i}' for i in range(1, 16)]
        edge_cols_16 = [f'lat_edge_bin{i}' for i in range(1, 17)]
        present_15 = [c for c in edge_cols_15 if c in grp.columns]
        present_16 = [c for c in edge_cols_16 if c in grp.columns]
        edge_row = grp[present_16 if present_16 else present_15].dropna(how='all') if (present_16 or present_15) else pd.DataFrame()
        midpoints_ms = []
        if not edge_row.empty:
            ecols = present_16 if present_16 else present_15
            edges = [pd.to_numeric(edge_row[c].iloc[0], errors='coerce') for c in ecols]
            edges = [e for e in edges if pd.notna(e)]
            # SNMP edges are in µs (e.g. 5, 10, 25 µs) — divide by 1000 to get ms
            # Kafka edges are already in ms (e.g. 0.05, 0.1, 0.25 ms)
            if edges and edges[0] >= 1.0:
                edges = [e / 1000.0 for e in edges]
            boundaries = [0.0] + edges + [edges[-1] * 2 if edges else float(len(present))]
            for i in range(len(present)):
                lo = boundaries[i] if i < len(boundaries) else boundaries[-1]
                hi = boundaries[i+1] if i+1 < len(boundaries) else boundaries[-1] * 2
                midpoints_ms.append((lo + hi) / 2.0 if pd.notna(lo) and pd.notna(hi) else 0.0)
        else:
            # No edge data — fall back to bin index as ms approximation
            midpoints_ms = [float(i + 1) for i in range(len(present))]

        def _pct_ms(pct):
            target, cumulative = total * pct, 0
            for i, count in enumerate(deltas):
                cumulative += count
                if cumulative >= target:
                    return round(midpoints_ms[i] if i < len(midpoints_ms) else float(i + 1), 3)
            return round(midpoints_ms[-1] if midpoints_ms else float(len(deltas)), 3)

        wavg_ms = sum(float(midpoints_ms[i]) * float(deltas[i])
                      for i in range(len(deltas))
                      if pd.notna(midpoints_ms[i]) and pd.notna(deltas[i])) / total
        return (round(wavg_ms, 3), _pct_ms(0.50), _pct_ms(0.99), _pct_ms(0.999), total)

    # rows: (lbl, dir, src, peak_mbps, avg_mbps, wavg_ms, max_ms,
    #        p50, p99, p999, aqm, aqm_pct, ce, ce_pct, sanctioned, sanc_pct, loss_pct)
    rows = []

    # --- SNMP US ---
    if us is not None and not us.empty:
        for sfid, grp in us.groupby('sfid'):
            grp  = grp.sort_values('captured_utc')
            lbl  = sfid_map.get(str(sfid), grp['sfid_label'].iloc[0] if 'sfid_label' in grp.columns else str(sfid))
            peak_tp = _peak_mbps_snmp(grp)
            tp_df   = _compute_throughput_mbps(grp.copy(), 'sfid')
            avg_tp  = tp_df['throughput_mbps'].dropna().mean()
            avg_tp  = round(avg_tp, 1) if pd.notna(avg_tp) else 0
            lat_max = pd.to_numeric(grp.get('lat_max_usec', pd.Series()), errors='coerce').max()
            lat_max_ms = lat_max / 1000 if pd.notna(lat_max) else 0
            bin_cols = [f'lat_bin{i}' for i in range(1, 17)]
            present  = [c for c in bin_cols if c in grp.columns]
            if present:
                wavg, p50, p99, p999, bin_total = _bin_stats(grp, present)
            else:
                wavg = p50 = p99 = p999 = bin_total = 0
            aqm        = _safe_delta(grp.get('cong_aqm_drop',   pd.Series(dtype=float)))
            ce         = _safe_delta(grp.get('cong_ce_marked',  pd.Series(dtype=float)))
            sanctioned = _safe_delta(grp.get('cong_sanctioned', pd.Series(dtype=float)))
            ref = bin_total or 1
            rows.append((lbl, 'US', 'SNMP',
                         round(peak_tp, 1), avg_tp,
                         round(wavg, 3), round(lat_max_ms, 3),
                         p50, p99, p999,
                         int(aqm), f'{aqm/ref*100:.2f}%',
                         int(ce),  f'{ce/ref*100:.2f}%',
                         int(sanctioned), f'{sanctioned/ref*100:.2f}%',
                         0.0))

    # --- Kafka US + DS ---
    for kdf, direction, source in [(k_us, 'US', 'Kafka'), (k_ds, 'DS', 'Kafka')]:
        if kdf is None or kdf.empty:
            continue
        grp_col = 'sfid_label' if 'sfid_label' in kdf.columns else 'sfid'
        for sfid, grp in kdf.groupby(grp_col):
            grp = grp.sort_values('captured_utc')
            peak_tp    = _peak_mbps_kafka(grp)
            kdf_tp     = _compute_throughput_mbps(grp.copy(), grp_col)
            avg_tp     = kdf_tp['throughput_mbps'].dropna().mean()
            avg_tp     = round(avg_tp, 1) if pd.notna(avg_tp) else 0
            lat_avg    = pd.to_numeric(grp.get('lat_avg_usec', pd.Series()), errors='coerce') / 1000
            avg_lat_ms = lat_avg[lat_avg > 0].mean() if not lat_avg[lat_avg > 0].empty else 0
            lat_max    = pd.to_numeric(grp.get('lat_max_usec', pd.Series()), errors='coerce').max()
            lat_max_ms = lat_max / 1000 if pd.notna(lat_max) else 0
            bin_cols = [f'lat_bin{i}' for i in range(1, 17)]
            present  = [c for c in bin_cols if c in grp.columns]
            if present:
                wavg, p50, p99, p999, bin_total = _bin_stats(grp, present)
            else:
                wavg, p50, p99, p999, bin_total = avg_lat_ms, 0, 0, 0, 0
            aqm_s = pd.to_numeric(grp.get('cong_aqm_drop',   pd.Series(dtype=float)), errors='coerce').dropna()
            ce_s  = pd.to_numeric(grp.get('cong_ce_marked',  pd.Series(dtype=float)), errors='coerce').dropna()
            san_s = pd.to_numeric(grp.get('cong_sanctioned', pd.Series(dtype=float)), errors='coerce').dropna()
            aqm        = max(float(aqm_s.max()) - float(aqm_s.min()), 0) if not aqm_s.empty else 0
            ce         = max(float(ce_s.max())  - float(ce_s.min()),  0) if not ce_s.empty  else 0
            sanctioned = max(float(san_s.max()) - float(san_s.min()), 0) if not san_s.empty else 0
            pkts_pass  = pd.to_numeric(grp.get('delta_pkts',         pd.Series(dtype=float)), errors='coerce').sum()
            pkts_drop  = pd.to_numeric(grp.get('delta_pkts_dropped', pd.Series(dtype=float)), errors='coerce').sum()
            total_pkts = pkts_pass + pkts_drop
            loss_pct   = pkts_drop / total_pkts * 100 if total_pkts > 0 else 0.0
            ref        = bin_total or total_pkts or 1
            rows.append((str(sfid), direction, source,
                         round(peak_tp, 1), avg_tp,
                         round(wavg, 3), round(lat_max_ms, 3),
                         p50, p99, p999,
                         int(aqm), f'{aqm/ref*100:.2f}%',
                         int(ce),  f'{ce/ref*100:.2f}%',
                         int(sanctioned), f'{sanctioned/ref*100:.2f}%',
                         round(loss_pct, 3)))

    if not rows:
        return

    # --- ThousandEyes results ---
    te_results = _load_te_results(session_dir)
    te_rows = []
    for te in te_results:
        for test_name, data in te.get('results', {}).items():
            if test_name == 'http_get_mt':
                mbps = round(data.get('bytes_sec', 0) * 8 / 1_000_000, 2)
                te_rows.append(('http_get_mt (DS)', 'DS', f'{mbps} Mbps', '\u2014', '\u2014'))
            elif test_name == 'http_post_mt':
                mbps = round(data.get('bytes_sec', 0) * 8 / 1_000_000, 2)
                te_rows.append(('http_post_mt (US)', 'US', f'{mbps} Mbps', '\u2014', '\u2014'))
            elif test_name == 'udp_jitter':
                lat_ms = round(data.get('latency', 0) / 1000, 3)
                dj_ms  = round(data.get('down_jitter', 0) / 1000, 3)
                uj_ms  = round(data.get('up_jitter', 0) / 1000, 3)
                te_rows.append(('udp_jitter', 'DS/US', '\u2014', f'{lat_ms} ms', f'\u2193{dj_ms} \u2191{uj_ms} ms'))

    # --- Layout ---
    fig = plt.figure(figsize=(11, 8.5))
    fig.patch.set_facecolor(BG_DARK)
    te_table_h = 0.22 if te_rows else 0
    cmts_top   = 0.08 + te_table_h
    cmts_h     = 0.78 - te_table_h

    ax = fig.add_axes([0.03, cmts_top, 0.94, cmts_h])
    ax.set_facecolor(BG_PANEL)
    ax.axis('off')

    col_labels = ['SFID / Service Class', 'Dir', 'Src',
                  'Peak\nMbps', 'Avg\nMbps', 'WAvg\n(ms)', 'Max\n(ms)',
                  'P50\n(ms)', 'P99\n(ms)', 'P99.9\n(ms)',
                  'AQM\nDrop', 'AQM%',
                  'CE\nMark', 'CE%',
                  'Sanc.', 'Sanc%', 'Loss%']
    col_widths = [0.14, 0.04, 0.04,
                  0.05, 0.05, 0.05, 0.05,
                  0.04, 0.04, 0.05,
                  0.05, 0.05,
                  0.05, 0.05,
                  0.04, 0.05, 0.04]

    table_data = [[str(v) for v in r] for r in rows]
    tbl = ax.table(
        cellText=table_data,
        colLabels=col_labels,
        colWidths=col_widths,
        loc='center', cellLoc='center',
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(7)
    tbl.scale(1, 1.6)

    for col in range(len(col_labels)):
        cell = tbl[0, col]
        cell.set_facecolor(ACCENT)
        cell.set_text_props(color='white', fontweight='bold')

    pct_cols = {col_labels.index(h) for h in ('AQM%', 'CE%', 'Sanc%')}
    for row_i in range(len(rows)):
        bg = BG_PANEL if row_i % 2 == 0 else BG_DARK
        for col in range(len(col_labels)):
            cell = tbl[row_i + 1, col]
            cell.set_facecolor('#0d2a4a' if col in pct_cols else bg)
            cell.set_text_props(color='#00c6ff' if col in pct_cols else TEXT_COLOR)
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
            loc='center', cellLoc='center',
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

    save_page(pdf, fig, ax, 'SESSION SUMMARY \u2014 THROUGHPUT & LATENCY',
              f'{m["modem_name"]} ({m["mac_fmt"]})  |  Peak & Avg Mbps  |  WAvg latency from session bin deltas  |  AQM/CE/Sanc counts + %',
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
        plot_bar_grouped(ax, us_pd, ['flow_policed_drop', 'flow_policed_delay'],
                         ['drop', 'delay'], 'sfid_label', 'Packets (delta)')
        save_page(pdf, fig, ax, 'US POLICED DROP & DELAY (SNMP)',
                  f'{m["modem_name"]} ({m["mac_fmt"]})  |  US Service Flows — per-poll delta', **_sp)

    if 'flow_aqm_drop' in us.columns and not us['flow_aqm_drop'].isna().all():
        us_aqm = _delta_col(us, 'flow_aqm_drop')
        fig, ax = make_fig()
        plot_bar_grouped(ax, us_aqm, ['flow_aqm_drop'], ['AQM drop'], 'sfid_label', 'Packets (delta)')
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
    # SNMP lat_edge_bin values are stored in units of 100µs — multiply by 10 to get ms
    if len(present) == len(edge_cols_15):
        edges = [e * 10 for e in edges]
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
        if sum(totals) == 0:
            continue  # SFID has no latency bin data — skip page
        edge_labels = _get_edge_labels(grp, n_bins)
        colors = CHART_COLORS[:n_bins] if n_bins <= len(CHART_COLORS) \
                 else [CHART_COLORS[i % len(CHART_COLORS)] for i in range(n_bins)]
        fig, ax = make_fig()
        ax.bar(x, totals, color=colors, edgecolor=BG_DARK, linewidth=0.5, width=0.7)
        ax.set_xticks(x)
        ax.set_xticklabels(edge_labels, color=TEXT_COLOR, fontsize=7, rotation=35, ha='right')
        ax.set_ylabel('Packets (total delta)', color=SUBTEXT, fontsize=10, fontweight='bold')
        ax.set_xlabel('Latency Range', color=SUBTEXT, fontsize=10)
        ax.grid(True, color=GRID_COLOR, linewidth=0.7, linestyle='--', alpha=0.8, axis='y')
        ax.set_axisbelow(True)
        ax.tick_params(colors=TEXT_COLOR)
        for spine in ax.spines.values():
            spine.set_edgecolor(GRID_COLOR)
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

    cong_bar_cols   = [c for c in ['cong_aqm_drop', 'cong_ce_marked', 'cong_sanctioned'] if c in present]
    cong_bar_labels = [c.replace('cong_', '').replace('_', ' ') for c in cong_bar_cols]
    if cong_bar_cols:
        fig, ax = make_fig()
        plot_bar_grouped(ax, us_d, cong_bar_cols, cong_bar_labels, 'sfid_label', 'Packets (delta)')
        save_page(pdf, fig, ax, 'US CONGESTION — AQM DROPS & CE MARKED (SNMP)',
                  f'{m["modem_name"]} ({m["mac_fmt"]})  |  per-poll delta per SFID', **_sp)

    if 'cong_ect0' in present and 'cong_ect1' in present:
        fig, ax = make_fig()
        plot_bar_grouped(ax, us_d, ['cong_ect0', 'cong_ect1'], ['ECT(0)', 'ECT(1)'],
                         'sfid_label', 'Packets (delta)')
        save_page(pdf, fig, ax, 'US ECT(0) & ECT(1) PACKETS (SNMP)',
                  f'{m["modem_name"]} ({m["mac_fmt"]})  |  per-poll delta per SFID', **_sp)




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
        ds_pd = _delta_col(_delta_col(ds, 'flow_policed_drop'), 'flow_policed_delay')
        fig, ax = make_fig()
        plot_bar_grouped(ax, ds_pd, ['flow_policed_drop', 'flow_policed_delay'],
                         ['drop', 'delay'], 'sfid_label', 'Packets (delta)')
        save_page(pdf, fig, ax, 'DS POLICED DROP & DELAY (SNMP)',
                  f'{m["modem_name"]} ({m["mac_fmt"]})  |  DS Service Flows — per-poll delta', **_sp)

    if 'flow_aqm_drop' in ds.columns and not ds['flow_aqm_drop'].isna().all():
        ds_aqm = _delta_col(ds, 'flow_aqm_drop')
        fig, ax = make_fig()
        plot_bar_grouped(ax, ds_aqm, ['flow_aqm_drop'], ['AQM drop'], 'sfid_label', 'Packets (delta)')
        save_page(pdf, fig, ax, 'DS AQM DROPPED PACKETS (SNMP)',
                  f'{m["modem_name"]} ({m["mac_fmt"]})  |  DS Service Flows — per-poll delta', **_sp)


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

    cong_bar_cols   = [c for c in ['cong_aqm_drop', 'cong_ce_marked'] if c in present]
    cong_bar_labels = [c.replace('cong_', '').replace('_', ' ') for c in cong_bar_cols]
    if cong_bar_cols:
        fig, ax = make_fig()
        plot_bar_grouped(ax, ds_d, cong_bar_cols, cong_bar_labels, 'sfid_label', 'Packets (delta)')
        save_page(pdf, fig, ax, 'DS CONGESTION — AQM DROPS & CE MARKED (SNMP)',
                  f'{m["modem_name"]} ({m["mac_fmt"]})  |  per-poll delta per SFID', **_sp)

    if 'cong_ect0' in present and 'cong_ect1' in present:
        fig, ax = make_fig()
        plot_bar_grouped(ax, ds_d, ['cong_ect0', 'cong_ect1'], ['ECT(0)', 'ECT(1)'],
                         'sfid_label', 'Packets (delta)')
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
    ax.set_ylim(bottom=0)
    from matplotlib.ticker import MultipleLocator
    ymax = ax.get_ylim()[1]
    step = 5 if ymax <= 100 else 10 if ymax <= 250 else 25 if ymax <= 500 else 50
    ax.yaxis.set_major_locator(MultipleLocator(step))
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
    from matplotlib.ticker import MultipleLocator
    ymax = ax.get_ylim()[1]
    step = 5 if ymax <= 100 else 10 if ymax <= 250 else 25 if ymax <= 500 else 50
    ax.yaxis.set_major_locator(MultipleLocator(step))
    ax.set_ylim(bottom=0)
    fmt_ax(ax)
    save_page(pdf, fig, ax,
              f'{direction} LATENCY DISTRIBUTION — VIOLIN ({source})',
              f'{m["modem_name"]} ({m["mac_fmt"]})  |  distribution across all polls',
              **_sp)


def page_latency_percentile(pdf, df, direction, group_col, source='SNMP', **m):
    """CDF chart: x=percentile (logit), y=latency (ms) — one curve per SFID."""
    import numpy as np
    bin_cols  = [f'lat_bin{i}'      for i in range(1, 17)]
    edge_cols = [f'lat_edge_bin{i}' for i in range(1, 16)]
    present_bins  = [c for c in bin_cols  if c in df.columns]
    present_edges = [c for c in edge_cols if c in df.columns]
    if not present_bins:
        return
    _sp = {k: m[k] for k in ('mac_fmt', 'modem_name', 'session_start', 'session_end')}
    _sp['cmts_type'] = m.get('cmts_type', 'icmts')

    PCT_MARKS  = [('P50', 0.50), ('P90', 0.90), ('P99', 0.99), ('P99.99', 0.9999)]
    PCT_TICKS  = [0.50, 0.90, 0.99, 0.9999]
    PCT_LABELS = ['P50', 'P90', 'P99', 'P99.99']

    def _build_midpoints_snmp(grp):
        edges_row = grp[present_edges].dropna(how='all') if present_edges else pd.DataFrame()
        if not edges_row.empty:
            edges = [float(edges_row[c].iloc[0]) for c in present_edges
                     if pd.to_numeric(edges_row[c].iloc[0], errors='coerce') > 0]
        else:
            edges = list(range(1, len(present_bins) + 1))
        boundaries = [0] + edges + [edges[-1] * 2 if edges else len(present_bins) + 1]
        n_mid = min(len(present_bins), len(boundaries) - 1)
        mids = [(boundaries[j] + boundaries[j + 1]) / 2 / 1000.0 for j in range(n_mid)]
        while len(mids) < len(present_bins):
            mids.append(mids[-1] * 2 if mids else float(len(mids) + 1))
        return mids

    def _build_midpoints_kafka(grp, present_edges_k):
        edges_row = grp[present_edges_k].dropna(how='all') if present_edges_k else pd.DataFrame()
        if not edges_row.empty:
            edges = [float(edges_row[c].iloc[0]) for c in present_edges_k
                     if pd.to_numeric(edges_row[c].iloc[0], errors='coerce') > 0]
        else:
            edges = list(range(1, len(present_bins) + 1))
        boundaries = [0] + [e for e in edges if np.isfinite(e)]
        if len(boundaries) < 2:
            boundaries = [0] + list(range(1, len(present_bins) + 2))
        boundaries.append(boundaries[-1] * 2)
        n_mid = min(len(present_bins), len(boundaries) - 1)
        mids = [(boundaries[j] + boundaries[j + 1]) / 2 for j in range(n_mid)]
        while len(mids) < len(present_bins):
            mids.append(mids[-1] * 2 if mids else float(len(mids) + 1))
        return mids

    def _draw_cdf(ax, cdf_arr, lat_arr, color, label):
        """Plot with x=percentile (logit), y=latency (ms)."""
        pct_clipped = np.clip(cdf_arr, 1e-6, 1 - 1e-6)
        sx, sy = _smooth_xy(pd.Series(pct_clipped), pd.Series(lat_arr))
        sy = np.clip(sy, 0, None)
        ax.plot(sx, sy, linewidth=2.5, color=color, label=label)
        ax.fill_betweenx(sy, sx, PCT_TICKS[0], alpha=0.07, color=color)
        ax.plot(pct_clipped[1:], lat_arr[1:], marker='o', markersize=4, linewidth=0,
                color=color, markerfacecolor='white', markeredgecolor=color, markeredgewidth=1.5)

    def _annotate_pcts(ax, cdf_arr, lat_arr, color):
        for pct_label, pct_val in PCT_MARKS:
            idx = np.searchsorted(cdf_arr, pct_val)
            if idx == 0 or idx >= len(lat_arr):
                continue
            lo_pct, hi_pct = cdf_arr[idx - 1], cdf_arr[idx]
            lo_lat, hi_lat = lat_arr[idx - 1], lat_arr[idx]
            lat_at_pct = hi_lat if hi_pct == lo_pct else \
                lo_lat + (pct_val - lo_pct) / (hi_pct - lo_pct) * (hi_lat - lo_lat)
            pct_clipped = np.clip(pct_val, 1e-6, 1 - 1e-6)
            ax.plot(pct_clipped, lat_at_pct, marker='D', markersize=5, color=color,
                    markerfacecolor=color, markeredgecolor='white', markeredgewidth=0.8, zorder=5)
            ax.annotate(f'{pct_label}\n{lat_at_pct:.2f}ms',
                        xy=(pct_clipped, lat_at_pct),
                        xytext=(0, 6), textcoords='offset points',
                        fontsize=6.5, color=color, ha='center', va='bottom')

    def _finalise_ax(ax):
        ax.set_xscale('logit')
        ax.set_xlim(PCT_TICKS[0], 0.99999)
        ax.set_xticks(PCT_TICKS)
        ax.set_xticklabels(PCT_LABELS, color=TEXT_COLOR, fontsize=8)
        ax.xaxis.set_minor_locator(plt.NullLocator())
        ax.set_xlabel('Percentile', color=SUBTEXT, fontsize=10, fontweight='bold')
        ax.set_ylabel('Latency (ms)', color=SUBTEXT, fontsize=10, fontweight='bold')
        ax.yaxis.set_major_formatter(plt.ScalarFormatter())
        from matplotlib.ticker import MultipleLocator
        ymax = ax.get_ylim()[1]
        step = 5 if ymax <= 100 else 10 if ymax <= 250 else 25 if ymax <= 500 else 50
        ax.yaxis.set_major_locator(MultipleLocator(step))
        plt.setp(ax.yaxis.get_majorticklabels(), color=TEXT_COLOR)
        ax.legend(fontsize=8, facecolor=BG_DARK, edgecolor=GRID_COLOR,
                  labelcolor=TEXT_COLOR, framealpha=0.9)
        ax.grid(True, color=GRID_COLOR, linewidth=0.7, linestyle='--', alpha=0.8)
        ax.set_axisbelow(True)

    # ------------------------------------------------------------------ SNMP
    if source == 'SNMP':
        diff_key = 'sfid' if 'sfid' in df.columns else group_col
        df = df.copy().sort_values([diff_key, 'captured_utc'])
        if df.empty:
            return
        for c in present_bins:
            df[c] = pd.to_numeric(df[c], errors='coerce')
            df[c] = df.groupby(diff_key)[c].diff().clip(lower=0)

        fig, ax = make_fig()
        for i, (sfid, grp) in enumerate(df.groupby(group_col)):
            mids = _build_midpoints_snmp(grp)
            totals = grp[present_bins].sum()
            counts = [float(totals.get(c, 0) or 0) for c in present_bins]
            grand_total = sum(counts)
            color = CHART_COLORS[i % len(CHART_COLORS)]
            if grand_total == 0:
                ax.plot([], [], linewidth=2.5, color=color, label=f'{sfid} (no data)')
                continue
            lat_pts = np.array([0.0] + mids)
            cdf_pts = np.array([0.0] + [sum(counts[:k + 1]) / grand_total for k in range(len(counts))])
            _draw_cdf(ax, cdf_pts, lat_pts, color, str(sfid))
            _annotate_pcts(ax, cdf_pts, lat_pts, color)

        _finalise_ax(ax)
        save_page(pdf, fig, ax,
                  f'{direction} LATENCY CDF — P50 to P99.99 ({source})',
                  f'{m["modem_name"]} ({m["mac_fmt"]})  |  x=percentile  y=latency (ms)  |  aggregated across all polls',
                  **_sp)
        return

    # ------------------------------------------------------------------ Kafka
    diff_key = 'sfid' if 'sfid' in df.columns else group_col
    df = df.copy().sort_values([diff_key, 'captured_utc'])
    if df.empty:
        return
    for c in present_bins:
        df[c] = pd.to_numeric(df[c], errors='coerce')
        df[c] = df.groupby(diff_key)[c].diff().clip(lower=0)

    edge_cols_16       = [f'lat_edge_bin{i}' for i in range(1, 17)]
    present_edges_kafka = [c for c in edge_cols_16 if c in df.columns]

    fig, ax = make_fig()
    for i, (sfid, grp) in enumerate(df.groupby(group_col)):
        mids = _build_midpoints_kafka(grp, present_edges_kafka)
        totals = grp[present_bins].sum()
        counts = [float(totals.get(c, 0) or 0) for c in present_bins]
        grand_total = sum(counts)
        color = CHART_COLORS[i % len(CHART_COLORS)]
        if grand_total == 0:
            ax.plot([], [], linewidth=2.5, color=color, label=f'{sfid} (no data)')
            continue
        lat_pts = np.array([0.0] + mids)
        cdf_pts = np.array([0.0] + [sum(counts[:k + 1]) / grand_total for k in range(len(counts))])
        _draw_cdf(ax, cdf_pts, lat_pts, color, str(sfid))
        _annotate_pcts(ax, cdf_pts, lat_pts, color)

    _finalise_ax(ax)
    save_page(pdf, fig, ax,
              f'{direction} LATENCY CDF — P50 to P99.99 ({source})',
              f'{m["modem_name"]} ({m["mac_fmt"]})  |  x=percentile  y=latency (ms)  |  aggregated across all polls',
              **_sp)

# ---------------------------------------------------------------------------
# Shared twin-axis correlation figure builder
# ---------------------------------------------------------------------------
def _dual_panel_fig(pdf, group_col,
                    top_df, top_col, top_ylabel, top_fmt, top_accent,
                    bot_df, bot_col, bot_ylabel, bot_fmt, bot_accent,
                    header_title, subtitle, _sp):
    """Single chart with twin y-axes: left=top metric (solid), right=bottom metric (dashed).
    Both series share the same time x-axis. Per-SFID color is consistent across both axes.
    """
    import matplotlib.ticker as mticker

    fig, ax_left = plt.subplots(figsize=(11, 5.8), subplot_kw={'facecolor': BG_PANEL})
    fig.patch.set_facecolor(BG_DARK)
    fig.subplots_adjust(top=0.88, bottom=0.18, left=0.10, right=0.90)
    style_ax(ax_left)
    ax_right = ax_left.twinx()
    style_ax(ax_right)

    # Collect all SFIDs across both dataframes to assign consistent colors
    all_sfids = list(dict.fromkeys(
        list(top_df[group_col].unique()) + list(bot_df[group_col].unique())
    ))
    color_map = {sfid: CHART_COLORS[i % len(CHART_COLORS)] for i, sfid in enumerate(all_sfids)}

    for name, grp in top_df.groupby(group_col):
        c = color_map[name]
        rx = grp['captured_utc']
        ry = pd.to_numeric(grp[top_col], errors='coerce')
        sx, sy = _smooth_xy(rx, ry)
        ax_left.plot(sx, sy, linewidth=2.2, color=c, label=str(name))
        ax_left.fill_between(sx, sy, alpha=0.10, color=c)
        ax_left.plot(rx, ry, 'o', markersize=4, linewidth=0, color=c,
                     markerfacecolor='white', markeredgecolor=c, markeredgewidth=1.5)

    for name, grp in bot_df.groupby(group_col):
        c = color_map[name]
        rx = grp['captured_utc']
        ry = pd.to_numeric(grp[bot_col], errors='coerce')
        sx, sy = _smooth_xy(rx, ry)
        ax_right.plot(sx, sy, linewidth=2.0, color=c, linestyle='--', alpha=0.85)
        ax_right.plot(rx, ry, 's', markersize=4, linewidth=0, color=c,
                      markerfacecolor='white', markeredgecolor=c, markeredgewidth=1.5)

    ax_left.set_ylabel(top_ylabel, color=top_accent, fontsize=10, fontweight='bold')
    ax_left.tick_params(axis='y', colors=top_accent, labelsize=8)
    ax_left.spines['left'].set_edgecolor(top_accent)
    ax_left.spines['left'].set_linewidth(1.2)
    ax_left.yaxis.set_major_formatter(mticker.StrMethodFormatter(top_fmt))

    ax_right.set_ylabel(bot_ylabel, color=bot_accent, fontsize=10, fontweight='bold')
    ax_right.tick_params(axis='y', colors=bot_accent, labelsize=8)
    ax_right.spines['right'].set_edgecolor(bot_accent)
    ax_right.spines['right'].set_linewidth(1.2)
    ax_right.yaxis.set_major_formatter(mticker.StrMethodFormatter(bot_fmt))
    ax_right.grid(False)
    if 'latency' in bot_ylabel.lower() or 'ms' in bot_ylabel.lower():
        from matplotlib.ticker import MultipleLocator
        ax_right.autoscale(axis='y')
        ymax = max(ax_right.get_ylim()[1], 50)  # minimum visible range 0–50 ms
        step = 5 if ymax <= 100 else 10 if ymax <= 250 else 25 if ymax <= 500 else 50
        ax_right.set_ylim(0, ymax)
        ax_right.yaxis.set_major_locator(MultipleLocator(step))
    else:
        ax_right.set_ylim(bottom=0)

    ax_left.set_xlabel('Time (UTC)', color=SUBTEXT, fontsize=10)
    fmt_ax(ax_left)
    ax_left.set_ylim(bottom=0)

    # Legend: solid patch per SFID + style note
    from matplotlib.lines import Line2D
    handles = [Line2D([0], [0], color=color_map[s], linewidth=2, label=str(s))
               for s in all_sfids]
    handles += [
        Line2D([0], [0], color='#888888', linewidth=2,   linestyle='-',  label=f'— {top_ylabel}'),
        Line2D([0], [0], color='#888888', linewidth=1.5, linestyle='--', label=f'-- {bot_ylabel}'),
    ]
    ax_left.legend(handles=handles, fontsize=7.5, facecolor=BG_DARK, edgecolor=GRID_COLOR,
                   labelcolor=TEXT_COLOR, framealpha=0.9, ncol=2, loc='upper left')

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
    aqm_ylabel = 'AQM Drops (pkts/Δ)'
    aqm_df = df.dropna(subset=['_aqm_delta'])
    lat_df = df.dropna(subset=['_lat_ms'])
    if aqm_df.empty or lat_df.empty:
        return
    dir_label = direction.upper()
    _dual_panel_fig(
        pdf, group_col,
        aqm_df, '_aqm_delta', aqm_ylabel,      '{x:,.0f}', '#ea4335',
        lat_df, '_lat_ms',    'Latency (ms)',   '{x:,.2f}', '#00c6ff',
        f'{dir_label} AQM DROPS vs LATENCY ({source})',
        f'{m["modem_name"]} ({m["mac_fmt"]})  |  AQM drop delta above  |  Latency inverted below',
        _sp,
    )


def page_kafka_congestion(pdf, kdf, direction, **m):
    """AQM drop, marked, and sanctioned packets over time per flow — per-poll deltas."""
    cong_cols  = ['cong_aqm_drop', 'cong_ce_marked', 'cong_sanctioned']
    present    = [c for c in cong_cols if c in kdf.columns and not kdf[c].isna().all()]
    if not present:
        return
    label   = direction.upper()
    grp_col = 'sfid_label' if 'sfid_label' in kdf.columns else 'sfid'
    _sp     = {k: m[k] for k in ('mac_fmt','modem_name','session_start','session_end')}
    _sp['cmts_type'] = m.get('cmts_type', 'vcmts')

    # Diff raw cumulative counters by sfid to get per-poll deltas
    kdf = kdf.copy().sort_values(['sfid', 'captured_utc'])
    for c in present:
        kdf[c] = pd.to_numeric(kdf[c], errors='coerce')
        kdf[c] = kdf.groupby('sfid')[c].diff().clip(lower=0)

    cong_bar_cols   = [c for c in ['cong_aqm_drop', 'cong_ce_marked', 'cong_sanctioned'] if c in present]
    cong_bar_labels = [c.replace('cong_', '').replace('_', ' ') for c in cong_bar_cols]
    if cong_bar_cols:
        fig, ax = make_fig()
        plot_bar_grouped(ax, kdf, cong_bar_cols, cong_bar_labels, grp_col, 'Packets (delta)')
        save_page(pdf, fig, ax, f'{label} CONGESTION — AQM DROPS & CE MARKED (Kafka)',
                  f'{m["modem_name"]} ({m["mac_fmt"]})  |  per-poll delta per SFID', **_sp)


# SFIDs that are OID artefacts / aggregate counters — never real service flows
_SFID_BLOCKLIST = {'0', '123', '0123'}

# SCN name fragments that identify non-data service flows to exclude from charts
_SCN_BLOCKLIST_RE = re.compile(r'wft|vid', re.IGNORECASE)


def _is_real_sfid(sfid_str):
    """Return True if sfid_str is a plausible service-flow ID (not a blocklisted artefact)."""
    return sfid_str.strip() not in _SFID_BLOCKLIST


def _drop_blocked_scn(df):
    """Remove rows whose sfid_label SCN matches WFT or VID service classes."""
    if 'sfid_label' not in df.columns:
        return df
    mask = df['sfid_label'].str.contains(_SCN_BLOCKLIST_RE, na=False)
    return df[~mask].copy()


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
    return _drop_blocked_scn(df).sort_values('captured_utc').reset_index(drop=True)


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

    us = _drop_blocked_scn(df[df['dir'] == 'upstream'].copy())
    ds = _drop_blocked_scn(df[df['dir'] == 'downstream'].copy())
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
    result_type = _detect_result_type(sess['session_dir'])
    pg3_title, pg3_desc = _RESULT_TYPE_TOC[result_type]

    if cmts_type == 'vcmts':
        toc = [
            ('3',  pg3_title,                          pg3_desc),
            ('4',  'US Flow Throughput (SNMP)',         'Per-poll delta octets → Mbps per US service flow'),
            ('5',  'US Latency Avg (SNMP)',             'Weighted avg latency from bin deltas per poll'),
            ('6',  'US Throughput & Latency Corr.',     'Mirrored chart: throughput above, latency inverted below'),
            ('7',  'US Latency Scatter (SNMP)',         'Per-poll latency scatter per US SFID'),
            ('8',  'US Latency CDF (SNMP)',             'CDF: x=latency (ms), y=percentile P50–P99.99 per SFID'),
            ('9',  'US Latency Bins (SNMP)',            'Last − first poll bin delta per US SFID'),
            ('10', 'US Congestion AQM & CE (SNMP)',     'AQM drops and CE marked packets per US flow'),
            ('11', 'DS Throughput (Kafka)',             'Kafka delta_octets → Mbps per DS flow'),
            ('12', 'DS Latency Avg (Kafka)',            'Kafka average latency per DS flow over time'),
            ('13', 'DS Throughput & Latency Corr.',     'Mirrored chart: throughput above, latency inverted below'),
            ('14', 'DS Latency CDF (Kafka)',            'CDF: x=latency (ms), y=percentile P50–P99.99 per SFID'),
            ('15', 'DS Latency Bins (Kafka)',           'Kafka last − first bin delta per DS SFID'),
            ('16', 'DS Congestion (Kafka)',             'Kafka AQM drop and marked packets per DS flow'),
            ('17', 'Session Summary',                  'Peak throughput, latency, P50/P99, AQM drops per SFID'),
        ]
    else:
        toc = [
            ('3',  pg3_title,                          pg3_desc),
            ('4',  'US Flow Throughput (SNMP)',         'Per-poll delta octets → Mbps per US service flow'),
            ('5',  'US Latency Avg (SNMP)',             'Weighted avg latency from bin deltas per poll'),
            ('6',  'US Throughput & Latency Corr.',     'Mirrored chart: throughput above, latency inverted below'),
            ('7',  'US Policed Drops vs Throughput',    'Throughput above, policed drop delta inverted below'),
            ('8',  'US Latency Scatter (SNMP)',         'Per-poll latency scatter per US SFID'),
            ('9',  'US Latency CDF (SNMP)',             'CDF: x=latency (ms), y=percentile P50–P99.99 per SFID'),
            ('10', 'US Latency Bins (SNMP)',            'Last − first poll bin delta per US SFID'),
            ('11', 'US Congestion AQM & CE (SNMP)',     'AQM drops and CE marked packets per US flow'),
            ('12', 'US ECT(0) & ECT(1) (SNMP)',        'ECN capable transport packet counts per US flow'),
            ('13', 'DS Flow Throughput (SNMP)',         'Per-poll delta octets → Mbps per DS service flow'),
            ('14', 'DS Policed Drop & Delay (SNMP)',    'Policed drop and delay packet counts per DS flow'),
            ('15', 'DS AQM Dropped Packets (SNMP)',     'AQM drop counters per DS service flow'),
            ('16', 'DS Congestion AQM & CE (SNMP)',     'AQM drops and CE marked packets per DS flow'),
            ('17', 'DS Throughput & Latency Corr.',     'Mirrored chart: throughput above, latency inverted below'),
            ('18', 'DS Policed Drops vs Throughput',    'Throughput above, policed drop delta inverted below'),
            ('19', 'DS Latency Bins (SNMP)',            'Last − first poll bin delta per DS SFID'),
            ('20', 'Session Summary',                  'Peak throughput, latency, P50/P99, AQM drops per SFID'),
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
        page_latency_scatter(pdf, us, 'US', 'sfid_label', source='SNMP', **m)
        page_latency_percentile(pdf, us, 'US', 'sfid_label', source='SNMP', **m)
        page_us_latency_histogram(pdf, us, **m)
        page_us_congestion(pdf, us, **m)

        if cmts_type == 'vcmts':
            # DS Kafka charts only
            page_kafka_throughput(pdf, k_ds, 'downstream', **m)
            page_kafka_latency_avg(pdf, k_ds, 'downstream', **m)
            page_throughput_latency_correlation(pdf, k_ds, 'DS', source='Kafka', **m)
            page_latency_percentile(pdf, k_ds, 'DS', 'sfid_label', source='Kafka', **m)
            page_kafka_latency_histogram(pdf, k_ds, 'downstream', **m)
            page_kafka_congestion(pdf, k_us, 'upstream', **m)
            page_kafka_congestion(pdf, k_ds, 'downstream', **m)
        else:
            # DS from SNMP
            page_ds_flow_stats(pdf, ds, **m)
            page_ds_congestion(pdf, ds, **m)
            page_throughput_latency_correlation(pdf, ds, 'DS', source='SNMP', **m)
            page_policed_drops_throughput_correlation(pdf, ds, 'DS', **m)
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
