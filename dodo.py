"""PyDoit pipeline for the Martin (2025) replication and extensions."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

from doit.tools import config_changed

sys.path.insert(1, "./src/")
from settings import config

DOIT_CONFIG = {
    "backend": "sqlite3",
    "dep_file": "./.doit-db.sqlite",
    "default_tasks": [
        "config",
        "pull_martin_data",
        "clean_martin_data",
        "forward_prices",
        "svix",
        "future_returns",
        "table1",
        "replication_validation",
        "power_utility",
        "rolling_predictive_power",
        "horizon_comparison",
        "regime_analysis",
        "svix_deliverables",
        "crisis_window_analysis",
        "forward_robustness",
        "run_notebooks",
        "latex_tables",
        "latex_report",
        "run_pytest",
    ],
}

DATA_DIR = Path(config("DATA_DIR"))
OUTPUT_DIR = Path(config("OUTPUT_DIR"))

LATEX_TABLE_DIR = OUTPUT_DIR / "latex_tables"
LATEX_TABLE_TARGETS = [
    LATEX_TABLE_DIR / "table1_replication.tex",
    LATEX_TABLE_DIR / "table1_published_comparison.tex",
    LATEX_TABLE_DIR / "table1_updated.tex",
    LATEX_TABLE_DIR / "table1_post2022.tex",
    LATEX_TABLE_DIR / "svix_summary_stats.tex",
    LATEX_TABLE_DIR / "horizon_comparison.tex",
    LATEX_TABLE_DIR / "regime_analysis.tex",
    LATEX_TABLE_DIR / "crisis_window_analysis.tex",
    LATEX_TABLE_DIR / "forward_price_discrepancy.tex",
    LATEX_TABLE_DIR / "forward_robustness_table1.tex",
]
LATEX_REPORT = OUTPUT_DIR / "martin_replication_report.pdf"

os.environ["PYDEVD_DISABLE_FILE_VALIDATION"] = "1"


def _date_setting(preferred: str, fallback: str, default: str) -> str:
    """Resolve a date setting from project-specific, generic, then default values."""
    return os.getenv(preferred, os.getenv(fallback, default))


def jupyter_execute_notebook(notebook_path: Path) -> str:
    """Return the command that executes a generated notebook in place."""
    return (
        "jupyter nbconvert --execute --to notebook "
        "--ClearMetadataPreprocessor.enabled=True "
        f"--inplace {notebook_path}"
    )


def jupyter_to_html(notebook_path: Path, output_dir: Path = OUTPUT_DIR) -> str:
    """Return the command that exports an executed notebook to HTML."""
    return f"jupyter nbconvert --to html --output-dir={output_dir} {notebook_path}"


def _compile_latex_report() -> None:
    """Compile the final LaTeX report with latexmk or a pdflatex fallback."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report = "martin_replication_report.tex"
    outdir = "../_output"

    latexmk = shutil.which("latexmk")
    if latexmk:
        subprocess.run(
            [
                latexmk,
                "-pdf",
                "-interaction=nonstopmode",
                "-halt-on-error",
                f"-outdir={outdir}",
                report,
            ],
            cwd="reports",
            check=True,
        )
        return

    pdflatex = shutil.which("pdflatex")
    if pdflatex:
        cmd = [
            pdflatex,
            "-interaction=nonstopmode",
            "-halt-on-error",
            f"-output-directory={outdir}",
            report,
        ]
        subprocess.run(cmd, cwd="reports", check=True)
        subprocess.run(cmd, cwd="reports", check=True)
        return

    raise RuntimeError(
        "A LaTeX compiler is required to build the final report. "
        "Install latexmk (preferred) or pdflatex and rerun `doit latex_report`."
    )


def task_config():
    """Create configured data and output directories."""
    return {
        "actions": ["python ./src/settings.py"],
        "targets": [DATA_DIR, OUTPUT_DIR],
        "file_dep": ["./src/settings.py"],
        "clean": [],
    }


def task_pull_martin_data():
    """Pull OptionMetrics SPX options, zero curve, and CRSP total returns."""
    option_signature = {
        "start": _date_setting("P06_OPTION_START_DATE", "P06_START_DATE", "1996-01-01"),
        "end": _date_setting(
            "P06_OPTION_END_DATE", "P06_END_DATE", date.today().isoformat()
        ),
        "library": os.getenv("P06_OPTION_LIBRARY", "optionm_all"),
        "secid": os.getenv("P06_SPX_SECID", "108105"),
    }
    crsp_signature = {
        "start": _date_setting("P06_CRSP_START_DATE", "P06_START_DATE", "1996-01-01"),
        "end": _date_setting(
            "P06_CRSP_END_DATE", "P06_END_DATE", date.today().isoformat()
        ),
        "library": os.getenv("P06_CRSP_LIBRARY", "crsp"),
    }

    yield {
        "name": "optionmetrics",
        "actions": ["python ./src/pull_optionmetrics.py"],
        "targets": [
            DATA_DIR / "optionmetrics_spx_raw_manifest.csv",
            DATA_DIR / "optionmetrics_spx_underlying_raw.parquet",
        ],
        "file_dep": [
            "./src/settings.py",
            "./src/wrds_helpers.py",
            "./src/martin_spec.py",
            "./src/pull_optionmetrics.py",
        ],
        "uptodate": [config_changed(option_signature)],
        "clean": True,
    }
    yield {
        "name": "zero_curve",
        "actions": ["python ./src/pull_zero_curve.py"],
        "targets": [DATA_DIR / "optionmetrics_zero_curve_raw.parquet"],
        "file_dep": [
            "./src/settings.py",
            "./src/wrds_helpers.py",
            "./src/pull_zero_curve.py",
        ],
        "uptodate": [config_changed(option_signature)],
        "clean": True,
    }
    yield {
        "name": "crsp_sp500",
        "actions": ["python ./src/pull_crsp_sp500.py"],
        "targets": [DATA_DIR / "crsp_sp500_daily_raw.parquet"],
        "file_dep": [
            "./src/settings.py",
            "./src/wrds_helpers.py",
            "./src/pull_crsp_sp500.py",
        ],
        "uptodate": [config_changed(crsp_signature)],
        "clean": True,
    }


def task_clean_martin_data():
    """Clean the raw licensed datasets into tidy analysis inputs."""
    yield {
        "name": "optionmetrics",
        "actions": ["python ./src/clean_optionmetrics.py"],
        "targets": [
            DATA_DIR / "optionmetrics_spx_clean_manifest.csv",
            DATA_DIR / "optionmetrics_cleaning_diagnostics.csv",
        ],
        "file_dep": [
            "./src/clean_optionmetrics.py",
            "./src/option_surface.py",
            "./src/martin_spec.py",
            DATA_DIR / "optionmetrics_spx_raw_manifest.csv",
            DATA_DIR / "optionmetrics_spx_underlying_raw.parquet",
        ],
        "task_dep": ["pull_martin_data:optionmetrics"],
        "clean": True,
    }
    yield {
        "name": "zero_curve",
        "actions": ["python ./src/clean_zero_curve.py"],
        "targets": [DATA_DIR / "optionmetrics_zero_curve_clean.parquet"],
        "file_dep": [
            "./src/clean_zero_curve.py",
            DATA_DIR / "optionmetrics_zero_curve_raw.parquet",
        ],
        "task_dep": ["pull_martin_data:zero_curve"],
        "clean": True,
    }
    yield {
        "name": "crsp_sp500",
        "actions": ["python ./src/clean_crsp_sp500.py"],
        "targets": [DATA_DIR / "crsp_sp500_daily_clean.parquet"],
        "file_dep": [
            "./src/clean_crsp_sp500.py",
            DATA_DIR / "crsp_sp500_daily_raw.parquet",
        ],
        "task_dep": ["pull_martin_data:crsp_sp500"],
        "clean": True,
    }


def task_forward_prices():
    """Construct expiration-level forward prices and surface diagnostics."""
    return {
        "actions": ["python ./src/forward_prices.py"],
        "targets": [
            DATA_DIR / "option_expiration_inputs.parquet",
            DATA_DIR / "forward_surface_diagnostics.csv",
        ],
        "file_dep": [
            "./src/forward_prices.py",
            "./src/clean_optionmetrics.py",
            "./src/option_surface.py",
            "./src/martin_spec.py",
            DATA_DIR / "optionmetrics_spx_clean_manifest.csv",
            DATA_DIR / "optionmetrics_zero_curve_clean.parquet",
        ],
        "task_dep": [
            "clean_martin_data:optionmetrics",
            "clean_martin_data:zero_curve",
        ],
        "clean": True,
    }


def task_svix():
    """Construct expiration-level and daily fixed-horizon SVIX."""
    return {
        "actions": ["python ./src/svix.py"],
        "targets": [
            DATA_DIR / "svix_by_expiration.parquet",
            DATA_DIR / "svix_daily.parquet",
        ],
        "file_dep": [
            "./src/svix.py",
            "./src/option_surface.py",
            "./src/martin_spec.py",
            DATA_DIR / "optionmetrics_spx_clean_manifest.csv",
            DATA_DIR / "option_expiration_inputs.parquet",
        ],
        "task_dep": ["forward_prices"],
        "clean": True,
    }


def task_future_returns():
    """Build future S&P 500 total and excess returns."""
    return {
        "actions": ["python ./src/build_future_returns.py"],
        "targets": [DATA_DIR / "future_sp500_returns.parquet"],
        "file_dep": [
            "./src/build_future_returns.py",
            "./src/martin_spec.py",
            DATA_DIR / "crsp_sp500_daily_clean.parquet",
            DATA_DIR / "optionmetrics_zero_curve_clean.parquet",
        ],
        "task_dep": [
            "clean_martin_data:crsp_sp500",
            "clean_martin_data:zero_curve",
        ],
        "clean": True,
    }


def task_table1():
    """Estimate Martin Table 1 on replication and updated samples."""
    return {
        "actions": ["python ./src/table1.py"],
        "targets": [
            OUTPUT_DIR / "table1_replication.csv",
            OUTPUT_DIR / "table1_published_comparison.csv",
            OUTPUT_DIR / "table1_updated.csv",
            OUTPUT_DIR / "table1_post2022.csv",
        ],
        "file_dep": [
            "./src/table1.py",
            DATA_DIR / "svix_daily.parquet",
            DATA_DIR / "future_sp500_returns.parquet",
        ],
        "task_dep": ["svix", "future_returns"],
        "clean": True,
    }


def task_replication_validation():
    """Validate replicated Table 1 values against documented tolerances."""
    return {
        "actions": ["python ./src/replication_validation.py"],
        "targets": [
            OUTPUT_DIR / "replication_tolerance_report.csv",
            OUTPUT_DIR / "replication_tolerance_summary.json",
        ],
        "file_dep": [
            "./src/replication_validation.py",
            OUTPUT_DIR / "table1_published_comparison.csv",
        ],
        "task_dep": ["table1"],
        "clean": True,
    }


def task_power_utility():
    """Replicate and update the power-utility equity-premium figures."""
    return {
        "actions": ["python ./src/power_utility.py"],
        "targets": [
            DATA_DIR / "power_utility_by_expiration.parquet",
            DATA_DIR / "power_utility_daily.parquet",
            OUTPUT_DIR / "figure1_power_utility_replication.png",
            OUTPUT_DIR / "figure2_power_utility_replication.png",
            OUTPUT_DIR / "figure1_power_utility_updated.png",
            OUTPUT_DIR / "figure2_power_utility_updated.png",
        ],
        "file_dep": [
            "./src/power_utility.py",
            "./src/clean_optionmetrics.py",
            "./src/forward_prices.py",
            "./src/martin_spec.py",
            "./src/option_surface.py",
            "./src/svix.py",
            DATA_DIR / "optionmetrics_spx_clean_manifest.csv",
            DATA_DIR / "option_expiration_inputs.parquet",
        ],
        "task_dep": ["forward_prices"],
        "clean": True,
    }


def task_rolling_predictive_power():
    """Estimate five-year rolling SVIX forecasting regressions."""
    return {
        "actions": ["python ./src/rolling_predictive_power.py"],
        "targets": [
            OUTPUT_DIR / "rolling_predictive_power.csv",
            OUTPUT_DIR / "rolling_predictive_beta.png",
        ],
        "file_dep": [
            "./src/rolling_predictive_power.py",
            DATA_DIR / "svix_daily.parquet",
            DATA_DIR / "future_sp500_returns.parquet",
        ],
        "task_dep": ["table1"],
        "clean": True,
    }


def task_horizon_comparison():
    """Compare in-sample and out-of-sample forecasting performance by horizon."""
    return {
        "actions": ["python ./src/horizon_comparison.py"],
        "targets": [
            OUTPUT_DIR / "horizon_comparison.csv",
            OUTPUT_DIR / "horizon_comparison.png",
        ],
        "file_dep": [
            "./src/horizon_comparison.py",
            DATA_DIR / "svix_daily.parquet",
            DATA_DIR / "future_sp500_returns.parquet",
        ],
        "task_dep": ["table1"],
        "clean": True,
    }


def task_regime_analysis():
    """Estimate ex-ante market-regime forecasting regressions."""
    return {
        "actions": ["python ./src/regime_analysis.py"],
        "targets": [
            OUTPUT_DIR / "regime_analysis.csv",
            OUTPUT_DIR / "regime_beta_comparison.png",
        ],
        "file_dep": [
            "./src/regime_analysis.py",
            DATA_DIR / "svix_daily.parquet",
            DATA_DIR / "future_sp500_returns.parquet",
        ],
        "task_dep": ["table1"],
        "clean": True,
    }


def task_svix_deliverables():
    """Generate SVIX summary statistics and report-ready SVIX figures."""
    return {
        "actions": [
            "python ./src/svix_summary_stats.py",
            "python ./src/plot_svix_series.py",
        ],
        "targets": [
            OUTPUT_DIR / "svix_summary_stats.csv",
            OUTPUT_DIR / "svix_series.png",
            OUTPUT_DIR / "svix_term_structure.png",
        ],
        "file_dep": [
            "./src/svix_summary_stats.py",
            "./src/plot_svix_series.py",
            "./src/martin_spec.py",
            DATA_DIR / "svix_daily.parquet",
        ],
        "task_dep": ["svix"],
        "clean": True,
    }


def task_crisis_window_analysis():
    """Quantify how far the published-sample slopes rest on 2008-2009."""
    return {
        "actions": ["python ./src/crisis_window_analysis.py"],
        "targets": [
            OUTPUT_DIR / "crisis_window_analysis.csv",
            OUTPUT_DIR / "crisis_leave_one_year_out.csv",
            OUTPUT_DIR / "crisis_leave_one_year_out.png",
        ],
        "file_dep": [
            "./src/crisis_window_analysis.py",
            "./src/table1.py",
            DATA_DIR / "svix_daily.parquet",
            DATA_DIR / "future_sp500_returns.parquet",
        ],
        "task_dep": ["table1"],
        "clean": True,
    }


def task_pull_optionmetrics_forwards():
    """Pull the OptionMetrics forward-price file used by the robustness check."""
    return {
        "actions": ["python ./src/pull_optionmetrics_forwards.py"],
        "targets": [DATA_DIR / "optionmetrics_spx_forwards_raw.parquet"],
        "file_dep": [
            "./src/settings.py",
            "./src/wrds_helpers.py",
            "./src/pull_optionmetrics.py",
            "./src/pull_optionmetrics_forwards.py",
        ],
        "clean": True,
    }


def task_forward_robustness():
    """Re-estimate Table 1 under the OptionMetrics forward convention."""
    return {
        "actions": ["python ./src/forward_robustness.py"],
        "targets": [
            DATA_DIR / "svix_daily_om_forward.parquet",
            OUTPUT_DIR / "forward_price_discrepancy.csv",
            OUTPUT_DIR / "forward_robustness_table1.csv",
            OUTPUT_DIR / "forward_robustness.png",
        ],
        "file_dep": [
            "./src/forward_robustness.py",
            "./src/svix.py",
            "./src/table1.py",
            DATA_DIR / "optionmetrics_spx_forwards_raw.parquet",
            DATA_DIR / "option_expiration_inputs.parquet",
            DATA_DIR / "svix_daily.parquet",
            DATA_DIR / "future_sp500_returns.parquet",
        ],
        "task_dep": ["table1", "pull_optionmetrics_forwards"],
        "clean": True,
    }


notebook_tasks = {
    "01_martin_replication.ipynb.py": {
        "path": "./src/01_martin_replication.ipynb.py",
        "file_dep": [
            DATA_DIR / "optionmetrics_cleaning_diagnostics.csv",
            DATA_DIR / "forward_surface_diagnostics.csv",
            OUTPUT_DIR / "table1_replication.csv",
            OUTPUT_DIR / "table1_published_comparison.csv",
            OUTPUT_DIR / "table1_updated.csv",
            OUTPUT_DIR / "table1_post2022.csv",
            OUTPUT_DIR / "replication_tolerance_report.csv",
            OUTPUT_DIR / "svix_summary_stats.csv",
            OUTPUT_DIR / "figure1_power_utility_replication.png",
            OUTPUT_DIR / "figure2_power_utility_replication.png",
            OUTPUT_DIR / "figure1_power_utility_updated.png",
            OUTPUT_DIR / "figure2_power_utility_updated.png",
            OUTPUT_DIR / "rolling_predictive_power.csv",
            OUTPUT_DIR / "rolling_predictive_beta.png",
            OUTPUT_DIR / "horizon_comparison.csv",
            OUTPUT_DIR / "horizon_comparison.png",
            OUTPUT_DIR / "regime_analysis.csv",
            OUTPUT_DIR / "regime_beta_comparison.png",
            OUTPUT_DIR / "crisis_window_analysis.csv",
            OUTPUT_DIR / "crisis_leave_one_year_out.csv",
            OUTPUT_DIR / "crisis_leave_one_year_out.png",
            OUTPUT_DIR / "forward_price_discrepancy.csv",
            OUTPUT_DIR / "forward_robustness_table1.csv",
            OUTPUT_DIR / "forward_robustness.png",
        ],
    },
}


def task_run_notebooks():
    """Build, execute, and export the guided-tour Jupyter notebook."""
    for notebook, details in notebook_tasks.items():
        pyfile = Path(details["path"])
        notebook_path = pyfile.with_suffix("")
        notebook_name = notebook_path.stem
        html_target = OUTPUT_DIR / f"{notebook_name}.html"

        yield {
            "name": notebook,
            "actions": [
                f"jupytext --to notebook --output {notebook_path} {pyfile}",
                jupyter_execute_notebook(notebook_path),
                jupyter_to_html(notebook_path),
            ],
            "file_dep": [pyfile, *details["file_dep"]],
            "targets": [notebook_path, html_target],
            "task_dep": [
                "table1",
                "replication_validation",
                "power_utility",
                "rolling_predictive_power",
                "horizon_comparison",
                "regime_analysis",
                "svix_deliverables",
                "crisis_window_analysis",
                "forward_robustness",
            ],
            # Keep the tracked .ipynb deliverable; only remove the generated HTML.
            "clean": [f"rm -f {html_target}"],
        }


def task_latex_tables():
    """Generate report-ready LaTeX table fragments from pipeline CSV outputs."""
    csv_inputs = [
        OUTPUT_DIR / "table1_replication.csv",
        OUTPUT_DIR / "table1_published_comparison.csv",
        OUTPUT_DIR / "table1_updated.csv",
        OUTPUT_DIR / "table1_post2022.csv",
        OUTPUT_DIR / "svix_summary_stats.csv",
        OUTPUT_DIR / "horizon_comparison.csv",
        OUTPUT_DIR / "regime_analysis.csv",
        OUTPUT_DIR / "crisis_window_analysis.csv",
        OUTPUT_DIR / "forward_price_discrepancy.csv",
        OUTPUT_DIR / "forward_robustness_table1.csv",
    ]
    return {
        "actions": ["python ./src/build_latex_tables.py"],
        "targets": LATEX_TABLE_TARGETS,
        "file_dep": ["./src/build_latex_tables.py", *csv_inputs],
        "task_dep": [
            "table1",
            "svix_deliverables",
            "horizon_comparison",
            "regime_analysis",
            "crisis_window_analysis",
            "forward_robustness",
        ],
        "clean": True,
    }


def task_latex_report():
    """Compile the final replication report from generated tables and figures."""
    figure_inputs = [
        OUTPUT_DIR / "figure1_power_utility_replication.png",
        OUTPUT_DIR / "figure2_power_utility_replication.png",
        OUTPUT_DIR / "figure1_power_utility_updated.png",
        OUTPUT_DIR / "figure2_power_utility_updated.png",
        OUTPUT_DIR / "svix_series.png",
        OUTPUT_DIR / "svix_term_structure.png",
        OUTPUT_DIR / "horizon_comparison.png",
        OUTPUT_DIR / "rolling_predictive_beta.png",
        OUTPUT_DIR / "regime_beta_comparison.png",
        OUTPUT_DIR / "crisis_leave_one_year_out.png",
        OUTPUT_DIR / "forward_robustness.png",
    ]
    return {
        "actions": [_compile_latex_report],
        "targets": [LATEX_REPORT],
        "file_dep": [
            "./reports/martin_replication_report.tex",
            *LATEX_TABLE_TARGETS,
            *figure_inputs,
        ],
        "task_dep": [
            "latex_tables",
            "replication_validation",
            "power_utility",
            "svix_deliverables",
            "horizon_comparison",
            "rolling_predictive_power",
            "regime_analysis",
            "crisis_window_analysis",
            "forward_robustness",
        ],
        "clean": True,
    }


def task_run_pytest():
    """Run the project unit and replication tests."""
    test_output = OUTPUT_DIR / "pytest_results.xml"
    return {
        "actions": [f"python -m pytest -q tests --junitxml={test_output}"],
        "targets": [test_output],
        "file_dep": [
            "./tests/conftest.py",
            "./tests/test_martin_replication.py",
            "./src/option_surface.py",
            "./src/forward_prices.py",
            "./src/svix.py",
            "./src/build_future_returns.py",
            "./src/power_utility.py",
        ],
        "clean": True,
    }


def task_build_chartbook_site():
    """Build the optional Chartbook site."""
    return {
        "actions": ["chartbook build -f"],
        "file_dep": [
            "./README.md",
            "./chartbook.toml",
            "./src/01_martin_replication.ipynb.py",
        ],
        "task_dep": ["run_notebooks"],
        "clean": True,
    }