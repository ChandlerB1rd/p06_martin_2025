"""Ex-ante market-regime extension for the SVIX forecasting relation."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

from settings import config
from table1 import HORIZONS, NW_LAGS, load_table1_data

OUTPUT_DIR = Path(config("OUTPUT_DIR"))
OUT = OUTPUT_DIR / "regime_analysis.csv"
FIG_OUT = OUTPUT_DIR / "regime_beta_comparison.png"


def add_regimes(df: pd.DataFrame) -> pd.DataFrame:
    """Create regime labels using only information observable at date t."""
    out = df.sort_values("date").copy()
    out["trail_21d_return"] = (
        (1.0 + out["ret"]).rolling(21, min_periods=21).apply(np.prod, raw=True) - 1.0
    )
    out["trail_21d_vol"] = out["ret"].rolling(21, min_periods=21).std() * np.sqrt(252.0)

    # Expanding cutoffs avoid using future observations to define today's regime.
    vol_cutoff = out["trail_21d_vol"].expanding(252).median()
    svix_cutoff = out["svix2_3m"].expanding(252).median()

    out["market_direction"] = pd.Series(pd.NA, index=out.index, dtype="string")
    valid_ret = out["trail_21d_return"].notna()
    out.loc[valid_ret & (out["trail_21d_return"] >= 0), "market_direction"] = "rising"
    out.loc[valid_ret & (out["trail_21d_return"] < 0), "market_direction"] = "falling"

    out["vol_regime"] = pd.Series(pd.NA, index=out.index, dtype="string")
    valid_vol = out["trail_21d_vol"].notna() & vol_cutoff.notna()
    out.loc[valid_vol & (out["trail_21d_vol"] >= vol_cutoff), "vol_regime"] = "high_vol"
    out.loc[valid_vol & (out["trail_21d_vol"] < vol_cutoff), "vol_regime"] = "low_vol"

    out["svix_regime"] = pd.Series(pd.NA, index=out.index, dtype="string")
    valid_svix = out["svix2_3m"].notna() & svix_cutoff.notna()
    out.loc[valid_svix & (out["svix2_3m"] >= svix_cutoff), "svix_regime"] = "high_svix"
    out.loc[valid_svix & (out["svix2_3m"] < svix_cutoff), "svix_regime"] = "low_svix"
    return out


def regime_regression(df: pd.DataFrame, horizon: str, regime_col: str, regime_value: str) -> dict[str, object]:
    y, x = f"excess_fwd_{horizon}", f"svix2_{horizon}"
    s = df.loc[df[regime_col] == regime_value, [y, x]].dropna()
    if len(s) <= NW_LAGS[horizon] + 5:
        return {
            "horizon": horizon,
            "regime_type": regime_col,
            "regime": regime_value,
            "nobs": len(s),
            "alpha": np.nan,
            "beta": np.nan,
            "beta_t_nw": np.nan,
            "r2": np.nan,
        }
    X = sm.add_constant(s[x], has_constant="add")
    fit = sm.OLS(s[y], X).fit(cov_type="HAC", cov_kwds={"maxlags": NW_LAGS[horizon]})
    return {
        "horizon": horizon,
        "regime_type": regime_col,
        "regime": regime_value,
        "nobs": int(fit.nobs),
        "alpha": float(fit.params["const"]),
        "beta": float(fit.params[x]),
        "beta_t_nw": float(fit.tvalues[x]),
        "r2": float(fit.rsquared),
    }


def run_regime_analysis(df: pd.DataFrame) -> pd.DataFrame:
    d = add_regimes(df)
    rows = []
    for h in HORIZONS:
        for col in ("market_direction", "vol_regime", "svix_regime"):
            for value in sorted(d[col].dropna().unique()):
                rows.append(regime_regression(d, h, col, value))
    return pd.DataFrame(rows)


def plot_regime_betas(result: pd.DataFrame) -> None:
    regime_types = ["market_direction", "vol_regime", "svix_regime"]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), sharey=True)
    for ax, regime_type in zip(axes, regime_types):
        g = result[result["regime_type"] == regime_type].copy()
        regimes = sorted(g["regime"].dropna().unique())
        x = np.arange(len(HORIZONS))
        width = 0.8 / max(len(regimes), 1)
        for j, regime in enumerate(regimes):
            vals = (
                g[g["regime"] == regime]
                .set_index("horizon")
                .reindex(HORIZONS)["beta"]
                .to_numpy(dtype=float)
            )
            ax.bar(x - 0.4 + width / 2 + j * width, vals, width, label=regime)
        ax.axhline(1.0, linewidth=1.0, linestyle="--")
        ax.set_xticks(x, HORIZONS)
        ax.set_title(regime_type.replace("_", " ").title())
        ax.set_xlabel("Horizon")
        ax.legend(fontsize=8)
    axes[0].set_ylabel("SVIX forecasting beta")
    fig.suptitle("SVIX forecasting slope across ex-ante market regimes")
    fig.tight_layout()
    fig.savefig(FIG_OUT, dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    result = run_regime_analysis(load_table1_data())
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUT, index=False)
    plot_regime_betas(result)
    print(result.to_string(index=False))
    print(f"\nSaved regime analysis -> {OUT}")
    print(f"Saved regime figure -> {FIG_OUT}")
