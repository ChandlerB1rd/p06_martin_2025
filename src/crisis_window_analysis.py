"""Measure how far the Table 1 slopes depend on the 2008-2009 crisis.

Martin (2025) footnote 13 singles out the October 2008 - March 2009 window,
where SVIX reached its sample maximum while the market kept falling into March.
At the 6- and 12-month horizons a few hundred overlapping crisis observations
carry a large share of the identification, so two implementations that differ
only in how they price the deep wings during that window can report visibly
different slopes.

This module quantifies that dependence two ways: by dropping the crisis window
outright, and by dropping each calendar year in turn so the crisis years can be
compared against a baseline of ordinary years rather than asserted to matter.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from martin_spec import HORIZONS, ORIGINAL_SAMPLE_END, ORIGINAL_SAMPLE_START
from settings import config
from table1 import PUBLISHED, load_table1_data, run_regression

OUTPUT_DIR = Path(config("OUTPUT_DIR"))
CRISIS_OUT = OUTPUT_DIR / "crisis_window_analysis.csv"
LEAVE_OUT = OUTPUT_DIR / "crisis_leave_one_year_out.csv"
FIGURE_OUT = OUTPUT_DIR / "crisis_leave_one_year_out.png"

CRISIS_START = "2008-10-01"
CRISIS_END = "2009-03-31"


def _drop_window(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    mask = df["date"].between(pd.Timestamp(start), pd.Timestamp(end))
    return df.loc[~mask].copy()


def crisis_sensitivity(df: pd.DataFrame) -> pd.DataFrame:
    """Compare full-sample slopes against slopes with the crisis removed."""
    without_crisis = _drop_window(df, CRISIS_START, CRISIS_END)
    published = PUBLISHED.set_index("horizon")

    rows = []
    for horizon in HORIZONS:
        base = run_regression(
            df, horizon, ORIGINAL_SAMPLE_START, ORIGINAL_SAMPLE_END, "full"
        )
        excl = run_regression(
            without_crisis,
            horizon,
            ORIGINAL_SAMPLE_START,
            ORIGINAL_SAMPLE_END,
            "ex-crisis",
        )
        pub_beta = float(published.loc[horizon, "beta_1996_2022"])
        rows.append(
            {
                "horizon": horizon,
                "beta_full": base["beta"],
                "beta_ex_crisis": excl["beta"],
                "beta_change": excl["beta"] - base["beta"],
                "beta_published": pub_beta,
                "abs_gap_full": abs(base["beta"] - pub_beta),
                "abs_gap_ex_crisis": abs(excl["beta"] - pub_beta),
                "r2_full": base["r2"],
                "r2_ex_crisis": excl["r2"],
                "nobs_full": base["nobs"],
                "nobs_ex_crisis": excl["nobs"],
                "crisis_obs_dropped": base["nobs"] - excl["nobs"],
            }
        )
    return pd.DataFrame(rows)


def leave_one_year_out(df: pd.DataFrame) -> pd.DataFrame:
    """Re-estimate the published sample with each calendar year removed."""
    sample = df.loc[
        df["date"].between(
            pd.Timestamp(ORIGINAL_SAMPLE_START), pd.Timestamp(ORIGINAL_SAMPLE_END)
        )
    ]
    years = sorted(sample["date"].dt.year.unique())

    rows = []
    for horizon in HORIZONS:
        base = run_regression(
            df, horizon, ORIGINAL_SAMPLE_START, ORIGINAL_SAMPLE_END, "full"
        )
        for year in years:
            reduced = df.loc[df["date"].dt.year != year]
            fit = run_regression(
                reduced,
                horizon,
                ORIGINAL_SAMPLE_START,
                ORIGINAL_SAMPLE_END,
                f"ex-{year}",
            )
            rows.append(
                {
                    "horizon": horizon,
                    "excluded_year": int(year),
                    "beta": fit["beta"],
                    "beta_full": base["beta"],
                    "beta_change": fit["beta"] - base["beta"],
                    "nobs": fit["nobs"],
                }
            )
    return pd.DataFrame(rows)


def plot_leave_one_year_out(leave_out: pd.DataFrame) -> plt.Figure:
    fig, axes = plt.subplots(2, 2, figsize=(12, 7), sharex=True)
    for ax, horizon in zip(axes.ravel(), HORIZONS):
        sub = leave_out[leave_out["horizon"] == horizon].sort_values("excluded_year")
        ax.bar(sub["excluded_year"], sub["beta_change"], color="tab:blue")
        ax.axhline(0.0, color="black", linewidth=0.8)
        ax.set_title(f"{horizon} horizon")
        ax.set_ylabel("Change in beta")
        ax.grid(alpha=0.3, axis="y")
    for ax in axes[1]:
        ax.set_xlabel("Excluded calendar year")
    fig.suptitle(
        "Leverage of individual years on the 1996-2022 SVIX slope "
        "(change in beta when the year is dropped)"
    )
    fig.tight_layout()
    return fig


def main() -> None:
    data = load_table1_data()
    crisis = crisis_sensitivity(data)
    leave_out = leave_one_year_out(data)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    crisis.to_csv(CRISIS_OUT, index=False)
    leave_out.to_csv(LEAVE_OUT, index=False)

    fig = plot_leave_one_year_out(leave_out)
    fig.savefig(FIGURE_OUT, dpi=200)
    plt.close(fig)

    print(crisis.to_string(index=False))
    print(f"\nSaved crisis sensitivity -> {CRISIS_OUT}")
    print(f"Saved leave-one-year-out results -> {LEAVE_OUT}")
    print(f"Saved leave-one-year-out figure -> {FIGURE_OUT}")


if __name__ == "__main__":
    main()
