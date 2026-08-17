"""Summary statistics for the fixed-horizon SVIX series.

The project brief asks for the SVIX index to be plotted *and* described, so this
module produces the numeric half of that deliverable.

Both measures are reported in annualized percentage points. ``svix`` is the
volatility-units series that Martin plots, and ``svix2`` is the variance that
enters Table 1 as the regressor; reporting only one of the two invites unit
confusion when the numbers are compared against another implementation.

Two samples are reported. The full sample covers everything the pipeline builds.
The ``martin2017`` sample stops at January 2012, matching the window of the
earlier paper, so the levels can be compared against a published reference
rather than only against themselves.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from martin_spec import HORIZONS
from settings import config
from svix import load_svix_daily

OUTPUT_DIR = Path(config("OUTPUT_DIR"))
OUT = OUTPUT_DIR / "svix_summary_stats.csv"

MARTIN_2017_END = "2012-01-31"
PERCENTILES = (0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99)


def _describe(series: pd.Series, dates: pd.Series) -> dict[str, float | int | str]:
    stats: dict[str, float | int | str] = {
        "mean": float(series.mean()),
        "std": float(series.std(ddof=1)),
    }
    for q in PERCENTILES:
        stats[f"p{int(round(q * 100))}"] = float(series.quantile(q))
    stats["min"] = float(series.min())
    stats["max"] = float(series.max())
    stats["n"] = int(series.size)
    stats["start"] = str(pd.Timestamp(dates.min()).date())
    stats["end"] = str(pd.Timestamp(dates.max()).date())
    return stats


def summarize_svix(svix: pd.DataFrame) -> pd.DataFrame:
    """Return annualized SVIX statistics in percent, by sample, measure, horizon."""
    df = svix.copy()
    df["date"] = pd.to_datetime(df["date"])

    samples = {
        "full": df,
        "martin2017": df.loc[df["date"] <= pd.Timestamp(MARTIN_2017_END)],
    }
    measures = {"svix": "svix_{h}", "svix2": "svix2_{h}"}

    rows = []
    for sample_name, frame in samples.items():
        if frame.empty:
            continue
        for measure, template in measures.items():
            for horizon in HORIZONS:
                column = template.format(h=horizon)
                if column not in frame.columns:
                    raise KeyError(f"{column} missing from the daily SVIX panel.")
                usable = frame.loc[frame[column].notna(), ["date", column]]
                if usable.empty:
                    continue
                rows.append(
                    {
                        "sample": sample_name,
                        "measure": measure,
                        "horizon": horizon,
                        **_describe(usable[column] * 100.0, usable["date"]),
                    }
                )

    return pd.DataFrame(rows)


def main() -> pd.DataFrame:
    stats = summarize_svix(load_svix_daily())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    stats.to_csv(OUT, index=False)
    print(stats.to_string(index=False))
    print(f"Saved {len(stats)} summary rows -> {OUT}")
    return stats


if __name__ == "__main__":
    main()
