"""Plot the fixed-horizon SVIX series as a pipeline figure.

The project brief asks for the SVIX index to be plotted and compared against
Martin (2017). The notebook already shows the term structure interactively; this
module writes a reviewable figure target so the deliverable does not depend on
executing a notebook.

The left panel shows the full sample. The right panel repeats the series over the
Martin (2017) window, which ends in January 2012, so the levels and the shape of
the 2008 spike can be checked against the published figure directly.
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
OUT = OUTPUT_DIR / "svix_series.png"

MARTIN_2017_END = "2012-01-31"
HORIZON_LABELS = {"1m": "1 month", "3m": "3 months", "6m": "6 months", "12m": "12 months"}


def _draw_panel(ax, frame: pd.DataFrame, title: str) -> None:
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
    df = svix.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    early = df.loc[df["date"] <= pd.Timestamp(MARTIN_2017_END)]

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    _draw_panel(axes[0], df, "(a) Full sample")
    _draw_panel(axes[1], early, "(b) Martin (2017) window, through January 2012")
    fig.suptitle("SVIX index at fixed horizons (Martin 2025)")
    fig.tight_layout()
    return fig


def main() -> Path:
    fig = plot_svix_series(load_svix_daily())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=200)
    plt.close(fig)
    print(f"Saved SVIX series figure -> {OUT}")
    return OUT


if __name__ == "__main__":
    main()
