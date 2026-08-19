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
# This notebook is the guided tour required by the project. Reusable data pulls,
# cleaning, pricing calculations, regressions, and extensions live in ordinary
# Python modules under `src/`; this notebook consumes the generated outputs.

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

# %% [markdown]
# ## 1. Reproducible data coverage
#
# Licensed OptionMetrics data are partitioned by year so the full 1996-present
# pipeline remains restartable and memory-safe.

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
# ## 2. Cleaning and surface diagnostics

# %%
pd.read_csv(DATA_DIR / "optionmetrics_cleaning_diagnostics.csv")

# %%
pd.read_csv(DATA_DIR / "forward_surface_diagnostics.csv").head(20)

# %% [markdown]
# ## 3. Daily fixed-horizon SVIX
#
# `svix2_1m`, `svix2_3m`, `svix2_6m`, and `svix2_12m` are the annualized
# variance forecasts used in the forecasting regressions. Period-total
# quantities are retained in separate `svix2_total_*` columns.

# %%
svix.set_index("date")[["svix_1m", "svix_3m", "svix_6m", "svix_12m"]].plot(
    figsize=(11, 5)
)
plt.ylabel("Annualized SVIX")
plt.title("SVIX fixed-horizon term structure")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "svix_term_structure.png", dpi=200)
plt.show()

# %% [markdown]
# ## 4. Martin (2025) Table 1 replication

# %%
pd.read_csv(OUTPUT_DIR / "table1_replication.csv")

# %%
pd.read_csv(OUTPUT_DIR / "table1_published_comparison.csv")

# %% [markdown]
# ## 5. Required post-2022 update

# %%
pd.read_csv(OUTPUT_DIR / "table1_updated.csv")

# %%
pd.read_csv(OUTPUT_DIR / "table1_post2022.csv")

# %% [markdown]
# ## 6. Martin (2025) Figures 1 and 2 — power utility

# %%
display(Image(filename=str(OUTPUT_DIR / "figure1_power_utility_replication.png")))
display(Image(filename=str(OUTPUT_DIR / "figure2_power_utility_replication.png")))
display(Image(filename=str(OUTPUT_DIR / "figure1_power_utility_updated.png")))
display(Image(filename=str(OUTPUT_DIR / "figure2_power_utility_updated.png")))

# %% [markdown]
# ## 7. Project extensions

# %%
pd.read_csv(OUTPUT_DIR / "rolling_predictive_power.csv").head()

# %%
pd.read_csv(OUTPUT_DIR / "horizon_comparison.csv")

# %%
pd.read_csv(OUTPUT_DIR / "regime_analysis.csv").head(24)
