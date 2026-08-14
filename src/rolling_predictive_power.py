"""Rolling predictive-power extension for SVIX."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import statsmodels.api as sm

from settings import config
from table1 import HORIZONS, NW_LAGS, load_table1_data

OUTPUT_DIR = Path(config("OUTPUT_DIR"))
OUT = OUTPUT_DIR / "rolling_predictive_power.csv"
FIG_OUT = OUTPUT_DIR / "rolling_predictive_beta.png"
ROLLING_WINDOW = 1260
STEP = 21


def rolling_regressions(df: pd.DataFrame, window: int = ROLLING_WINDOW, step: int = STEP) -> pd.DataFrame:
    rows = []
    for h in HORIZONS:
        y, x = f"excess_fwd_{h}", f"svix2_{h}"
        sample = df[["date", y, x]].dropna().reset_index(drop=True)
        for end_idx in range(window, len(sample) + 1, step):
            w = sample.iloc[end_idx - window : end_idx]
            X = sm.add_constant(w[x], has_constant="add")
            fit = sm.OLS(w[y], X).fit(cov_type="HAC", cov_kwds={"maxlags": NW_LAGS[h]})
            rows.append(
                {
                    "date": w["date"].iloc[-1],
                    "horizon": h,
                    "window_obs": len(w),
                    "alpha": float(fit.params["const"]),
                    "beta": float(fit.params[x]),
                    "beta_t_nw": float(fit.tvalues[x]),
                    "r2": float(fit.rsquared),
                }
            )
    return pd.DataFrame(rows)


def plot_rolling_beta(result: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(11, 5))
    for h in HORIZONS:
        g = result[result["horizon"] == h]
        ax.plot(g["date"], g["beta"], label=h)
    ax.axhline(1.0, linewidth=1.0, linestyle="--")
    ax.set_ylabel("Rolling beta")
    ax.set_xlabel("Window end date")
    ax.set_title("Five-year rolling SVIX forecasting slope")
    ax.legend(title="Horizon")
    fig.tight_layout()
    fig.savefig(FIG_OUT, dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    result = rolling_regressions(load_table1_data())
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUT, index=False)
    plot_rolling_beta(result)
    print(f"Saved rolling results -> {OUT}")
    print(f"Saved rolling beta figure -> {FIG_OUT}")
