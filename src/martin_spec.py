"""Shared empirical specification for the Martin (2025) replication.

Martin (2025) reports 1-, 3-, 6-, and 12-month horizons.  The constant-
maturity implementation follows the documented Martin (2017) construction:
30, 90, 180, and 360 calendar days, with linear maturity interpolation.
The 2025 Table 1 extends that earlier SVIX sample through December 2022.
"""

from __future__ import annotations

HORIZON_DAYS = {
    "1m": 30,
    "3m": 90,
    "6m": 180,
    "12m": 360,
}
HORIZONS = tuple(HORIZON_DAYS)

# Horizon-level annualization used for the paper-style regressions and figures.
# In particular, Martin (2025) explicitly annualizes the 1-month Figure 1
# premium by multiplying by 12.
ANNUALIZATION_FACTOR = {
    "1m": 12.0,
    "3m": 4.0,
    "6m": 2.0,
    "12m": 1.0,
}

NW_LAGS = {"1m": 21, "3m": 65, "6m": 130, "12m": 260}

MIN_DTE = 7
MAX_DTE = 550  # Martin (2017): fewer than 550 days to expiry.
YEAR_DAYS = 365.0

ORIGINAL_SAMPLE_START = "1996-01-01"
ORIGINAL_SAMPLE_END = "2022-12-31"
RECENT_SAMPLE_START = "2012-02-01"
POST_2022_START = "2023-01-01"


def year_fraction(days: float) -> float:
    """Convert calendar days to a year fraction for discounting."""
    return float(days) / YEAR_DAYS
