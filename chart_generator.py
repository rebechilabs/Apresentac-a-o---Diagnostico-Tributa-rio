"""
chart_generator.py

Generates chart images (PNG) using matplotlib for use in the
Diagnóstico Tributário PowerPoint presentation.

Charts match the flat, clean style of the template with brand colors.
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import Arc, Wedge, FancyBboxPatch
from matplotlib.collections import PatchCollection

# ---------------------------------------------------------------------------
# Font registration
# ---------------------------------------------------------------------------
_FONT_DIR = os.path.expanduser("~/Library/Fonts")

_montserrat_bold_path = os.path.join(_FONT_DIR, "Montserrat-Bold.ttf")
_poppins_bold_path = os.path.join(_FONT_DIR, "Poppins-Bold.ttf")

for _fpath in (_montserrat_bold_path, _poppins_bold_path):
    if os.path.isfile(_fpath):
        fm.fontManager.addfont(_fpath)

_montserrat_bold = fm.FontProperties(fname=_montserrat_bold_path)
_poppins_bold = fm.FontProperties(fname=_poppins_bold_path)

FONT_MONTSERRAT_BOLD = _montserrat_bold.get_name()
FONT_POPPINS_BOLD = _poppins_bold.get_name()

# ---------------------------------------------------------------------------
# Brand colours
# ---------------------------------------------------------------------------
COLOR_YELLOW = "#FFC824"
COLOR_RED = "#F07070"
COLOR_GREEN = "#4CAF50"
COLOR_DARK_GRAY = "#888888"
COLOR_LIGHT_GRAY = "#C0C0C0"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_brl(value: float) -> str:
    """Format a float as Brazilian Real currency string."""
    if value >= 1_000_000:
        return f"R$ {value / 1_000_000:,.2f}M".replace(",", "X").replace(".", ",").replace("X", ".")
    if value >= 1_000:
        return f"R$ {value / 1_000:,.1f}mil".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _set_defaults():
    """Apply common matplotlib rc defaults."""
    plt.rcParams.update({
        "figure.facecolor": "none",
        "axes.facecolor": "none",
        "savefig.facecolor": "none",
        "savefig.edgecolor": "none",
        "font.family": FONT_MONTSERRAT_BOLD,
    })


# ---------------------------------------------------------------------------
# 1. Donut chart
# ---------------------------------------------------------------------------

def generate_donut_chart(data: dict, output_path: str) -> str:
    """
    Creates a donut (ring) chart with 5 segments.

    Parameters in *data*:
        impostos_pct, cmv_pct, folha_pct, despesas_pct, lucro_pct
        tributos_valor, cmv_valor, folha_valor, despesas_valor, lucro_valor
    """
    _set_defaults()

    # Segment order: CMV (largest, starts at bottom), Impostos, Folha, Despesas, Lucro
    labels = ["CMV", "Impostos", "Folha", "Despesas", "Lucro"]
    sizes = [
        data["cmv_pct"],
        data["impostos_pct"],
        data["folha_pct"],
        data["despesas_pct"],
        data["lucro_pct"],
    ]
    values = [
        data["cmv_valor"],
        data["tributos_valor"],
        data["folha_valor"],
        data["despesas_valor"],
        data["lucro_valor"],
    ]
    colors = [COLOR_YELLOW, COLOR_RED, COLOR_DARK_GRAY, COLOR_LIGHT_GRAY, COLOR_GREEN]

    fig, ax = plt.subplots(figsize=(10, 10))
    fig.patch.set_alpha(0)

    # Start angle so CMV (the largest) sits at the bottom-center
    start_angle = 270 - (data["cmv_pct"] / 100 * 360) / 2

    wedges, _ = ax.pie(
        sizes,
        colors=colors,
        startangle=start_angle,
        counterclock=True,
        wedgeprops=dict(width=0.35, edgecolor="white", linewidth=2),
        radius=1.0,
    )

    # Draw labels with R$ values around the chart
    for i, (wedge, label, value) in enumerate(zip(wedges, labels, values)):
        angle = (wedge.theta2 + wedge.theta1) / 2
        angle_rad = np.deg2rad(angle)

        # Position labels outside the donut
        r_label = 1.25
        x = r_label * np.cos(angle_rad)
        y = r_label * np.sin(angle_rad)

        ha = "left" if x >= 0 else "right"
        va = "center"

        pct = sizes[i]
        brl = _fmt_brl(value)

        ax.text(
            x, y,
            f"{label}\n{pct:.0f}%  •  {brl}",
            ha=ha, va=va,
            fontproperties=_montserrat_bold,
            fontsize=11,
            color="#333333",
        )

        # Connector line
        r_inner = 0.85
        x0 = r_inner * np.cos(angle_rad)
        y0 = r_inner * np.sin(angle_rad)
        r_outer = 1.15
        x1 = r_outer * np.cos(angle_rad)
        y1 = r_outer * np.sin(angle_rad)
        ax.plot([x0, x1], [y0, y1], color="#AAAAAA", linewidth=0.8)

    ax.set_aspect("equal")
    ax.set_xlim(-1.8, 1.8)
    ax.set_ylim(-1.8, 1.8)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fig.savefig(output_path, dpi=300, transparent=True, bbox_inches="tight", pad_inches=0.3)
    plt.close(fig)
    return output_path


# ---------------------------------------------------------------------------
# 2. Gauge chart (two semicircular speedometers)
# ---------------------------------------------------------------------------

def generate_gauge_chart(lr_pct: float, lp_pct: float, output_path: str) -> str:
    """
    Creates a pair of semicircular gauge charts.

    lr_pct  – Lucro Real effective tax rate (%)
    lp_pct  – Lucro Presumido effective tax rate (%)
    """
    _set_defaults()

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.patch.set_alpha(0)

    gauge_data = [
        (lr_pct, "LUCRO REAL"),
        (lp_pct, "LUCRO PRESUMIDO"),
    ]

    max_pct = 25.0  # typical upper bound for the gauge

    for ax, (pct, title) in zip(axes, gauge_data):
        ax.set_aspect("equal")
        ax.set_xlim(-1.4, 1.4)
        ax.set_ylim(-0.4, 1.5)
        ax.axis("off")

        # Background arc (full semicircle, dark gray)
        bg_wedge = Wedge(
            center=(0, 0), r=1.0,
            theta1=0, theta2=180,
            width=0.30,
            facecolor=COLOR_DARK_GRAY, edgecolor="none", alpha=0.25,
        )
        ax.add_patch(bg_wedge)

        # Filled arc (proportional to pct)
        fill_angle = min(pct / max_pct, 1.0) * 180
        fill_wedge = Wedge(
            center=(0, 0), r=1.0,
            theta1=180 - fill_angle, theta2=180,
            width=0.30,
            facecolor=COLOR_YELLOW, edgecolor="none",
        )
        ax.add_patch(fill_wedge)

        # Percentage text in center
        ax.text(
            0, 0.30,
            f"{pct:.1f}%",
            ha="center", va="center",
            fontproperties=_poppins_bold,
            fontsize=36,
            color="#333333",
        )

        # Title below gauge
        ax.text(
            0, -0.25,
            title,
            ha="center", va="center",
            fontproperties=_montserrat_bold,
            fontsize=16,
            color="#555555",
        )

        # Scale labels (0% and max%)
        ax.text(-1.05, -0.08, "0%", ha="center", va="top",
                fontproperties=_montserrat_bold, fontsize=10, color=COLOR_DARK_GRAY)
        ax.text(1.05, -0.08, f"{max_pct:.0f}%", ha="center", va="top",
                fontproperties=_montserrat_bold, fontsize=10, color=COLOR_DARK_GRAY)

    fig.subplots_adjust(wspace=0.4)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fig.savefig(output_path, dpi=300, transparent=True, bbox_inches="tight", pad_inches=0.3)
    plt.close(fig)
    return output_path


# ---------------------------------------------------------------------------
# 3. Bar chart (tax reform projections)
# ---------------------------------------------------------------------------

def generate_bar_chart(anos_data: list, output_path: str) -> str:
    """
    Creates a bar chart for tax reform year-by-year projections.

    anos_data – list of dicts with 'ano' (int) and 'valor' (float) keys.
    """
    _set_defaults()

    anos = [d["ano"] for d in anos_data]
    valores = [d["valor"] for d in anos_data]

    fig, ax = plt.subplots(figsize=(15, 7))
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    x = np.arange(len(anos))
    bar_width = 0.55

    # Draw bars using FancyBboxPatch for rounded corners
    max_val = max(valores) if valores else 1
    for i, (xi, val) in enumerate(zip(x, valores)):
        bar_height = val
        rounding = max_val * 0.015  # subtle rounding
        fancy = FancyBboxPatch(
            (xi - bar_width / 2, 0),
            bar_width, bar_height,
            boxstyle=f"round,pad=0,rounding_size={rounding}",
            facecolor=COLOR_YELLOW,
            edgecolor="none",
            zorder=3,
        )
        ax.add_patch(fancy)

        # Value label above bar
        ax.text(
            xi, bar_height + max_val * 0.02,
            _fmt_brl(val),
            ha="center", va="bottom",
            fontproperties=_montserrat_bold,
            fontsize=10,
            color="#555555",
        )

    # X-axis labels (years)
    ax.set_xticks(x)
    ax.set_xticklabels(
        [str(a) for a in anos],
        fontproperties=_montserrat_bold,
        fontsize=12,
        color="#555555",
    )

    # Clean up axes
    ax.set_xlim(-0.6, len(anos) - 0.4)
    ax.set_ylim(0, max_val * 1.15)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color(COLOR_LIGHT_GRAY)
    ax.tick_params(axis="y", left=False, labelleft=False)
    ax.tick_params(axis="x", bottom=False)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fig.savefig(output_path, dpi=300, transparent=True, bbox_inches="tight", pad_inches=0.3)
    plt.close(fig)
    return output_path


# ---------------------------------------------------------------------------
# 4. Orchestrator
# ---------------------------------------------------------------------------

def generate_all_charts(data: dict, output_dir: str) -> dict:
    """
    Generate all charts and save PNGs to *output_dir*.

    Expected keys in *data*:
        donut   – dict with pct/valor keys for the donut chart
        gauge   – dict with 'lr_pct' and 'lp_pct'
        bars    – list of dicts with 'ano' and 'valor'

    Returns a dict mapping chart name to its file path.
    """
    os.makedirs(output_dir, exist_ok=True)
    result = {}

    # Donut chart
    if "donut" in data:
        path = os.path.join(output_dir, "donut_chart.png")
        generate_donut_chart(data["donut"], path)
        result["donut"] = path

    # Gauge chart
    if "gauge" in data:
        path = os.path.join(output_dir, "gauge_chart.png")
        generate_gauge_chart(data["gauge"]["lr_pct"], data["gauge"]["lp_pct"], path)
        result["gauge"] = path

    # Bar chart
    if "bars" in data:
        path = os.path.join(output_dir, "bar_chart.png")
        generate_bar_chart(data["bars"], path)
        result["bar"] = path

    return result


# ---------------------------------------------------------------------------
# Sample run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sample_data = {
        "donut": {
            "cmv_pct": 64,
            "impostos_pct": 12,
            "folha_pct": 10,
            "despesas_pct": 8,
            "lucro_pct": 6,
            "cmv_valor": 640_000,
            "tributos_valor": 120_000,
            "folha_valor": 100_000,
            "despesas_valor": 80_000,
            "lucro_valor": 60_000,
        },
        "gauge": {
            "lr_pct": 11.3,
            "lp_pct": 16.8,
        },
        "bars": [
            {"ano": 2025, "valor": 120_000},
            {"ano": 2026, "valor": 135_000},
            {"ano": 2027, "valor": 148_000},
            {"ano": 2028, "valor": 162_000},
            {"ano": 2029, "valor": 175_000},
            {"ano": 2030, "valor": 190_000},
            {"ano": 2031, "valor": 205_000},
            {"ano": 2032, "valor": 220_000},
        ],
    }

    out_dir = os.path.join(os.path.dirname(__file__), "output", "charts")
    paths = generate_all_charts(sample_data, out_dir)

    print("Generated charts:")
    for name, path in paths.items():
        print(f"  {name}: {path}")
