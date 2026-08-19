"""Data-dependent tolerance report for the published Table 1 replication."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from settings import config

OUTPUT_DIR = Path(config("OUTPUT_DIR"))
COMPARISON_IN = OUTPUT_DIR / "table1_published_comparison.csv"
REPORT_OUT = OUTPUT_DIR / "replication_tolerance_report.csv"
SUMMARY_OUT = OUTPUT_DIR / "replication_tolerance_summary.json"

# Diagnostic tolerances. A failure is intentionally reported, not hidden or
# replaced with published values. These thresholds are broad enough to allow
# small data-vintage/discretization differences while still flagging a
# materially different replication.
TOLERANCE = {
    "alpha": 0.01,
    "alpha_se": 0.01,
    "beta": 0.20,
    "beta_se": 0.10,
    "r2": 0.012,
}


def build_tolerance_report(comparison: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in comparison.iterrows():
        for sample in ("1996_2022", "2012_2022"):
            for metric, tolerance in TOLERANCE.items():
                diff_col = f"{metric}_abs_diff_{sample}"
                diff = float(r[diff_col])
                rows.append(
                    {
                        "horizon": r["horizon"],
                        "sample": sample,
                        "metric": metric,
                        "absolute_difference": diff,
                        "tolerance": tolerance,
                        # A pass says only that the deviation fits inside the
                        # band. Reporting how much of the band it consumes
                        # distinguishes an exact match from a near miss.
                        "tolerance_utilization": diff / tolerance,
                        "within_tolerance": diff <= tolerance,
                    }
                )
    return pd.DataFrame(rows)


def summarize(report: pd.DataFrame) -> dict[str, object]:
    worst = report.sort_values("tolerance_utilization", ascending=False).iloc[0]
    return {
        "checks": int(len(report)),
        "passed": int(report["within_tolerance"].sum()),
        "failed": int((~report["within_tolerance"]).sum()),
        "all_within_tolerance": bool(report["within_tolerance"].all()),
        "max_tolerance_utilization": round(float(worst["tolerance_utilization"]), 4),
        "tightest_check": (
            f"{worst['horizon']} {worst['sample']} {worst['metric']}"
        ),
        "checks_above_half_tolerance": int(
            (report["tolerance_utilization"] > 0.5).sum()
        ),
        "note": "Failures are investigation flags; generated results are never replaced by published values.",
    }


if __name__ == "__main__":
    comparison = pd.read_csv(COMPARISON_IN)
    report = build_tolerance_report(comparison)
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(REPORT_OUT, index=False)
    summary = summarize(report)
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2) + "\n")
    print(report.to_string(index=False))
    print(json.dumps(summary, indent=2))
