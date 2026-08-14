# Generated Data Dictionary

The listed files are generated locally and should not be committed when they
contain licensed WRDS data.

| File | Main unit | Key fields |
|---|---|---|
| `_data/optionmetrics_spx_raw_manifest.csv` | raw partition | table, start/end date, row count, local partition path |
| `_data/optionmetrics_spx_underlying_raw.parquet` | date | SPX close |
| `_data/optionmetrics_zero_curve_clean.parquet` | date × maturity | maturity_days, zero_rate |
| `_data/crsp_sp500_daily_clean.parquet` | date | `ret` = CRSP S&P total return |
| `_data/optionmetrics_spx_clean_manifest.csv` | clean partition | source period, raw/clean row counts, path |
| `_data/option_expiration_inputs.parquet` | date × expiration | surface_key, DTE, spot, zero_rate, rf_gross, forward, parity diagnostics |
| `_data/svix_by_expiration.parquet` | date × expiration | put/call contributions, option sum, horizon-total and annualized listed-expiry SVIX |
| `_data/svix_daily.parquet` | date | fixed 1m/3m/6m/12m SVIX, source maturities, extrapolation flags |
| `_data/future_sp500_returns.parquet` | date | realized target dates, future total returns, risk-free gross returns, total and annualized excess returns |
| `_data/power_utility_by_expiration.parquet` | date × expiration | Eq. 49 moments and Eq. 48 equity premia for gamma 1/2/3 |
| `_data/power_utility_daily.parquet` | date | fixed 1m/12m power-utility premia and ratios |

## Important column conventions

### `svix_daily.parquet`

- `svix2_h`: **annualized** fixed-horizon SVIX variance used as the Table 1 predictor.
- `svix_h`: square root of `svix2_h`.
- `svix2_total_h`: corresponding period-total variance retained for audit.
- `source_dte_left_h`, `source_dte_right_h`: listed expirations used for maturity interpolation.
- `extrapolated_h`: whether the target maturity required linear extrapolation.

### `future_sp500_returns.parquet`

- `market_fwd_h`: simple CRSP total return over the target period.
- `rf_gross_h`: maturity-matched gross risk-free return.
- `excess_total_h = (1 + market_fwd_h) / rf_gross_h - 1`.
- `excess_fwd_h`: annualized Table 1 dependent variable using factor 12/4/2/1.
- `realized_target_date_h`: actual CRSP trading date used to close the horizon.

### Table 1 outputs

- `table1_replication.csv`: original Jan 1996–Dec 2022 and Feb 2012–Dec 2022 samples.
- `table1_published_comparison.csv`: replicated vs published alpha, beta, Newey-West SE, and R-squared.
- `table1_updated.csv`: Jan 1996 through the latest usable realized outcome by horizon.
- `table1_post2022.csv`: post-paper sample beginning Jan 2023.
- `replication_tolerance_report.csv`: diagnostic pass/fail checks against documented tolerances.
