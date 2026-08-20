"""Plot the fixed-horizon SVIX series as report-ready pipeline figures.

The first output compares the full sample with the Martin (2017) validation
window through January 2012. The second output shows the four fixed-horizon
SVIX series over the full sample in the same units used by the analysis.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from martin_spec import HORIZONS
from settings import config
from svix import load_svix_daily

OUTPUT_DIR = Path(config("OUTPUT_DIR"))
SERIES_OUT = OUTPUT_DIR / "svix_series.png"
TERM_STRUCTURE_OUT = OUTPUT_DIR / "svix_term_structure.png"

MARTIN_2017_END = "2012-01-31"
HORIZON_LABELS = {
    "1m": "1 month",
    "3m": "3 months",
    "6m": "6 months",
    "12m": "12 months",
}


def _draw_panel(ax, frame: pd.DataFrame, title: str) -> None:
    """Draw one SVIX comparison panel in percentage units."""
    for horizon in HORIZONS:
        column = f"svix_{horizon}"
        if column not in frame.columns:
            continue
        ax.plot(
            frame["date"],
            frame[column] * 100.0,
            linewidth=0.7,
            label=HORIZON_LABELS.get(horizon, horizon),
        )
    ax.set_title(title)
    ax.set_xlabel("Year")
    ax.set_ylabel("Annualized SVIX (%)")
    ax.grid(alpha=0.3)
    ax.legend(title="Horizon", fontsize=8)


def plot_svix_series(svix: pd.DataFrame) -> plt.Figure:
    """Plot the full sample beside the Martin (2017) validation window."""
    df = svix.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    early = df.loc[df["date"] <= pd.Timestamp(MARTIN_2017_END)]

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    _draw_panel(axes[0], df, "(a) Full sample")
    _draw_panel(
        axes[1],
        early,
        "(b) Martin (2017) window, through January 2012",
    )
    fig.suptitle("SVIX index at fixed horizons (Martin 2025)")
    fig.tight_layout()
    return fig


def plot_svix_term_structure(svix: pd.DataFrame) -> plt.Figure:
    """Plot all fixed-horizon SVIX series over the full sample."""
    df = svix.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    fig, ax = plt.subplots(figsize=(11, 5))
    for horizon in HORIZONS:
        column = f"svix_{horizon}"
        if column not in df.columns:
            continue
        ax.plot(df["date"], df[column], label=column)

    ax.set_title("SVIX fixed-horizon term structure")
    ax.set_xlabel("date")
    ax.set_ylabel("Annualized SVIX")
    ax.legend()
    fig.tight_layout()
    return fig


def main() -> tuple[Path, Path]:
    """Generate both report-ready SVIX figures from the cleaned daily series."""
    svix = load_svix_daily()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    series_fig = plot_svix_series(svix)
    series_fig.savefig(SERIES_OUT, dpi=200)
    plt.close(series_fig)

    term_fig = plot_svix_term_structure(svix)
    term_fig.savefig(TERM_STRUCTURE_OUT, dpi=200)
    plt.close(term_fig)

    print(f"Saved SVIX series figure -> {SERIES_OUT}")
    print(f"Saved SVIX term-structure figure -> {TERM_STRUCTURE_OUT}")
    return SERIES_OUT, TERM_STRUCTURE_OUT


if __name__ == "__main__":
    main()