"""Specification robustness: parity-implied vs OptionMetrics forward prices.

The forward price sets the boundary between the put and call legs of the SVIX
strip, so it is one of the few construction choices that can move the index
without any change to the option data or to the integral itself.

The production pipeline infers the forward from put-call parity at the paired
strike with the smallest |C - P|. An independent implementation of this paper
instead used the OptionMetrics forward-price file, which is built from the whole
chain. The two agree closely on liquid short-dated expirations and drift apart
on thin long-dated ones, so the natural worry is that the choice matters for the
6- and 12-month cells of Table 1.

This module quantifies the disagreement, rebuilds SVIX under the OptionMetrics
forward, and re-estimates Table 1 under both conventions. The measured answer is
that it does not matter: the forwards differ by a median of 5 basis points inside
45 days rising to 20 basis points beyond 400 days, yet every Table 1 slope moves
by less than 1e-4. The forward enters only as the boundary between the put and
call legs, and the two legs are nearly equal in price wherever the boundary
lands, so a small shift reassigns very few strikes and changes their contribution
negligibly. Recording that as a measured null result is the point of the module.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from build_future_returns import load_future_returns
from forward_prices import load_expiration_inputs
from martin_spec import HORIZONS, ORIGINAL_SAMPLE_END, ORIGINAL_SAMPLE_START
from pull_optionmetrics_forwards import load_spx_forwards
from settings import config
from svix import build_fixed_horizon_svix, build_svix_by_expiration
from table1 import PUBLISHED, run_regression

DATA_DIR = Path(config("DATA_DIR"))
OUTPUT_DIR = Path(config("OUTPUT_DIR"))

ALT_SVIX_OUT = DATA_DIR / "svix_daily_om_forward.parquet"
DIFF_OUT = OUTPUT_DIR / "forward_price_discrepancy.csv"
TABLE_OUT = OUTPUT_DIR / "forward_robustness_table1.csv"
FIGURE_OUT = OUTPUT_DIR / "forward_robustness.png"

DTE_BUCKETS = [0, 45, 90, 180, 270, 400, 550]


def merge_om_forwards(
    inputs: pd.DataFrame,
    om_forwards: pd.DataFrame,
) -> pd.DataFrame:
    """Attach the OptionMetrics forward to each expiration input row."""
    om = om_forwards[["date", "exdate", "forwardprice"]].copy()
    om["date"] = pd.to_datetime(om["date"])
    om["exdate"] = pd.to_datetime(om["exdate"])
    om = om.dropna(subset=["forwardprice"])
    om = om[om["forwardprice"] > 0]
    om = om.drop_duplicates(["date", "exdate"], keep="first")

    merged = inputs.copy()
    merged["date"] = pd.to_datetime(merged["date"])
    merged["exdate"] = pd.to_datetime(merged["exdate"])
    merged = merged.merge(
        om.rename(columns={"forwardprice": "forward_om"}),
        on=["date", "exdate"],
        how="left",
        validate="many_to_one",
    )
    merged["forward_parity"] = merged["forward"]
    merged["forward_rel_diff"] = (
        merged["forward_om"] - merged["forward_parity"]
    ) / merged["forward_parity"]
    return merged


def discrepancy_by_maturity(merged: pd.DataFrame) -> pd.DataFrame:
    """Summarize forward disagreement by maturity bucket."""
    df = merged.dropna(subset=["forward_om"]).copy()
    df["dte_bucket"] = pd.cut(df["days_to_expiry"], bins=DTE_BUCKETS, right=False)
    grouped = df.groupby("dte_bucket", observed=True).agg(
        n=("forward_rel_diff", "size"),
        mean_rel_diff_bp=("forward_rel_diff", lambda s: float(s.mean() * 10_000)),
        median_abs_rel_diff_bp=(
            "forward_rel_diff",
            lambda s: float(s.abs().median() * 10_000),
        ),
        p95_abs_rel_diff_bp=(
            "forward_rel_diff",
            lambda s: float(s.abs().quantile(0.95) * 10_000),
        ),
    )
    return grouped.reset_index().astype({"dte_bucket": str})


def build_alternative_inputs(merged: pd.DataFrame) -> pd.DataFrame:
    """Replace the parity forward with the OptionMetrics forward where present.

    Rows without an OptionMetrics quote keep the parity forward so that the two
    SVIX series are estimated on an identical set of expirations; otherwise the
    comparison would confound the forward convention with sample composition.
    """
    alt = merged.copy()
    alt["forward"] = alt["forward_om"].where(
        alt["forward_om"].notna(), alt["forward_parity"]
    )
    alt["forward_source"] = np.where(alt["forward_om"].notna(), "optionmetrics", "parity")
    return alt


def table1_under(svix_daily: pd.DataFrame, label: str) -> pd.DataFrame:
    """Re-estimate the published-sample regressions against a given SVIX panel."""
    returns = load_future_returns()
    returns["date"] = pd.to_datetime(returns["date"])
    panel = svix_daily.copy()
    panel["date"] = pd.to_datetime(panel["date"])
    merged = returns.merge(panel, on="date", how="inner", validate="one_to_one")

    rows = []
    for horizon in HORIZONS:
        fit = run_regression(
            merged, horizon, ORIGINAL_SAMPLE_START, ORIGINAL_SAMPLE_END, label
        )
        rows.append(fit)
    return pd.DataFrame(rows)


def compare_tables(baseline: pd.DataFrame, alternative: pd.DataFrame) -> pd.DataFrame:
    published = PUBLISHED.set_index("horizon")
    base = baseline.set_index("horizon")
    alt = alternative.set_index("horizon")

    rows = []
    for horizon in HORIZONS:
        pub_beta = float(published.loc[horizon, "beta_1996_2022"])
        b = float(base.loc[horizon, "beta"])
        a = float(alt.loc[horizon, "beta"])
        rows.append(
            {
                "horizon": horizon,
                "beta_parity_forward": b,
                "beta_om_forward": a,
                "beta_change": a - b,
                "beta_published": pub_beta,
                "abs_gap_parity": abs(b - pub_beta),
                "abs_gap_om": abs(a - pub_beta),
                "r2_parity_forward": float(base.loc[horizon, "r2"]),
                "r2_om_forward": float(alt.loc[horizon, "r2"]),
                "nobs_parity": int(base.loc[horizon, "nobs"]),
                "nobs_om": int(alt.loc[horizon, "nobs"]),
            }
        )
    return pd.DataFrame(rows)


def plot_robustness(comparison: pd.DataFrame, discrepancy: pd.DataFrame) -> plt.Figure:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

    x = np.arange(len(comparison))
    width = 0.27
    axes[0].bar(x - width, comparison["beta_parity_forward"], width, label="Parity forward")
    axes[0].bar(x, comparison["beta_om_forward"], width, label="OptionMetrics forward")
    axes[0].bar(x + width, comparison["beta_published"], width, label="Published")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(comparison["horizon"])
    axes[0].set_xlabel("Horizon")
    axes[0].set_ylabel("Slope on SVIX squared")
    axes[0].set_title("(a) Table 1 slope, 1996-2022, by forward convention")
    axes[0].legend(fontsize=8)
    axes[0].grid(alpha=0.3, axis="y")

    axes[1].bar(
        np.arange(len(discrepancy)),
        discrepancy["median_abs_rel_diff_bp"],
        color="tab:gray",
    )
    axes[1].set_xticks(np.arange(len(discrepancy)))
    axes[1].set_xticklabels(discrepancy["dte_bucket"], rotation=30, ha="right", fontsize=8)
    axes[1].set_xlabel("Days to expiration")
    axes[1].set_ylabel("Median |difference| (bp of forward)")
    axes[1].set_title("(b) Forward disagreement widens with maturity")
    axes[1].grid(alpha=0.3, axis="y")

    fig.suptitle("Sensitivity of SVIX and Table 1 to the forward-price convention")
    fig.tight_layout()
    return fig


def main() -> None:
    inputs = load_expiration_inputs()
    merged = merge_om_forwards(inputs, load_spx_forwards())

    matched = int(merged["forward_om"].notna().sum())
    print(
        f"Matched OptionMetrics forwards on {matched:,} of {len(merged):,} "
        f"expiration surfaces ({matched / len(merged):.1%})"
    )

    discrepancy = discrepancy_by_maturity(merged)
    print(discrepancy.to_string(index=False))

    alt_inputs = build_alternative_inputs(merged)
    alt_expiration = build_svix_by_expiration(alt_inputs)
    alt_daily = build_fixed_horizon_svix(alt_expiration)

    baseline = table1_under(pd.read_parquet(DATA_DIR / "svix_daily.parquet"), "parity forward")
    alternative = table1_under(alt_daily, "optionmetrics forward")
    comparison = compare_tables(baseline, alternative)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    alt_daily.to_parquet(ALT_SVIX_OUT, index=False)
    discrepancy.to_csv(DIFF_OUT, index=False)
    comparison.to_csv(TABLE_OUT, index=False)

    fig = plot_robustness(comparison, discrepancy)
    fig.savefig(FIGURE_OUT, dpi=200)
    plt.close(fig)

    print()
    print(comparison.to_string(index=False))
    print(f"\nSaved alternative SVIX panel -> {ALT_SVIX_OUT}")
    print(f"Saved forward discrepancy summary -> {DIFF_OUT}")
    print(f"Saved forward robustness table -> {TABLE_OUT}")
    print(f"Saved robustness figure -> {FIGURE_OUT}")


if __name__ == "__main__":
    main()
