"""Replicate Martin (2025) Figures 1 and 2 using Equations (48) and (49)."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from clean_optionmetrics import iter_clean_options
from forward_prices import load_expiration_inputs
from martin_spec import HORIZON_DAYS
from option_surface import option_sum
from settings import config
from svix import interpolate_fixed_maturity

DATA_DIR = Path(config("DATA_DIR"))
OUTPUT_DIR = Path(config("OUTPUT_DIR"))
BY_EXPIRATION_OUT = DATA_DIR / "power_utility_by_expiration.parquet"
DAILY_OUT = DATA_DIR / "power_utility_daily.parquet"

REPLICATION_END = pd.Timestamp("2022-12-30")

FIGURE1_REPLICATION_OUT = OUTPUT_DIR / "figure1_power_utility_replication.png"
FIGURE2_REPLICATION_OUT = OUTPUT_DIR / "figure2_power_utility_replication.png"
FIGURE1_UPDATED_OUT = OUTPUT_DIR / "figure1_power_utility_updated.png"
FIGURE2_UPDATED_OUT = OUTPUT_DIR / "figure2_power_utility_updated.png"

GAMMAS = (1, 2, 3)


def risk_neutral_moment(
    options: pd.DataFrame,
    theta: int,
    rf_gross: float,
    spot: float,
) -> float:
    """Evaluate Equation (49) for integer theta >= 1.

    The printed equation in Martin (2025) splits the option integrals at
    S_t R_f,t+1.  We implement that expression literally.  The article notes
    that it abstracts from the distinction between price and total returns,
    i.e. from dividends, over these horizons.
    """
    if theta < 1:
        raise ValueError("theta must be at least 1")
    if theta == 1:
        return float(rf_gross)
    if rf_gross <= 0 or spot <= 0:
        return np.nan

    boundary = spot * rf_gross
    sums = option_sum(options, boundary=boundary, strike_power=theta - 2)
    total = float(sums["total_sum"])
    if not np.isfinite(total):
        return np.nan

    adjustment = (
        rf_gross
        * theta
        * (theta - 1)
        / (spot**theta)
        * total
    )
    return float(rf_gross**theta + adjustment)


def premium_for_gamma(
    options: pd.DataFrame,
    gamma: int,
    rf_gross: float,
    spot: float,
) -> dict[str, float]:
    """Return the power-utility equity premium implied by Equations 48-49."""
    m1 = risk_neutral_moment(options, 1, rf_gross, spot)
    mg = risk_neutral_moment(options, gamma, rf_gross, spot)
    m1g = risk_neutral_moment(options, 1 + gamma, rf_gross, spot)
    if not all(np.isfinite(v) and v > 0 for v in (m1, mg, m1g)):
        return {"moment_gamma": np.nan, "moment_1pgamma": np.nan, "premium": np.nan}

    # Eq. 48 is a LOG equity premium.  The paper's discrete-time analogue
    # of mu-r_f is log(E[R] / R_f), so Figure 1/2 must use the logarithm
    # of the risk-neutral moment ratio, not the arithmetic excess return.
    expected_return_ratio = m1g / (m1 * mg)
    if not np.isfinite(expected_return_ratio) or expected_return_ratio <= 0:
        return {"moment_gamma": np.nan, "moment_1pgamma": np.nan, "premium": np.nan}
    premium = np.log(expected_return_ratio)
    return {
        "moment_gamma": float(mg),
        "moment_1pgamma": float(m1g),
        "premium": float(premium),
    }


def build_by_expiration() -> pd.DataFrame:
    inputs = load_expiration_inputs()
    rows = []

    for meta, options in iter_clean_options():
        start = pd.Timestamp(meta.start_date)
        end = pd.Timestamp(meta.end_date)
        inp = inputs[(inputs["date"] >= start) & (inputs["date"] <= end)].copy()
        if inp.empty:
            continue
        keep = inp[
            ["date", "exdate", "surface_key", "days_to_expiry", "spot", "rf_gross"]
        ]
        merged = options.merge(
            keep,
            on=["date", "exdate", "surface_key"],
            how="inner",
            suffixes=("", "_input"),
        )
        print(f"[power utility] {meta.start_date} to {meta.end_date}: {len(merged):,} quotes")

        for (dt, exdate, surface_key), g in merged.groupby(
            ["date", "exdate", "surface_key"], sort=False
        ):
            dte = int(g["days_to_expiry_input"].iloc[0] if "days_to_expiry_input" in g else g["days_to_expiry"].iloc[0])
            spot = float(g["spot_input"].iloc[0] if "spot_input" in g else g["spot"].iloc[0])
            rf = float(g["rf_gross"].iloc[0])
            row: dict[str, object] = {
                "date": dt,
                "exdate": exdate,
                "surface_key": surface_key,
                "days_to_expiry": dte,
                "spot": spot,
                "rf_gross": rf,
                "eq49_boundary": spot * rf,
            }
            for gamma in GAMMAS:
                result = premium_for_gamma(g, gamma, rf, spot)
                row[f"moment_g{gamma}"] = result["moment_gamma"]
                row[f"moment_g{gamma + 1}"] = result["moment_1pgamma"]
                row[f"premium_g{gamma}"] = result["premium"]
            rows.append(row)

    out = pd.DataFrame(rows)
    if out.empty:
        raise RuntimeError("Power-utility calculation produced no expiration rows.")
    return out.sort_values(["date", "days_to_expiry", "exdate"]).reset_index(drop=True)


def build_fixed_horizon_premia(by_expiration: pd.DataFrame) -> pd.DataFrame:
    """Interpolate the 1-month and 1-year premia used in Figures 1 and 2."""
    rows = []
    for dt, g in by_expiration.groupby("date", sort=True):
        row: dict[str, object] = {"date": dt}
        for label in ("1m", "12m"):
            target = HORIZON_DAYS[label]
            row[f"target_days_{label}"] = target
            for gamma in GAMMAS:
                value, left, right, extrap = interpolate_fixed_maturity(
                    g, target, f"premium_g{gamma}"
                )
                row[f"premium_{label}_g{gamma}"] = value
                row[f"source_dte_left_{label}_g{gamma}"] = left
                row[f"source_dte_right_{label}_g{gamma}"] = right
                row[f"extrapolated_{label}_g{gamma}"] = extrap
        rows.append(row)

    out = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    for gamma in GAMMAS:
        # Martin (2025), Figure 1: multiply the 1-month premium by 12.
        out[f"premium_1m_ann_g{gamma}"] = 12.0 * out[f"premium_1m_g{gamma}"]
        out[f"ratio_1m_g{gamma}"] = out[f"premium_1m_g{gamma}"] / out["premium_1m_g1"]
        out[f"ratio_12m_g{gamma}"] = out[f"premium_12m_g{gamma}"] / out["premium_12m_g1"]
    return out


def plot_figure1(df: pd.DataFrame, output_path: Path) -> None:
    """Plot Martin Figure 1 for the supplied sample."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for gamma in GAMMAS:
        axes[0].plot(
            df["date"],
            100.0 * df[f"premium_1m_ann_g{gamma}"],
            label=fr"$\gamma={gamma}$",
        )
    axes[0].set_ylabel("Annualized 1-month equity premium (%)")
    axes[0].set_xlabel("Year")
    axes[0].legend()

    for gamma in (2, 3):
        axes[1].plot(
            df["date"],
            df[f"ratio_1m_g{gamma}"],
            label=fr"$\gamma={gamma}$",
        )
    axes[1].set_ylabel("Ratio to log-investor equity premium")
    axes[1].set_xlabel("Year")
    axes[1].legend()

    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def plot_figure2(df: pd.DataFrame, output_path: Path) -> None:
    """Plot Martin Figure 2 for the supplied sample."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for gamma in GAMMAS:
        axes[0].plot(
            df["date"],
            100.0 * df[f"premium_12m_g{gamma}"],
            label=fr"$\gamma={gamma}$",
        )
    axes[0].set_ylabel("1-year equity premium (%)")
    axes[0].set_xlabel("Year")
    axes[0].legend()

    for gamma in (2, 3):
        axes[1].plot(
            df["date"],
            df[f"ratio_12m_g{gamma}"],
            label=fr"$\gamma={gamma}$",
        )
    axes[1].set_ylabel("Ratio to log-investor equity premium")
    axes[1].set_xlabel("Year")
    axes[1].legend()

    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def write_power_utility_figures(daily: pd.DataFrame) -> None:
    """Write strict replication figures and full-sample updated figures."""
    dates = pd.to_datetime(daily["date"])
    replication = daily.loc[dates <= REPLICATION_END].copy()
    if replication.empty:
        raise RuntimeError(
            f"No power-utility observations available through {REPLICATION_END.date()}."
        )

    plot_figure1(replication, FIGURE1_REPLICATION_OUT)
    plot_figure2(replication, FIGURE2_REPLICATION_OUT)
    plot_figure1(daily, FIGURE1_UPDATED_OUT)
    plot_figure2(daily, FIGURE2_UPDATED_OUT)


if __name__ == "__main__":
    by_exp = build_by_expiration()
    daily = build_fixed_horizon_premia(by_exp)

    BY_EXPIRATION_OUT.parent.mkdir(parents=True, exist_ok=True)
    by_exp.to_parquet(BY_EXPIRATION_OUT, index=False)
    daily.to_parquet(DAILY_OUT, index=False)

    write_power_utility_figures(daily)

    print(f"Saved expiration-level power-utility data -> {BY_EXPIRATION_OUT}")
    print(f"Saved fixed-horizon power-utility data -> {DAILY_OUT}")
    print(
        "Saved replication Figures 1-2 "
        f"through {REPLICATION_END.date()} -> "
        f"{FIGURE1_REPLICATION_OUT}, {FIGURE2_REPLICATION_OUT}"
    )
    print(
        "Saved updated Figures 1-2 through "
        f"{pd.to_datetime(daily['date']).max().date()} -> "
        f"{FIGURE1_UPDATED_OUT}, {FIGURE2_UPDATED_OUT}"
    )