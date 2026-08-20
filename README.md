# P06 – Martin (2025): Information in Derivatives Markets — Forecasting Prices with Prices

## About This Project

This project replicates and extends the empirical analysis in:

> Martin, Ian W. R. (2025). *Information in Derivatives Markets: Forecasting Prices with Prices*.  
> *Annual Review of Financial Economics*, 17, 295–319.

Using OptionMetrics IvyDB US and CRSP data from WRDS, we construct daily SVIX measures for the S&P 500 at the 1-, 3-, 6-, and 12-month horizons, replicate the paper's main forecasting results and power-utility figures, and extend the analysis through the latest available 2025 data.

The goal is not only to reproduce the published results, but also to test how stable and useful the SVIX forecasting relationship is across time, horizons, market conditions, crises, and implementation choices.

The repository also includes a read-only **SVIX Monitor** that presents the latest available option-implied equity premium, SVIX level, historical regime, time series, and forecasting-regression results from the same research pipeline.

## Research Question

Our main extension asks:

> **How robust is SVIX as a forecasting signal for future S&P 500 excess returns?**

We examine that question along four dimensions:

1. **Time:** Does the forecasting relationship remain stable across the sample?
2. **Horizon:** Which of the 1-, 3-, 6-, and 12-month horizons performs best?
3. **Market conditions:** Is SVIX more informative in calm or stressed markets?
4. **Specification robustness:** Are the results sensitive to crisis observations or the forward-price convention used in SVIX construction?

## Key Findings

The replication closely matches Martin's published return-predictability results through December 2022. In the original 1996–2022 sample, our 1-month forecasting regression produces a slope of 1.425 versus the published 1.569, while the 6-month estimate is 2.432 versus the published 2.418.

Extending the sample beyond 2022 shows that the SVIX-return relationship has not disappeared. In the January 2023 through latest usable subsample, estimated forecasting slopes are positive at all four horizons:

| Horizon | Beta | Newey–West t-stat | R² |
|---|---:|---:|---:|
| 1 month | 8.655 | 3.56 | 11.15% |
| 3 months | 9.903 | 4.70 | 22.75% |
| 6 months | 6.151 | 1.89 | 14.68% |
| 12 months | 6.221 | 3.39 | 20.23% |

The 12-month post-2022 estimate should be interpreted cautiously because the short updated sample contains only about two independent 12-month periods.

The horizon comparison also shows that strong in-sample fit does not automatically translate into short-horizon forecasting performance. Out of sample, the 1- and 3-month horizons have negative R², while the 6-month horizon is strongest at approximately 6.3% and the 12-month horizon remains positive at approximately 2.8%.

The regime analysis provides some of the clearest evidence in the project. At the 6- and 12-month horizons, predictive power is materially stronger in high-volatility and high-SVIX states than in calm markets. This suggests that option prices contain the most useful information about expected equity returns when perceived market risk is elevated.

Rolling regressions show that the forecasting coefficient varies substantially through time, particularly around the Global Financial Crisis, COVID-19, and the post-2022 period. The relationship is therefore not well described by a single constant coefficient over the entire sample.

Finally, the robustness tests show that the main conclusions are not driven by a single implementation choice. Removing the 2008–2009 crisis window does not eliminate the short-horizon relationship, and replacing the baseline forward-price construction with the OptionMetrics forward leaves the Table 1 coefficients essentially unchanged.

## Replication

The completed replication includes:

- daily SVIX at the 1-, 3-, 6-, and 12-month horizons;
- Martin's Table 1 forecasting regressions;
- Figures 1 and 2 for power-utility investors with risk aversion \(\gamma = 1, 2, 3\);
- the original paper sample through December 2022;
- an updated sample through the latest available 2025 data; and
- automated comparisons between replicated and published values using documented tolerances.

## Empirical Extensions

### Rolling Predictive Power

We estimate five-year rolling versions of the forecasting regression to study how the relationship between SVIX and future excess returns changes through time.

The rolling estimates show substantial variation across the sample. The coefficient changes sharply around major market episodes, which reinforces the idea that the information content of SVIX is state dependent rather than constant.

### Forecast-Horizon Comparison

We compare forecasting performance across the 1-, 3-, 6-, and 12-month horizons using both in-sample and out-of-sample metrics.

The 6-month horizon produces the strongest out-of-sample performance, with an OOS R² of approximately 6.3%. The 12-month horizon is also positive at approximately 2.8%, while the 1- and 3-month horizons have negative OOS R².

This result suggests that SVIX is more useful as a medium-term measure of expected market compensation for risk than as a short-term trading signal.

### Market-Regime Analysis

We estimate the forecasting relationship separately across market-direction, realized-volatility, and SVIX regimes.

The strongest state dependence appears at the 6- and 12-month horizons. High-volatility and high-SVIX environments exhibit larger forecasting coefficients and R² than calm environments, while the relationship is weak or close to zero in several low-risk states.

### Crisis-Window Robustness

We test whether the full-sample forecasting relationship is driven by a small number of extreme crisis observations.

Removing the 2008–2009 crisis window increases the 1- and 3-month forecasting slopes rather than eliminating them. Leave-one-year-out analysis also shows that years such as 2008, 2009, and 2020 have meaningful leverage on the estimates, but the positive relationship is not simply a Global Financial Crisis artifact.

### Forward-Price Robustness

The estimated forward price determines the boundary between out-of-the-money puts and calls used in the SVIX calculation, so we compare the baseline forward construction with the OptionMetrics-provided forward.

Although the forward estimates differ modestly, recomputing SVIX with the alternative convention leaves the Table 1 forecasting coefficients effectively unchanged. The main replication results are therefore not being driven by the forward-price convention.

## Data Sources

All licensed data are accessed through WRDS.

### OptionMetrics IvyDB US

We use S&P 500 index option data for `secid = 108105`, including:

- observation date;
- expiration date;
- strike price;
- put/call indicator;
- bid and ask prices;
- underlying S&P 500 index level; and
- contract identifiers and quality-control fields.

### OptionMetrics Zero-Coupon Yield Curve

The zero-coupon curve is used to construct maturity-matched discount factors and gross risk-free returns.

### CRSP

CRSP provides the daily S&P 500 total-return series used to construct realized future market returns.

The pipeline derives:

- cumulative 1-, 3-, 6-, and 12-month future total returns;
- horizon-matched realized excess returns; and
- trailing return and realized-volatility measures used in the extension analysis.

Raw licensed WRDS data are not committed to GitHub.

## Methodology

### Option Cleaning

The pipeline cleans and validates the SPX option panel before any SVIX calculation. The main checks include:

- removing missing or invalid quotes;
- removing crossed markets;
- constructing bid-ask midpoint prices;
- handling duplicate contracts and inconsistent metadata;
- validating strike and expiration information; and
- retaining the out-of-the-money puts and calls required for the SVIX integral.

The cleaning code also preserves diagnostics so that data coverage and option counts can be inspected throughout the sample.

### Forward Prices and Maturity Matching

For each date and expiration, the pipeline matches the OptionMetrics zero-coupon curve to the option maturity and constructs the forward price used to separate out-of-the-money puts and calls.

Fixed 1-, 3-, 6-, and 12-month SVIX horizons are then constructed by interpolating across available expirations.

A separate robustness specification recomputes the analysis using the OptionMetrics-provided forward price. The resulting Table 1 estimates are effectively unchanged.

### SVIX Construction

SVIX is implemented from Equation (19) in Martin (2025) by numerically integrating out-of-the-money put and call prices across strikes.

The intermediate output retains:

- put contribution;
- call contribution;
- total option-price integral;
- \(SVIX^2\); and
- SVIX.

### Forecasting Regressions

Daily SVIX forecasts are merged with subsequent CRSP total returns and horizon-matched risk-free returns.

Table 1 is estimated using the paper's forecasting specification with Newey–West standard errors. The lag choices are:

| Horizon | Newey–West lags |
|---|---:|
| 1 month | 21 |
| 3 months | 65 |
| 6 months | 130 |
| 12 months | 260 |

### Power-Utility Equity Premia

Figures 1 and 2 are replicated using the paper's risk-neutral moment formulas for investors with risk aversion \(\gamma = 1, 2, 3\).

The implementation produces both replication-sample figures through December 2022 and updated figures through the latest available data.

## Completed Workflow

The project is organized as a reproducible pipeline:

1. Pull licensed OptionMetrics and CRSP data from WRDS.
2. Clean option, zero-curve, and return data.
3. Construct forward prices and option surfaces.
4. Compute daily SVIX at four horizons.
5. Construct horizon-matched future excess returns.
6. Replicate Martin's Table 1 and power-utility figures.
7. Extend the analysis through the latest available 2025 data.
8. Run rolling, horizon, regime, crisis, and forward-price robustness analyses.
9. Generate tables, figures, notebook outputs, and the SVIX Monitor.
10. Validate the implementation with automated tests and replication tolerances.

## Repository Organization

The repository follows the required Chartbook Cookiecutter structure.

```text
assets/          Non-generated images and presentation assets
data_manual/     Small manually maintained files that may be version controlled
docs_src/        Chartbook page definitions and documentation
reports/         Report and presentation source files
src/             Data pulls, cleaning, SVIX construction, analysis, and tests
web/             SVIX Monitor web app (FastAPI backend + React frontend)
_data/           Raw and intermediate data generated locally; excluded from Git
_output/         Generated tables, figures, notebooks, and research outputs
dodo.py          PyDoit task definitions for the end-to-end pipeline
environment.yml  Conda environment specification
.env.example     Example local configuration without private credentials
```

## Analysis Code Map

| File | Purpose |
|---|---|
| `src/pull_optionmetrics.py` | Pull SPX option data from WRDS |
| `src/pull_zero_curve.py` | Pull the OptionMetrics zero-coupon curve |
| `src/pull_crsp_sp500.py` | Pull S&P 500 return data from CRSP |
| `src/clean_optionmetrics.py` | Clean and validate SPX option quotes |
| `src/clean_zero_curve.py` | Clean the zero-coupon curve |
| `src/clean_crsp_sp500.py` | Prepare S&P 500 total returns |
| `src/option_surface.py` | Build date-expiration option surfaces |
| `src/forward_prices.py` | Construct option-implied forward prices |
| `src/svix.py` | Compute SVIX and interpolate fixed horizons |
| `src/build_future_returns.py` | Construct future realized market returns |
| `src/table1.py` | Estimate Martin Table 1 regressions |
| `src/power_utility.py` | Replicate and update Figures 1 and 2 |
| `src/rolling_predictive_power.py` | Estimate rolling forecasting regressions |
| `src/horizon_comparison.py` | Compare forecasting performance across horizons |
| `src/regime_analysis.py` | Estimate market-regime regressions |
| `src/crisis_window_analysis.py` | Run crisis-window and leave-one-year-out tests |
| `src/forward_robustness.py` | Test sensitivity to forward-price convention |
| `dodo.py` | Define the end-to-end PyDoit task graph |
| `web/` | Read-only SVIX monitoring application |

## SVIX Monitor

The `web/` directory contains a local read-only dashboard built on top of the research pipeline outputs.

The monitor displays:

- the latest option-implied expected excess return;
- the current SVIX level and historical percentile;
- the current calm/elevated/stress regime;
- the historical SVIX series and selected market events; and
- the Table 1 regression results across samples and horizons.

The application does not estimate a separate model and does not contact WRDS. It reads the same generated artifacts used by the replication pipeline, which keeps the research results and the dashboard consistent.

The current local extract extends through **August 29, 2025**. The monitor should therefore be interpreted as a view of the latest available research dataset rather than a real-time market-data application.

To run the monitor, first generate the required pipeline outputs, then start the backend:

```bash
pip install -r web/backend/requirements.txt
PYTHONPATH=web/backend uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```bash
cd web/frontend
npm install
npm run dev
```

See [`web/README.md`](web/README.md) for additional details.

## Quick Start

### Prerequisites

You will need:

- Conda or Mamba;
- Git;
- the Python dependencies specified by the project environment; and
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

On macOS or Linux:

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
doit list --all
```

### Run Tests

```bash
python -m pytest -q tests
```

The final validated project currently contains **17 passing tests**.

### Format and Lint Python Code

```bash
ruff format .
ruff check --select I --fix .
ruff check . --fix
```

## Data and Output Storage

- `_data/` contains licensed raw and intermediate data that can be recreated locally. It is excluded from Git.
- `_output/` contains generated tables, figures, notebooks, and selected research outputs.
- `data_manual/` is reserved for small manually maintained inputs.
- `.env` contains local paths and credentials and must never be tracked.
- `.env.example` documents the expected configuration without containing private information.

## Reproducibility

The repository is designed so that a WRDS-authorized user can recreate the analysis from source code.

Key reproducibility practices include:

- raw licensed WRDS data are excluded from Git;
- generated research outputs are produced from code rather than edited manually;
- methodology is separated into focused source modules;
- the project is automated with PyDoit;
- important calculations are covered by unit and replication-tolerance tests; and
- implementation choices and robustness checks are documented in the repository.

## Project Status

The replication, updated sample, empirical extensions, robustness analysis, notebook, and SVIX Monitor are complete.

The final submission version is tagged:

`project-final-v1`
