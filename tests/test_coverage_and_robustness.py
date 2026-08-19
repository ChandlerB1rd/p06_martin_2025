"""Tests for the data-coverage guard and the specification-robustness layer."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from build_future_returns import check_return_coverage
from crisis_window_analysis import CRISIS_END, CRISIS_START, _drop_window
from forward_robustness import build_alternative_inputs, merge_om_forwards
from replication_validation import build_tolerance_report, summarize
from svix_summary_stats import summarize_svix


def _curve(last_date: str) -> pd.DataFrame:
    return pd.DataFrame({"date": pd.to_datetime(["1996-01-02", last_date])})


def _returns(last_date: str) -> pd.DataFrame:
    return pd.DataFrame({"date": pd.to_datetime(["1996-01-02", last_date])})


def test_return_coverage_allows_normal_publication_lag():
    # CRSP trails OptionMetrics by weeks in ordinary operation; that must pass.
    lag = check_return_coverage(_returns("2025-07-31"), _curve("2025-08-29"))
    assert lag == 29


def test_return_coverage_rejects_a_frozen_return_file():
    # The legacy crsp.dsp500 file stops at the end of 2024 while the option
    # data continues, which silently truncates the update sample.
    with pytest.raises(RuntimeError, match="frozen CRSP index file"):
        check_return_coverage(_returns("2024-12-31"), _curve("2025-08-29"))


def test_return_coverage_threshold_is_overridable():
    assert check_return_coverage(
        _returns("2024-12-31"), _curve("2025-08-29"), max_lag_days=400
    ) == 241


def test_crisis_window_drops_only_the_named_months():
    dates = pd.date_range("2008-01-01", "2009-12-31", freq="D")
    df = pd.DataFrame({"date": dates})
    trimmed = _drop_window(df, CRISIS_START, CRISIS_END)

    removed = set(dates) - set(trimmed["date"])
    assert min(removed) == pd.Timestamp(CRISIS_START)
    assert max(removed) == pd.Timestamp(CRISIS_END)
    assert pd.Timestamp("2008-09-30") in set(trimmed["date"])
    assert pd.Timestamp("2009-04-01") in set(trimmed["date"])


def test_alternative_forward_falls_back_to_parity_when_unmatched():
    # Both series must be estimated on the same expirations, otherwise the
    # comparison confounds the forward convention with sample composition.
    inputs = pd.DataFrame(
        {
            "date": pd.to_datetime(["2010-01-04", "2010-01-04"]),
            "exdate": pd.to_datetime(["2010-02-19", "2010-03-19"]),
            "days_to_expiry": [46, 74],
            "forward": [1140.0, 1145.0],
        }
    )
    om = pd.DataFrame(
        {
            "date": pd.to_datetime(["2010-01-04"]),
            "exdate": pd.to_datetime(["2010-02-19"]),
            "forwardprice": [1141.0],
        }
    )

    merged = merge_om_forwards(inputs, om)
    alternative = build_alternative_inputs(merged)

    assert alternative.loc[0, "forward"] == pytest.approx(1141.0)
    assert alternative.loc[0, "forward_source"] == "optionmetrics"
    assert alternative.loc[1, "forward"] == pytest.approx(1145.0)
    assert alternative.loc[1, "forward_source"] == "parity"
    assert len(alternative) == len(inputs)


def test_summary_statistics_report_both_svix_and_svix_squared():
    dates = pd.date_range("2005-01-03", periods=40, freq="B")
    panel = {"date": dates}
    for horizon in ("1m", "3m", "6m", "12m"):
        vol = np.linspace(0.15, 0.25, len(dates))
        panel[f"svix_{horizon}"] = vol
        panel[f"svix2_{horizon}"] = vol**2

    stats = summarize_svix(pd.DataFrame(panel))

    assert set(stats["measure"]) == {"svix", "svix2"}
    # Statistics are reported in percentage points, not decimals.
    vol_mean = stats.loc[
        (stats["measure"] == "svix") & (stats["horizon"] == "1m"), "mean"
    ].iloc[0]
    assert vol_mean == pytest.approx(20.0, abs=0.5)


def test_tolerance_report_exposes_how_much_of_the_band_is_used():
    comparison = pd.DataFrame(
        [
            {
                "horizon": "12m",
                **{
                    f"{metric}_abs_diff_{sample}": value
                    for sample in ("1996_2022", "2012_2022")
                    for metric, value in (
                        ("alpha", 0.001),
                        ("alpha_se", 0.001),
                        ("beta", 0.18),
                        ("beta_se", 0.01),
                        ("r2", 0.001),
                    )
                },
            }
        ]
    )
    report = build_tolerance_report(comparison)
    summary = summarize(report)

    beta_row = report[report["metric"] == "beta"].iloc[0]
    assert beta_row["within_tolerance"]
    # A pass at 90% of the band is very different from an exact match, and the
    # summary has to say so.
    assert beta_row["tolerance_utilization"] == pytest.approx(0.9)
    assert summary["max_tolerance_utilization"] == pytest.approx(0.9)
    assert summary["tightest_check"].endswith("beta")
