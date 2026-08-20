# P06 – Martin (2025): Information in Derivatives Markets — Forecasting Prices with Prices

## About This Project

This project replicates and extends the empirical analysis in Ian W. R. Martin's 2025 paper, *Information in Derivatives Markets: Forecasting Prices with Prices*.

Using OptionMetrics IvyDB US and CRSP data accessed through WRDS, the project constructs daily SVIX measures for the S&P 500 at 1-, 3-, 6-, and 12-month horizons, replicates Martin's main forecasting results and power-utility figures, and extends the analysis through the latest available 2025 data.

The project is organized as a reproducible research pipeline. Raw licensed data are pulled from WRDS, cleaned into tidy intermediate datasets, transformed into option surfaces and fixed-horizon SVIX measures, joined to future S&P 500 total returns, and passed through the replication, extension, notebook, and report stages.

## Research Question

The main extension asks:

> **How robust is SVIX as a forecasting signal for future S&P 500 excess returns?**

We study this along four dimensions:

1. **Time:** Does the forecasting relationship remain stable through the sample?
2. **Horizon:** Which of the 1-, 3-, 6-, and 12-month horizons performs best?
3. **Market conditions:** Is SVIX more informative in calm or stressed markets?
4. **Specification robustness:** Are the results sensitive to crisis observations or the forward-price convention used in SVIX construction?

## Key Findings

The replication closely matches Martin's published return-predictability results through December 2022.

For the original 1996–2022 sample:

| Horizon | Replicated Beta | Published Beta | Replicated R² | Published R² |
|---|---:|---:|---:|---:|
| 1 month | 1.425 | 1.569 | 1.13% | 1.30% |
| 3 months | 1.382 | 1.439 | 2.11% | 2.20% |
| 6 months | 2.432 | 2.418 | 7.04% | 6.84% |
| 12 months | 2.026 | 1.858 | 5.66% | 4.73% |

Extending the sample beyond 2022 shows that the SVIX-return relationship remains positive at all four horizons. In the January 2023 through latest usable subsample:

| Horizon | Beta | Newey–West t-stat | R² |
|---|---:|---:|---:|
| 1 month | 8.655 | 3.56 | 11.15% |
| 3 months | 9.903 | 4.70 | 22.75% |
| 6 months | 6.151 | 1.89 | 14.68% |
| 12 months | 6.221 | 3.39 | 20.23% |

The 12-month post-2022 result should be interpreted cautiously because the short updated sample contains only about two independent annual periods after accounting for overlapping returns.

The horizon comparison shows that the strongest in-sample relationship does not always translate into short-horizon out-of-sample forecasting performance. The 6-month horizon has the strongest out-of-sample R² at approximately 6.3%, the 12-month horizon remains positive at approximately 2.8%, and the 1- and 3-month horizons are negative out of sample.

The regime analysis shows that predictive power is materially stronger at the 6- and 12-month horizons during high-volatility and high-SVIX states than during calm markets. Rolling regressions also show that the forecasting coefficient changes substantially through time.

Crisis-window and forward-price robustness checks support the same conclusion. Removing the 2008–2009 crisis window does not eliminate the relationship, and replacing the baseline forward-price construction with the OptionMetrics forward leaves the Table 1 coefficients essentially unchanged.

## Data Sources

All licensed market data are accessed through WRDS.

### OptionMetrics IvyDB US

S&P 500 index option data for `secid = 108105`, including:

- observation date;
- expiration date;
- strike price;
- put/call indicator;
- bid and ask prices;
- underlying S&P 500 index level; and
- contract identifiers and data-quality fields.

### OptionMetrics Zero-Coupon Yield Curve

Used to construct maturity-matched discount factors and gross risk-free returns.

### CRSP

Used for the daily S&P 500 total-return series and the construction of horizon-matched future excess returns.

Raw licensed OptionMetrics and CRSP data are intentionally excluded from GitHub.

## Methodology

### Data Cleaning

Data cleaning is separated from analysis code. The pipeline removes invalid or crossed option quotes, constructs midpoint prices, checks contract metadata, validates expirations and strikes, and preserves diagnostics on data coverage and option surfaces.

### Forward Prices and SVIX

For each date and expiration, the cleaned option surface is matched to the zero-coupon curve and a forward price is constructed. The forward determines the out-of-the-money put/call boundary used in the SVIX integral.

SVIX is computed from Equation (19) in Martin (2025) by numerically integrating out-of-the-money put and call prices across strikes. Expiration-level values are then interpolated to fixed 1-, 3-, 6-, and 12-month horizons.

### Forecasting Regressions

Future S&P 500 total returns are constructed from CRSP and converted to excess returns using horizon-matched risk-free returns.

Table 1 uses Newey–West standard errors with:

| Horizon | Newey–West lags |
|---|---:|
| 1 month | 21 |
| 3 months | 65 |
| 6 months | 130 |
| 12 months | 260 |

### Power-Utility Equity Premia

Figures 1 and 2 are replicated for risk aversion values \(\gamma = 1, 2, 3\), with separate replication-sample and updated figures.

## Empirical Extensions

The project includes:

- five-year rolling predictive regressions;
- in-sample and out-of-sample horizon comparisons;
- ex-ante market-regime analysis;
- 2008–2009 crisis-window exclusion;
- leave-one-year-out sensitivity analysis; and
- forward-price robustness using the OptionMetrics forward.

## Repository Organization

```text
assets/          Non-generated images and presentation assets
data_manual/     Small manually maintained inputs
docs_src/        Chartbook source and documentation
reports/         Final LaTeX report source
src/             Data pulls, cleaning, SVIX construction, analysis, tests, and notebook
web/             Read-only SVIX Monitor web application
_data/           Raw and intermediate licensed data generated locally; excluded from Git
_output/         Generated tables, figures, notebook HTML, LaTeX fragments, and PDF report
dodo.py          PyDoit task graph for the end-to-end pipeline
environment.yml  Conda environment specification
requirements.txt Python package requirements
.env.example     Example local configuration without credentials
```

## Analysis Code Map

| File | Purpose |
|---|---|
| `src/pull_optionmetrics.py` | Pull SPX option data from WRDS |
| `src/pull_zero_curve.py` | Pull the OptionMetrics zero-coupon curve |
| `src/pull_crsp_sp500.py` | Pull S&P 500 total returns from CRSP |
| `src/clean_optionmetrics.py` | Clean and validate SPX option quotes |
| `src/clean_zero_curve.py` | Clean the zero-coupon curve |
| `src/clean_crsp_sp500.py` | Prepare S&P 500 total returns |
| `src/option_surface.py` | Build date-expiration option surfaces |
| `src/forward_prices.py` | Construct forward prices and diagnostics |
| `src/svix.py` | Compute expiration-level and fixed-horizon SVIX |
| `src/build_future_returns.py` | Construct future realized market and excess returns |
| `src/table1.py` | Estimate Martin Table 1 regressions |
| `src/power_utility.py` | Replicate and update Figures 1 and 2 |
| `src/rolling_predictive_power.py` | Estimate rolling forecasting regressions |
| `src/horizon_comparison.py` | Compare forecasting performance across horizons |
| `src/regime_analysis.py` | Estimate market-regime regressions |
| `src/crisis_window_analysis.py` | Run crisis-window and leave-one-year-out tests |
| `src/forward_robustness.py` | Test sensitivity to forward-price convention |
| `src/svix_summary_stats.py` | Generate SVIX summary statistics |
| `src/plot_svix_series.py` | Generate report-ready SVIX figures |
| `src/build_latex_tables.py` | Generate LaTeX table fragments from pipeline CSVs |
| `src/01_martin_replication.ipynb.py` | Jupytext source for the guided-tour notebook |
| `src/01_martin_replication.ipynb` | Executed Jupyter notebook deliverable |
| `reports/martin_replication_report.tex` | Final LaTeX report source |
| `dodo.py` | End-to-end PyDoit automation |

## Jupyter Notebook

The repository includes a guided-tour notebook:

```text
src/01_martin_replication.ipynb
```

It walks through:

- data coverage;
- cleaning and surface diagnostics;
- fixed-horizon SVIX;
- summary statistics;
- Table 1 replication;
- updated results;
- power-utility figures;
- horizon comparison;
- rolling analysis;
- regime analysis;
- crisis robustness; and
- forward-price robustness.

The notebook is generated from the paired Jupytext source:

```text
src/01_martin_replication.ipynb.py
```

and is rebuilt automatically by PyDoit.

## Final LaTeX Report

The final report source is:

```text
reports/martin_replication_report.tex
```

The report contains the replication, updated results, summary statistics, project extensions, robustness analysis, discussion of data sources, implementation challenges, and conclusions.

Numerical tables are not typed manually into the report. `src/build_latex_tables.py` reads the CSV outputs generated by the research pipeline and writes the LaTeX table fragments used by the final report.

The compiled report is generated at:

```text
_output/martin_replication_report.pdf
```

## SVIX Monitor

The `web/` directory contains an optional read-only SVIX Monitor built on the same pipeline outputs.

It displays:

- the latest available option-implied equity premium;
- the current SVIX level and historical percentile;
- current market regime;
- historical SVIX;
- selected market events; and
- Table 1 regression results.

The monitor does not estimate a separate model and does not contact WRDS. It reads the same generated pipeline artifacts used by the research project.

The current local research extract extends through August 29, 2025. The monitor should therefore be viewed as a research interface to the latest available dataset rather than as a real-time market-data application.

To run it:

```bash
pip install -r web/backend/requirements.txt
PYTHONPATH=web/backend uvicorn app.main:app --reload --port 8000
```

In another terminal:

```bash
cd web/frontend
npm install
npm run dev
```

See [`web/README.md`](web/README.md) for more detail.

## Quick Start

### Prerequisites

You will need:

- Git;
- Conda or Mamba;
- authorized WRDS access to OptionMetrics IvyDB US and CRSP;
- the Python dependencies defined by `environment.yml` / `requirements.txt`; and
- a LaTeX installation such as MacTeX or TeX Live with `latexmk` or `pdflatex`.

A fresh end-to-end run requires WRDS access because licensed raw data are not distributed with the repository.

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

Add only local configuration and credentials to `.env`.

Never commit `.env` or WRDS credentials.

On macOS or Linux:

```bash
set -a
source .env
set +a
```

### Run the Full Pipeline

From the repository root:

```bash
doit
```

The default PyDoit pipeline:

1. creates configured directories;
2. pulls OptionMetrics and CRSP data;
3. cleans the licensed data;
4. constructs forward prices;
5. computes SVIX;
6. constructs future S&P 500 returns;
7. reproduces and updates Table 1;
8. validates replication tolerances;
9. reproduces and updates the power-utility figures;
10. runs rolling, horizon, regime, crisis, and forward robustness analyses;
11. generates SVIX summary statistics and figures;
12. builds and executes the Jupyter notebook;
13. generates LaTeX tables;
14. compiles the final PDF report; and
15. runs the unit and replication tests.

List all tasks with:

```bash
doit list --all
```

Individual stages can also be run directly, for example:

```bash
doit table1
doit run_notebooks
doit latex_tables
doit latex_report
doit run_pytest
```

## Tests

Run the test suite directly with:

```bash
python -m pytest -q tests
```

The final validated project contains 17 passing tests.

## Data and Output Storage

- `_data/` contains licensed raw and intermediate data generated locally and is excluded from Git.
- `_output/` contains generated tables, figures, notebook HTML, LaTeX fragments, and the compiled report.
- `.env` contains local configuration and credentials and must never be committed.
- `.env.example` documents the expected configuration without credentials.

## Reproducibility

The repository is designed so that a WRDS-authorized user can recreate the analysis from source code.

Key reproducibility practices include:

- licensed raw data are excluded from Git;
- cleaning and analysis logic are separated;
- generated research outputs are produced from code rather than edited manually;
- numerical LaTeX tables are generated from pipeline CSV outputs;
- the guided-tour notebook is generated and executed automatically;
- the final PDF report is compiled automatically;
- the project is orchestrated end-to-end with PyDoit; and
- important calculations are covered by unit and replication-tolerance tests.
