"""Motivated unit tests for the Martin (2025) replication pipeline."""

from __future__ import annotations

import numpy as np
import pandas as pd

from build_future_returns import future_return_to_day_target
from forward_prices import estimate_forward
from martin_spec import ANNUALIZATION_FACTOR, HORIZON_DAYS, NW_LAGS
from option_surface import (
    add_surface_key,
    delta_k_weights,
    lower_mid_surface,
    option_sum,
    quarterly_mask,
)
from power_utility import premium_for_gamma
from svix import compute_svix_for_expiration, interpolate_fixed_maturity


def test_forward_uses_call_put_crossing():
    q = pd.DataFrame(
        {
            "strike": [100.0, 100.0, 105.0, 105.0],
            "cp_flag": ["C", "P", "C", "P"],
            "mid": [5.0, 3.0, 2.0, 5.0],
        }
    )
    forward, gap, n_pairs, method = estimate_forward(q, rf_gross=1.01)
    assert n_pairs == 2
    assert method == "cp_crossing"
    assert np.isclose(forward, 102.0)
    assert np.isclose(gap, 2.0)


def test_surface_key_distinguishes_am_and_pm_contracts():
    q = pd.DataFrame(
        {
            "am_settlement": [0.0, 1.0],
            "ss_flag": [0, 0],
            "contract_size": [100, 100],
        }
    )
    out = add_surface_key(q)
    assert out["surface_key"].nunique() == 2


def test_delta_k_matches_cboe_weights():
    strikes = np.array([80.0, 90.0, 110.0, 120.0])
    assert np.allclose(delta_k_weights(strikes), [10.0, 15.0, 15.0, 10.0])


def test_lower_mid_then_zero_bid_ordering():
    q = pd.DataFrame(
        {
            "strike": [80, 80, 90, 90, 110, 110, 120, 120],
            "cp_flag": ["P", "C", "P", "C", "C", "P", "C", "P"],
            "mid": [2, 22, 1, 20, 1, 20, 2, 22],
            "best_bid": [1, 21, 0, 19, 0, 19, 1, 21],
        }
    )
    surface = lower_mid_surface(q, boundary=100.0)
    # At K=90 and K=110 the lower-mid OTM quote has zero bid, so Martin's
    # ordering deletes the strike rather than substituting the ITM option.
    assert surface["strike"].tolist() == [80.0, 120.0]


def test_quarterly_identifier_is_removed_without_deleting_other_series():
    q = pd.DataFrame(
        {
            "root": ["SPXQ", "SPXW", "SPX"],
            "expiry_indicator": [None, None, None],
            "suffix": [None, None, None],
        }
    )
    assert quarterly_mask(q).tolist() == [True, False, False]


def test_svix_equation_19_is_positive_and_annualizes():
    q = pd.DataFrame(
        {
            "strike": [80, 90, 110, 120],
            "cp_flag": ["P", "P", "C", "C"],
            "mid": [1.0, 2.0, 2.0, 1.0],
            "best_bid": [0.9, 1.9, 1.9, 0.9],
        }
    )
    out = compute_svix_for_expiration(
        q,
        forward=100.0,
        rf_gross=1.01,
        spot=100.0,
        annualization_factor=12.0,
    )
    assert out["svix2_total"] > 0
    assert np.isclose(out["svix2"], 12.0 * out["svix2_total"])
    assert np.isclose(out["svix"], np.sqrt(out["svix2"]))


def test_fixed_maturity_interpolation_and_extrapolation():
    g = pd.DataFrame(
        {
            "days_to_expiry": [20, 40, 60],
            "value": [0.10, 0.30, 0.50],
        }
    )
    value, left, right, extrap = interpolate_fixed_maturity(g, 30, "value")
    assert np.isclose(value, 0.20)
    assert (left, right, extrap) == (20.0, 40.0, False)

    value2, left2, right2, extrap2 = interpolate_fixed_maturity(g, 10, "value")
    assert np.isclose(value2, 0.0)
    assert (left2, right2, extrap2) == (20.0, 40.0, True)


def test_future_return_uses_fixed_days_and_excludes_predictor_date():
    dates = pd.bdate_range("2025-01-02", periods=40)
    df = pd.DataFrame({"date": dates, "ret": 0.0})
    df.loc[0, "ret"] = 0.50  # predictor-date return: must be excluded
    df.loc[1, "ret"] = 0.10
    values, targets = future_return_to_day_target(df, target_days=30)
    assert values.iloc[0] < 0.50
    assert np.isclose(values.iloc[0], 0.10)
    assert pd.notna(targets.iloc[0])


def test_equation_48_gamma1_matches_log_investor_premium_under_eq49():
    q = pd.DataFrame(
        {
            "strike": [80, 90, 110, 120],
            "cp_flag": ["P", "P", "C", "C"],
            "mid": [1.0, 2.0, 2.0, 1.0],
            "best_bid": [0.9, 1.9, 1.9, 0.9],
        }
    )
    spot, rf = 100.0, 1.0
    result = premium_for_gamma(q, gamma=1, rf_gross=rf, spot=spot)
    sums = option_sum(q, boundary=spot * rf, strike_power=0)
    expected = np.log1p(2.0 * sums["total_sum"] / spot**2)
    assert np.isclose(result["premium"], expected)


def test_project_horizon_and_newey_west_specification():
    assert HORIZON_DAYS == {"1m": 30, "3m": 90, "6m": 180, "12m": 360}
    assert ANNUALIZATION_FACTOR == {"1m": 12.0, "3m": 4.0, "6m": 2.0, "12m": 1.0}
    assert NW_LAGS == {"1m": 21, "3m": 65, "6m": 130, "12m": 260}
