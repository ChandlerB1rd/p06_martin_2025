# P06 – Martin (2025): Information in Derivatives Markets — Forecasting Prices with Prices

## About This Project

This project replicates and extends the empirical analysis in:

> Martin, Ian W. R. (2025). *Information in Derivatives Markets: Forecasting Prices with Prices*.  
> *Annual Review of Financial Economics*, 17, 295–319.

Using OptionMetrics IvyDB US and CRSP data from WRDS, we will construct the daily SVIX index from S&P 500 index options, reproduce the paper's main forecasting results, and extend the analysis through the most recent available data.

The required replication includes SVIX at the 1-, 3-, 6-, and 12-month horizons, Table 1, and Figures 1 and 2.

## Why This Project Is Useful

Constructing SVIX requires several nontrivial steps: cleaning a large option panel, matching interest rates and maturities, estimating forward prices, integrating option prices across strikes, and joining the resulting forecasts to future S&P 500 returns.

This repository is intended to provide a reproducible pipeline that allows a WRDS-authorized user to:

- pull the required OptionMetrics and CRSP data;
- construct an updated SVIX term structure;
- reproduce Martin's published tables and figures;
- evaluate the stability and usefulness of SVIX as a forecasting signal; and
- adapt the code to different dates, horizons, and market-condition definitions.

Raw licensed WRDS data will not be committed to GitHub. The repository will contain the code, configuration examples, documentation, tests, and generated research outputs needed to recreate the analysis.

## Research Question

Our central extension asks:

> **How robust is SVIX as a forecasting signal for future S&P 500 excess returns?**

Subject to instructor feedback, we will study robustness along three dimensions:

1. **Time:** Has the predictive relationship remained stable through the sample?
2. **Horizon:** Which of the 1-, 3-, 6-, and 12-month horizons provides the strongest forecasting performance?
3. **Market conditions:** Does SVIX perform differently in calm, volatile, rising, or falling markets?

## Required Replication

We will complete the following assigned tasks:

- Construct daily SVIX at:
  - 1 month;
  - 3 months;
  - 6 months; and
  - 12 months.
- Replicate Martin's Table 1 forecasting regressions.
- Replicate Martin's Figures 1 and 2 for power-utility investors with risk aversion \(\gamma = 1, 2, 3\).
- Match the paper's original sample definitions as closely as the available data and methodology allow.
- Extend the SVIX series, tables, and figures from December 2022 through the most recent available WRDS data.
- Compare replicated results with the published values using documented tolerances and unit tests.

## Planned Project Extension

Updating the paper through the present is already part of the assigned replication. Our additional contribution is to examine whether SVIX is a stable and practically useful return-forecasting signal.

The following analyses are planned and remain subject to instructor feedback during the consultation.

### 1. Rolling Predictive Power

We will estimate fixed-window rolling versions of the forecasting regression to study how the relationship between SVIX and future excess returns changes through time.

Potential outputs include:

- rolling slope coefficients;
- rolling \(R^2\);
- rolling Newey–West t-statistics; and
- confidence intervals around the rolling slope estimates.

### 2. Forecast-Horizon Comparison

We will compare forecasting performance across the 1-, 3-, 6-, and 12-month horizons.

Potential metrics include:

- in-sample \(R^2\);
- out-of-sample \(R^2\);
- root mean squared error;
- mean absolute error;
- forecast bias; and
- correlation between SVIX-implied premia and realized future excess returns.

This analysis will identify whether the predictive content of option prices is concentrated at shorter or longer horizons.

### 3. Market-Regime Analysis

We will test whether SVIX performs differently across market environments using variables constructed from the project's OptionMetrics and CRSP data.

Potential regime definitions include:

- positive versus negative trailing market returns;
- high versus low realized volatility from CRSP returns; and
- high versus low SVIX environments.

The final regime definitions, thresholds, and estimation approach will be documented and selected to avoid look-ahead bias.

## Data Sources

All licensed data are accessed through WRDS.

### OptionMetrics IvyDB US

S&P 500 index option data for `secid = 108105`, including fields needed to identify and value each contract:

- observation date;
- expiration date;
- strike price;
- put/call indicator;
- bid price;
- ask price;
- option midpoint or settlement-related fields when appropriate;
- underlying S&P 500 index level; and
- contract identifiers and data-quality fields.

### OptionMetrics Zero-Coupon Yield Curve

The zero-coupon curve will be used to construct maturity-matched discount factors and gross risk-free returns.

Required fields include:

- curve date;
- maturity;
- zero-coupon rate; and
- discount factor, when directly available.

### CRSP

CRSP will provide the daily S&P 500 total-return series required to construct realized future market returns.

From the CRSP series, we will derive:

- cumulative 1-, 3-, 6-, and 12-month future total returns;
- horizon-matched realized excess returns; and
- trailing returns and realized-volatility measures used in the regime analysis.

## Methodology Overview

### Option Cleaning

The option-cleaning procedure will be documented explicitly and may include:

- removing missing or invalid quotes;
- removing crossed markets;
- constructing bid-ask midpoint prices;
- handling zero bids and extremely wide spreads;
- removing duplicate contracts;
- verifying strike and expiration consistency;
- retaining the appropriate out-of-the-money puts and calls; and
- recording data-coverage and option-count diagnostics.

### Forward Prices and Maturities

For each date and expiration, we will:

- match the zero-coupon curve to the option maturity;
- estimate the forward price using the methodology agreed upon during the instructor consultation;
- separate out-of-the-money puts and calls at the forward boundary; and
- interpolate between available expirations to obtain fixed 1-, 3-, 6-, and 12-month horizons.

### SVIX Construction

We will implement Equation (19) from Martin (2025), numerically integrating out-of-the-money put and call prices across strikes.

The code will separately retain:

- the put contribution;
- the call contribution;
- the total option-price integral;
- \(SVIX^2\); and
- SVIX.

### Forecasting Regressions

We will merge daily SVIX forecasts with subsequent CRSP total returns and horizon-matched risk-free returns.

Table 1 will be replicated using the paper's regression specification and Newey–West standard errors. The paper reports 21, 65, 130, and 260 lags at the 1-, 3-, 6-, and 12-month horizons, respectively.

### Power-Utility Equity Premia

Figures 1 and 2 will be replicated using the paper's risk-neutral moment formulas for investors with risk aversion \(\gamma = 1, 2, 3\).

The 1-month series will be annualized consistently with the paper, while the 1-year series will be reported at its stated horizon.

## Project Roadmap

### Phase 1 — Project Setup

- Scaffold the repository using the required Chartbook Cookiecutter template.
- Configure Conda, `.env.example`, `settings.py`, PyDoit, tests, and GitHub collaboration.
- Remove or replace irrelevant template examples as project modules are introduced.

### Phase 2 — Data Collection

- Pull SPX option data from OptionMetrics.
- Pull the OptionMetrics zero-coupon yield curve.
- Pull the CRSP S&P 500 total-return series.
- Cache raw data locally in the configured `_data` directory.

### Phase 3 — Data Cleaning and Tidy Datasets

- Clean and validate OptionMetrics quotes.
- Clean and validate CRSP returns.
- Construct maturity and interest-rate matches.
- Save separate tidy option, yield-curve, return, and merged analysis datasets.

### Phase 4 — SVIX Construction

- Estimate forward prices.
- Integrate option prices across strikes.
- Interpolate to fixed horizons.
- Construct and validate daily SVIX at 1, 3, 6, and 12 months.

### Phase 5 — Required Replication and Update

- Replicate Table 1.
- Replicate Figures 1 and 2.
- Compare results with the paper.
- Extend all required outputs through the latest available data.

### Phase 6 — Extension Analysis

- Estimate rolling forecasting regressions.
- Compare forecasting performance across horizons.
- Evaluate forecasting performance across market regimes.

### Phase 7 — Product, Testing, and Documentation

- Automate the pipeline end-to-end with PyDoit.
- Add motivated unit tests and replication-tolerance tests.
- Generate all Chartbook tables and figures from code.
- Produce the Jupyter notebook tour and LaTeX report.
- Prepare the proposal presentation, final presentation, and oral defense.

## Expected Outputs

### Required Deliverables

- Daily SVIX series at four horizons.
- Replicated Table 1.
- Replicated Figures 1 and 2.
- Updated SVIX series, regressions, and power-utility figures.
- A single LaTeX report containing the generated tables and figures.
- A Jupyter notebook that provides a guided tour of the cleaned data and analysis.

### Additional Research Product

A reusable **SVIX forecasting research toolkit** containing:

- automated WRDS data pulls;
- documented option-cleaning procedures;
- a tidy date-by-horizon SVIX dataset generated locally;
- reusable functions for forward-price estimation and SVIX integration;
- rolling predictive-power analysis;
- horizon-level forecast comparisons;
- market-regime analysis;
- tests and data-quality diagnostics; and
- a reproducible Chartbook site.

## Team Responsibilities

The assignments below identify the primary lead for each workstream. Both members will review the full pipeline, contribute code through branches and pull requests, and be prepared to explain and modify the complete project during the oral defense.

### Chandler Bird — Data, Returns, Table 1, and Regime Analysis Lead

Chandler will lead:

- WRDS extraction for OptionMetrics, the zero-coupon curve, and CRSP;
- cleaning and validation of the option, rate, and return datasets;
- construction and documentation of tidy intermediate datasets;
- creation of future 1-, 3-, 6-, and 12-month CRSP total and excess returns;
- merging the SVIX and return datasets;
- replication of Table 1 and its Newey–West regressions;
- design and implementation of the market-regime analysis; and
- regime-specific tables, figures, and interpretation.

### Andrew Heekin — SVIX and Power-Utility Figures Lead

Andrew will lead:

- zero-coupon maturity matching for the SVIX calculation;
- forward-price construction;
- implementation of Equation (19);
- numerical integration across strikes;
- expiration interpolation to the four fixed horizons;
- construction and validation of the daily SVIX term structure;
- implementation of the risk-neutral moment calculations in Equations (48) and (49); and
- replication of Figures 1 and 2.

### Shared Responsibilities

Both team members will contribute to:

- final option-filtering and interpolation decisions;
- rolling predictive-power analysis;
- forecast-horizon comparison;
- replication-tolerance tests and other unit tests;
- PyDoit task design and end-to-end automation;
- code review and debugging;
- Chartbook development;
- documentation and the data dictionary;
- the Jupyter notebook and LaTeX report;
- proposal and final presentations; and
- oral-defense preparation.

## Repository Organization

The repository follows the required Chartbook Cookiecutter structure. Project-specific source files will be added under `src/`, while licensed raw data and reproducible intermediate data will remain outside version control in `_data/`.

Key locations include:

```text
assets/          Non-generated images and presentation assets
data_manual/     Small manually maintained files that may be version controlled
docs_src/        Chartbook page definitions and project documentation
reports/         LaTeX report and presentation source files
src/             Data pulls, cleaning, SVIX construction, analysis, and tests
_data/           Raw and intermediate data generated locally; excluded from Git
_output/         Generated tables, figures, notebooks, and Chartbook outputs
dodo.py          PyDoit task definitions for the end-to-end pipeline
environment.yml  Conda environment specification
.env.example     Example local configuration without private credentials
```

Raw OptionMetrics and CRSP data must not be committed to the repository.

## Pipeline

The intended end-to-end workflow is:

1. Download the required WRDS data.
2. Clean and validate OptionMetrics, yield-curve, and CRSP data.
3. Construct forward prices and maturity-matched risk-free returns.
4. Compute SVIX at the four target horizons.
5. Construct future realized market and excess returns.
6. Replicate Table 1.
7. Replicate Figures 1 and 2.
8. Extend the required results through the latest available data.
9. Run the planned robustness extensions.
10. Generate Chartbook pages, tables, figures, notebooks, and the LaTeX report.

## Quick Start

### Prerequisites

You must have:

- Conda or Mamba;
- a LaTeX distribution such as MacTeX or TeX Live;
- Git;
- Python dependencies specified by the project environment; and
- authorized WRDS access to OptionMetrics IvyDB US and CRSP.

### Create and Activate the Environment

```bash
conda env create -f environment.yml
conda activate p06_martin_2025
```

To update an existing environment:

```bash
conda env update -f environment.yml --prune
```

### Configure Environment Variables

Copy the example configuration:

```bash
cp .env.example .env
```

Add only local paths and private credentials to `.env`. Never commit `.env` or WRDS credentials.

On macOS or Linux, environment variables may be exported with:

```bash
set -a
source .env
set +a
```

### Run the Pipeline

Run PyDoit from the project root, where `dodo.py` is located:

```bash
doit
```

List available tasks with:

```bash
doit list
```

### Run Tests

```bash
pytest --doctest-modules
```

### Format and Lint Python Code

```bash
ruff format .
ruff check --select I --fix .
ruff check . --fix
```

## Data and Output Storage

- `_data/` contains raw and intermediate data that can be recreated by running the pipeline. It is excluded from Git.
- `_output/` contains generated tables, figures, notebooks, and site artifacts.
- `data_manual/` is reserved for small manually maintained inputs that cannot be automatically pulled.
- `.env` contains local paths and secrets and must never be tracked.
- `.env.example` documents the required configuration without containing credentials.

## Naming Conventions

- Files and functions that retrieve external data use the `pull_` prefix.
- Functions that read locally cached data use the `load_` prefix.
- Cleaning logic is kept separate from analysis logic.
- Generated tables and figures are produced from code rather than edited manually.
- Each Python file includes a module docstring.
- Public functions use descriptive names and include docstrings where appropriate.

## Reproducibility and Git Practices

- Both group members will make substantive commits.
- Both group members will create and merge at least one pull request.
- Raw licensed data, private paths, and credentials will not be committed.
- All final tables and figures will be reproducible through PyDoit.
- Important calculations will be covered by motivated unit tests.
- Changes to methodology will be documented in the README, code comments, and project report.

## Project Status

This README reflects the proposal-stage project plan. Specific filtering rules, interpolation methods, rolling-window lengths, regime definitions, and extension priorities may be revised after the instructor consultation and documented in subsequent commits.
