# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Martin (2025) — SVIX Replication and Extension
#
# This notebook provides a guided tour of the cleaned data, the core replication, and the main extensions in the project. Reusable data pulls, cleaning routines, pricing calculations, regressions, and robustness checks live in ordinary Python modules under `src/`; this notebook reads those cleaned datasets and generated outputs so the reader can see how the pieces fit together.
#
# The project replicates Ian W. R. Martin's *Information in Derivatives Markets: Forecasting Prices with Prices* and extends the analysis through the latest available 2025 data.

# %%
from pathlib import Path

import pandas as pd
from matplotlib import pyplot as plt
from IPython.display import Image, display

from clean_crsp_sp500 import load_clean_crsp_sp500
from clean_optionmetrics import load_clean_manifest
from settings import config
from svix import load_svix_daily

DATA_DIR = Path(config("DATA_DIR"))
OUTPUT_DIR = Path(config("OUTPUT_DIR"))

pd.set_option("display.max_columns", 50)
pd.set_option("display.width", 140)

# %% [markdown]
# ## 1. Reproducible data coverage
#
# The project uses licensed OptionMetrics and CRSP data accessed through WRDS. OptionMetrics data are partitioned by year so the full 1996–present pipeline remains restartable and memory-safe. This first check shows the date coverage and size of the cleaned datasets used downstream.

# %%
manifest = load_clean_manifest()
crsp = load_clean_crsp_sp500()
svix = load_svix_daily()

coverage = pd.DataFrame(
    {
        "dataset": ["SPX options", "CRSP S&P 500 returns", "SVIX"],
        "first_date": [
            pd.to_datetime(manifest["start_date"]).min(),
            crsp["date"].min(),
            svix["date"].min(),
        ],
        "last_date": [
            pd.to_datetime(manifest["end_date"]).max(),
            crsp["date"].max(),
            svix["date"].max(),
        ],
        "rows": [manifest["clean_rows"].sum(), len(crsp), len(svix)],
    }
)
coverage

# %% [markdown]
# The cleaned datasets cover the original Martin sample and extend into 2025. The option and SVIX series can extend farther than a realized-return regression at longer horizons because a 6- or 12-month forecast requires future CRSP observations that have not yet occurred at the end of the sample.

# %% [markdown]
# ## 2. Cleaning and option-surface diagnostics
#
# SVIX is sensitive to the quality of the option surface. Before constructing the index, the pipeline removes invalid observations, checks contract metadata, constructs usable option surfaces, and records diagnostics.

# %%
pd.read_csv(DATA_DIR / "optionmetrics_cleaning_diagnostics.csv").head(20)

# %%
pd.read_csv(DATA_DIR / "forward_surface_diagnostics.csv").head(20)

# %% [markdown]
# ## 3. Daily fixed-horizon SVIX
#
# The pipeline constructs daily SVIX at the 1-, 3-, 6-, and 12-month horizons. Short-horizon SVIX reacts more sharply to sudden market stress, while longer horizons are smoother.

# %%
svix_plot = svix.copy()
svix_plot["date"] = pd.to_datetime(svix_plot["date"])

ax = svix_plot.set_index("date")[["svix_1m", "svix_3m", "svix_6m", "svix_12m"]].plot(
    figsize=(11, 5)
)
ax.set_ylabel("Annualized SVIX")
ax.set_title("SVIX fixed-horizon term structure")
plt.tight_layout()
plt.show()

# %% [markdown]
# ## 4. Summary statistics
#
# The summary-statistics output gives a compact view of the level and dispersion of SVIX across horizons before we move to the forecasting regressions.

# %%
pd.read_csv(OUTPUT_DIR / "svix_summary_stats.csv")

# %% [markdown]
# Across the full sample, average annualized SVIX is close to 19–20% across maturities. Crisis peaks are much larger at the front end of the curve, which is consistent with near-term option prices reacting most strongly when perceived market risk rises suddenly.

# %% [markdown]
# ## 5. Martin (2025) Table 1 replication
#
# The central forecasting regression relates future S&P 500 excess returns to contemporaneous SVIX. The project reproduces the paper's original sample and uses horizon-specific Newey–West corrections for overlapping returns.

# %%
pd.read_csv(OUTPUT_DIR / "table1_replication.csv")

# %%
pd.read_csv(OUTPUT_DIR / "table1_published_comparison.csv")

# %% [markdown]
# The replication is close to the published results across horizons. The 6-month coefficient is especially close to Martin's published estimate, and the project's replication-tolerance tests confirm that the results fall within documented numerical tolerances.

# %%
pd.read_csv(OUTPUT_DIR / "replication_tolerance_report.csv")

# %% [markdown]
# ## 6. Updated results through 2025
#
# The same forecasting specification is recomputed using all available data. Because realized returns must be observed after the forecast date, the latest usable date depends on the horizon.

# %%
pd.read_csv(OUTPUT_DIR / "table1_updated.csv")

# %%
pd.read_csv(OUTPUT_DIR / "table1_post2022.csv")

# %% [markdown]
# The post-2022 estimates remain positive at all four horizons and are particularly strong at 1 and 3 months. The 12-month result is economically large, but it should be interpreted cautiously because the short updated sample contains only about two independent 12-month periods after accounting for overlapping returns.

# %% [markdown]
# ## 7. Martin (2025) Figures 1 and 2 — power utility
#
# The project also replicates the paper's power-utility equity-premium figures for risk aversion \(\gamma = 1,2,3\), then extends the same calculations through the latest available data.

# %%
display(Image(filename=str(OUTPUT_DIR / "figure1_power_utility_replication.png")))
display(Image(filename=str(OUTPUT_DIR / "figure2_power_utility_replication.png")))
display(Image(filename=str(OUTPUT_DIR / "figure1_power_utility_updated.png")))
display(Image(filename=str(OUTPUT_DIR / "figure2_power_utility_updated.png")))

# %% [markdown]
# The updated figures preserve the same economic interpretation as the replication sample: higher option-implied risk is associated with a larger required equity premium, and the effect becomes more pronounced for more risk-averse investors during periods of market stress.

# %% [markdown]
# ## 8. Forecast-horizon comparison

# %%
pd.read_csv(OUTPUT_DIR / "horizon_comparison.csv")

# %%
display(Image(filename=str(OUTPUT_DIR / "horizon_comparison.png")))

# %% [markdown]
# The 6-month horizon has the strongest out-of-sample performance in the project. The 12-month horizon also remains positive out of sample, while the 1- and 3-month horizons have negative out-of-sample \(R^2\).

# %% [markdown]
# ## 9. Time variation, regimes, and robustness
#
# A constant full-sample coefficient can hide substantial changes through time. The remaining extensions examine rolling estimates, market regimes, crisis sensitivity, and the forward-price convention.

# %%
pd.read_csv(OUTPUT_DIR / "rolling_predictive_power.csv").head()

# %%
display(Image(filename=str(OUTPUT_DIR / "rolling_predictive_beta.png")))

# %% [markdown]
# The rolling estimates show that the forecasting coefficient is not stable through time. Large changes occur around major market episodes, so the full-sample slope should be interpreted as an average across very different environments.

# %%
pd.read_csv(OUTPUT_DIR / "regime_analysis.csv").head(24)

# %%
display(Image(filename=str(OUTPUT_DIR / "regime_beta_comparison.png")))

# %% [markdown]
# The regime analysis shows the strongest state dependence at the 6- and 12-month horizons. Predictive power is much stronger when realized volatility or SVIX is high and is weak in several calm-market specifications.

# %%
pd.read_csv(OUTPUT_DIR / "crisis_window_analysis.csv")

# %%
pd.read_csv(OUTPUT_DIR / "crisis_leave_one_year_out.csv").head(20)

# %%
display(Image(filename=str(OUTPUT_DIR / "crisis_leave_one_year_out.png")))

# %% [markdown]
# The crisis checks show that the positive relationship is not simply created by the Global Financial Crisis. Removing the main 2008–2009 crisis window actually increases the short-horizon slopes, although individual years such as 2008, 2009, and 2020 have substantial leverage.

# %%
pd.read_csv(OUTPUT_DIR / "forward_price_discrepancy.csv")

# %%
pd.read_csv(OUTPUT_DIR / "forward_robustness_table1.csv")

# %%
display(Image(filename=str(OUTPUT_DIR / "forward_robustness.png")))

# %% [markdown]
# Although the alternative forward prices differ modestly from the baseline construction, the resulting Table 1 coefficients are essentially unchanged. The main replication results are therefore not an artifact of the forward-price convention.

# %% [markdown]
# ## 10. Main takeaways
#
# 1. **The replication works.** The original-sample forecasting regressions and power-utility figures closely match Martin's published results within documented tolerances.
# 2. **The relationship persists after 2022.** Updated estimates remain positive, although long-horizon inference is limited by the short amount of non-overlapping post-2022 data.
# 3. **Forecasting performance depends on horizon.** The 6-month horizon produces the strongest out-of-sample performance, while the shortest horizons are weaker out of sample.
# 4. **The relationship is state dependent.** SVIX is substantially more informative in high-volatility and high-SVIX environments than in calm markets.
# 5. **The main findings are robust.** Crisis-window tests and an alternative forward-price convention do not overturn the central results.
#
# This notebook is intentionally a tour rather than the implementation itself. The reusable research logic remains in the project modules under `src/`, where it can be tested, modified, and run end-to-end with PyDoit.
