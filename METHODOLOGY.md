# Martin (2025) Replication Methodology

This document freezes the empirical choices used by the project so the final
results are reproducible and defensible in the oral presentation.

## Primary replication target

The primary target is Ian W. R. Martin (2025), *Information in Derivatives
Markets: Forecasting Prices with Prices*, Annual Review of Financial Economics
17, 295–319.

The required replication is:

- daily SVIX at 1, 3, 6, and 12 months;
- Table 1 forecasting regressions;
- Figures 1 and 2 for power-utility investors with gamma = 1, 2, 3;
- an update beyond December 2022 using the latest data available through WRDS.

The 2025 article gives the equations and regression specification but does not
restate every data-cleaning and discretization detail. Because its Table 1
explicitly extends the SVIX sample from Martin (2017), this project uses the
published Martin (2017) Appendix for those implementation details where the
2025 article is silent.

## Data

- OptionMetrics IvyDB US, S&P 500 index (`secid = 108105`).
- OptionMetrics zero-coupon yield curve.
- CRSP daily S&P Composite Index total-return field `sprtrn`.
- Licensed raw/intermediate data remain in `_data/` and are not committed.

The OptionMetrics pull is partitioned by year and controlled by a manifest. This
is an engineering change only; it does not change the sample definition.

## Option cleaning

The project follows the documented Martin cleaning logic as closely as the
modern OptionMetrics schema allows:

1. Remove unusable/missing records and exact replicated observations.
2. Require valid call/put flags, positive strike, nonnegative bid, and a
   non-crossed bid/ask market.
3. Midpoint = (best bid + best offer) / 2.
4. Use options with at least 7 and fewer than 550 calendar days to expiry.
5. Remove option series identified as Quarterlies.
6. Preserve OptionMetrics contract-series metadata, especially AM/PM settlement.
   Modern SPX data can contain more than one series on the same date/expiration,
   so those quotes are never combined into one synthetic surface.
7. For the strike integral, at each strike select the call or put with the lower
   midpoint. Then drop that selected strike if its selected closing bid is zero.

The last ordering is intentional: a zero-bid lower-mid OTM option is not replaced
by the more expensive ITM side.

## One surface per date and expiration

When modern data contain multiple coherent series with the same calendar
expiration (for example AM- and PM-settled SPX), the pipeline estimates a
forward for each series separately and selects one series for that
`date/exdate`. Selection is deterministic: greatest paired-strike coverage,
then smallest call-put parity gap, then narrowest median spread. Diagnostics
record every date/expiration for which this choice was necessary.

This modern-series rule prevents the invalid alternative of combining quotes
with different settlement conventions.

## Forward and risk-free rate

For each date/expiration:

- linearly interpolate the OptionMetrics zero curve in calendar maturity days;
- convert the decimal zero rate to a gross maturity-matched risk-free return;
- estimate the forward from put-call parity, preferring a linear interpolation
  of the strike at which `call - put = 0`, with a nearest-parity fallback.

## Discrete strike integral

For unique strikes K_i, use the CBOE/Martin weights

- first strike: `DeltaK = K_2 - K_1`;
- interior: `DeltaK_i = (K_{i+1} - K_{i-1}) / 2`;
- last strike: `DeltaK = K_N - K_{N-1}`.

The option integral is approximated by `sum Omega(K_i) * DeltaK_i`, where the
OTM option price is the lower-mid call/put selected at the strike.

## SVIX — Equation (19)

For one listed expiration, the horizon-total quantity is

`SVIX2_total = 2 / (Rf * S^2) * [put integral + call integral]`.

For fixed maturity construction, the listed-expiration SVIX variance is first
annualized and then linearly interpolated to 30, 90, 180, and 360 calendar days.
Those fixed horizons correspond to the project's 1-, 3-, 6-, and 12-month
series. When the target lies outside the eligible expiry range, the nearest two
eligible expirations are used for linear extrapolation and the observation is
flagged.

The main columns `svix2_1m`, ..., `svix2_12m` are annualized. Period-total
versions are also retained as `svix2_total_*` for auditing.

## Future returns and Table 1

CRSP daily total returns are compounded from the trading day after predictor
 date t through the first CRSP trading day on or after t + 30/90/180/360
calendar days. The predictor-date return is excluded.

For horizon h:

`excess_total_h = market_gross_h / rf_gross_h - 1`.

The Table 1 dependent variable is the annualized excess return, using factors
12, 4, 2, and 1 at the four horizons. The corresponding annualized SVIX squared
is the predictor.

The original samples are exactly:

- January 1996 through December 2022;
- February 2012 through December 2022.

Newey-West lags are 21, 65, 130, and 260 at 1, 3, 6, and 12 months.

Published coefficients, Newey-West standard errors, and R-squared values are
stored in `table1.py`; the pipeline writes a direct replicated-versus-published
comparison rather than silently forcing a match.

The update is also reported from 1996 through the latest usable realized return
at each horizon and separately for the post-2022 sample. The last usable date
naturally differs by horizon because a 12-month forecast needs 12 months of
subsequent CRSP data.

## Power-utility Figures 1 and 2 — Equations (48) and (49)

Equation (49) is implemented literally using the boundary `S * Rf` and the same
discrete strike-sum machinery. Risk-neutral moments through fourth order are
sufficient for gamma = 1, 2, 3.

Equation (48) implies

`E[R] / Rf = E*[R^(1+gamma)] / (E*[R] * E*[R^gamma])`.

The arithmetic equity premium is `Rf * (ratio - 1)`.

Figure 1 uses the fixed 30-day premium and, exactly as stated in Martin (2025),
annualizes it by multiplying by 12. Figure 2 uses the fixed 360-day premium at
its stated horizon. Both figures include the gamma = 1, 2, 3 premium panel and
the gamma = 2, 3 ratio-to-log-investor panel.

Martin (2025) explicitly notes that the article abstracts from the distinction
between capital gains and total returns/dividends; the printed Equation (49)
therefore uses `S * Rf` as its boundary. The project follows the printed formula
for the figure replication and documents this approximation.

## Extensions

The project then runs the proposal's three robustness exercises:

- five-year rolling predictive regressions (evaluated about monthly);
- horizon-level in-sample and expanding-window out-of-sample forecast metrics;
- ex-ante market regimes based on trailing 21-day returns, trailing realized
  volatility, and expanding-median SVIX, with no look-ahead in regime labels.

## Validation policy

The pipeline retains intermediate quantities rather than only final charts:
put/call contributions, total option sums, forwards, rates, source expirations,
extrapolation flags, future target dates, and published Table 1 comparisons.
Unit tests cover the forward crossing, AM/PM surface separation, Delta-K
weights, lower-mid/zero-bid ordering, quarterly identification, Equation (19),
fixed-maturity interpolation, future-return timing, and the gamma=1 special case
of Equations (48)-(49).

Final replication accuracy is assessed against the published Table 1 values.
Any material difference is investigated and documented; published values are
never substituted for generated results.
