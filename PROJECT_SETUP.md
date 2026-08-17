# Drop-in setup and run instructions

These files replace the earlier Martin project implementation. Keep the
repository's existing `src/settings.py`, `.env`, `README.md`, `chartbook.toml`,
`environment.yml`, `docs_src/`, and `reports/` files.

## Files to copy

Copy the supplied `src/*.py`, `tests/test_martin_replication.py`, `dodo.py`, and
`METHODOLOGY.md` into the repository, replacing the earlier project-specific
versions with the same names.

The new option pipeline uses manifests and yearly partitions, so the old single
files `_data/optionmetrics_spx_raw.parquet` and
`_data/optionmetrics_spx_clean.parquet` are no longer inputs. They can remain on
disk until the new pipeline is validated, then be deleted to reclaim space.

## Re-run the current Jan-Jun 2022 validation sample

The existing fallback variables still work:

```bash
export P06_START_DATE=2022-01-03
export P06_END_DATE=2022-06-30

doit list
doit pull_martin_data:optionmetrics
doit pull_martin_data:zero_curve
doit pull_martin_data:crsp_sp500
doit clean_martin_data
doit forward_prices
doit svix
doit future_returns
doit power_utility
doit run_pytest
```

Do not run Table 1 or the rolling extensions on a six-month sample.

Sanity-check the corrected fixed-horizon SVIX:

```bash
python - <<'PY'
import pandas as pd
x = pd.read_parquet('_data/svix_daily.parquet')
print(x[['date','svix_1m','svix_3m','svix_6m','svix_12m']].head())
print(x[['svix_1m','svix_3m','svix_6m','svix_12m']].describe())
print(x.filter(like='extrapolated_').mean())
PY
```

Inspect multi-series handling:

```bash
python - <<'PY'
import pandas as pd
x = pd.read_csv('_data/forward_surface_diagnostics.csv')
print('multi-surface groups:', len(x))
print(x.head(20).to_string(index=False))
PY
```

## Full replication and update

After the test sample passes, remove the temporary shared-window variables so
OptionMetrics and CRSP can use their own full date ranges:

```bash
unset P06_START_DATE
unset P06_END_DATE
unset P06_OPTION_START_DATE
unset P06_OPTION_END_DATE
unset P06_CRSP_START_DATE
unset P06_CRSP_END_DATE
```

Then run the full pipeline:

```bash
doit
```

The defaults request OptionMetrics from January 1996 through the latest rows
available in the current year table and CRSP from January 1996 through its
latest available rows. OptionMetrics is pulled in yearly chunks, so progress is
visible and each active partition is recorded in a manifest.

The required outputs include:

- `_data/svix_daily.parquet`
- `_output/table1_replication.csv`
- `_output/table1_published_comparison.csv`
- `_output/table1_updated.csv`
- `_output/table1_post2022.csv`
- `_output/replication_tolerance_report.csv`
- `_output/figure1_power_utility.png`
- `_output/figure2_power_utility.png`
- `_output/rolling_predictive_power.csv` and `_output/rolling_predictive_beta.png`
- `_output/horizon_comparison.csv` and `_output/horizon_comparison.png`
- `_output/regime_analysis.csv` and `_output/regime_beta_comparison.png`
- `_output/01_martin_replication.html`
- `_output/pytest_results.xml`

Build the Chartbook site separately after the research outputs have been
reviewed:

```bash
doit build_chartbook_site
```
