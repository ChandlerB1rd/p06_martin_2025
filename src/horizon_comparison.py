"""Compare SVIX forecast performance across 1m/3m/6m/12m horizons."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

from settings import config
from table1 import HORIZONS, load_table1_data

OUTPUT_DIR = Path(config("OUTPUT_DIR"))
OUT = OUTPUT_DIR / "horizon_comparison.csv"
FIG_OUT = OUTPUT_DIR / "horizon_comparison.png"
INITIAL_WINDOW = 1260
REFIT_STEP = 21


def expanding_oos_predictions(sample: pd.DataFrame, y: str, x: str, initial_window: int = INITIAL_WINDOW, refit_step: int = REFIT_STEP) -> pd.DataFrame:
    s = sample[["date", y, x]].dropna().reset_index(drop=True)
    pred = np.full(len(s), np.nan)
    benchmark = np.full(len(s), np.nan)
    for train_end in range(initial_window, len(s), refit_step):
        train = s.iloc[:train_end]
        test_end = min(train_end + refit_step, len(s))
        test = s.iloc[train_end:test_end]
        fit = sm.OLS(train[y], sm.add_constant(train[x], has_constant="add")).fit()
        pred[train_end:test_end] = fit.predict(sm.add_constant(test[x], has_constant="add"))
        benchmark[train_end:test_end] = train[y].mean()
    out = s.copy()
    out["prediction"] = pred
    out["benchmark"] = benchmark
    return out


def compare_horizons(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for h in HORIZONS:
        y, x = f"excess_fwd_{h}", f"svix2_{h}"
        s = df[["date", y, x]].dropna().copy()
        X = sm.add_constant(s[x], has_constant="add")
        fit = sm.OLS(s[y], X).fit()
        fitted = fit.predict(X)
        oos = expanding_oos_predictions(s, y, x).dropna(subset=["prediction", "benchmark"])
        sse_model = np.sum((oos[y] - oos["prediction"]) ** 2)
        sse_benchmark = np.sum((oos[y] - oos["benchmark"]) ** 2)
        oos_r2 = 1.0 - sse_model / sse_benchmark if sse_benchmark > 0 else np.nan
        rows.append(
            {
                "horizon": h,
                "nobs": len(s),
                "in_sample_r2": float(fit.rsquared),
                "rmse": float(np.sqrt(np.mean((s[y] - fitted) ** 2))),
                "mae": float(np.mean(np.abs(s[y] - fitted))),
                "bias": float(np.mean(fitted - s[y])),
                "correlation": float(s[x].corr(s[y])),
                "oos_nobs": len(oos),
                "oos_r2": float(oos_r2),
                "oos_rmse": float(np.sqrt(np.mean((oos[y] - oos["prediction"]) ** 2))) if len(oos) else np.nan,
                "oos_mae": float(np.mean(np.abs(oos[y] - oos["prediction"]))) if len(oos) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def plot_horizon_comparison(result: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7, 4.5))
    x = np.arange(len(result))
    width = 0.36
    ax.bar(x - width / 2, result["in_sample_r2"], width, label="In-sample R²")
    ax.bar(x + width / 2, result["oos_r2"], width, label="OOS R²")
    ax.set_xticks(x, result["horizon"])
    ax.set_ylabel("R²")
    ax.set_xlabel("Forecast horizon")
    ax.set_title("SVIX forecasting performance by horizon")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_OUT, dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    result = compare_horizons(load_table1_data())
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUT, index=False)
    plot_horizon_comparison(result)
    print(result.to_string(index=False))
    print(f"\nSaved horizon comparison -> {OUT}")
    print(f"Saved horizon figure -> {FIG_OUT}")
