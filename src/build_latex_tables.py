"""Build curated LaTeX table fragments for the Martin (2025) final report.

All numerical values come from CSV artifacts produced by the research
pipeline. This module only selects, reshapes, labels, and formats those
generated results for presentation in the LaTeX report.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from settings import config


HORIZON_ORDER = ["1m", "3m", "6m", "12m"]


def _paths() -> tuple[Path, Path]:
    """Return the analysis-output directory and generated LaTeX-table directory."""
    output_dir = Path(config("OUTPUT_DIR"))
    table_dir = output_dir / "latex_tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    return output_dir, table_dir


def _read(output_dir: Path, filename: str) -> pd.DataFrame:
    """Read a required generated CSV artifact."""
    path = output_dir / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Missing required report input: {path}. "
            "Run the corresponding analysis task before building the report."
        )
    return pd.read_csv(path)


def _require(df: pd.DataFrame, columns: list[str], filename: str) -> None:
    """Raise a clear error if a report input schema changes unexpectedly."""
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(
            f"{filename} is missing required columns {missing}. "
            f"Available columns: {df.columns.tolist()}"
        )


def _sort_horizon(df: pd.DataFrame) -> pd.DataFrame:
    """Sort horizon rows as 1m, 3m, 6m, 12m."""
    result = df.copy()
    result["_horizon_order"] = pd.Categorical(
        result["horizon"], categories=HORIZON_ORDER, ordered=True
    )
    sort_cols = ["_horizon_order"]
    if "sample" in result.columns:
        # Preserve the source file's sample ordering while sorting within sample.
        sample_order = list(dict.fromkeys(result["sample"].astype(str)))
        result["_sample_order"] = pd.Categorical(
            result["sample"].astype(str), categories=sample_order, ordered=True
        )
        sort_cols = ["_sample_order", "_horizon_order"]
    result = result.sort_values(sort_cols).drop(
        columns=[c for c in ["_sample_order", "_horizon_order"] if c in result.columns]
    )
    return result.reset_index(drop=True)


def _num(value: object, decimals: int = 3) -> str:
    """Format a numeric statistic."""
    return "--" if pd.isna(value) else f"{float(value):.{decimals}f}"


def _count(value: object) -> str:
    """Format an observation count."""
    return "--" if pd.isna(value) else f"{int(round(float(value))):d}"


def _pct(value: object, decimals: int = 2) -> str:
    """Format a decimal ratio as a percentage."""
    return "--" if pd.isna(value) else f"{100.0 * float(value):.{decimals}f}"


def _yes_no(value: object) -> str:
    """Format a boolean-style value as Yes or No."""
    if pd.isna(value):
        return "--"
    if isinstance(value, str):
        return "Yes" if value.strip().lower() in {"true", "1", "yes"} else "No"
    return "Yes" if bool(value) else "No"


def _human(value: object) -> str:
    """Convert machine-readable labels to presentation text."""
    return "--" if pd.isna(value) else str(value).replace("_", " ").title()


def _dte_label(value: object) -> str:
    """Convert labels such as '[0, 45)' to a LaTeX-safe readable range."""
    if pd.isna(value):
        return "--"
    text = str(value).strip()
    match = re.fullmatch(r"[\[\(]\s*(\d+)\s*,\s*(\d+)\s*[\)\]]", text)
    if match:
        lo, hi = match.groups()
        return f"{lo}--{hi} days"
    return text


def _write(table: pd.DataFrame, destination: Path) -> None:
    """Write one booktabs tabular fragment for inclusion in the report."""
    destination.write_text(
        table.to_latex(
            index=False,
            escape=True,
            na_rep="--",
            multicolumn=False,
            bold_rows=False,
        ),
        encoding="utf-8",
    )


def _table1_replication(output_dir: Path) -> pd.DataFrame:
    """Build the original-sample Table 1 replication summary."""
    filename = "table1_replication.csv"
    df = _read(output_dir, filename)
    cols = [
        "sample", "horizon", "nobs", "alpha", "alpha_se_nw",
        "beta", "beta_se_nw", "beta_t_nw", "r2",
    ]
    _require(df, cols, filename)
    df = _sort_horizon(df)
    return pd.DataFrame({
        "Sample": df["sample"],
        "Horizon": df["horizon"],
        "N": df["nobs"].map(_count),
        "Alpha": df["alpha"].map(_num),
        "NW SE Alpha": df["alpha_se_nw"].map(_num),
        "Beta": df["beta"].map(_num),
        "NW SE Beta": df["beta_se_nw"].map(_num),
        "NW t-stat Beta": df["beta_t_nw"].map(_num),
        "R-squared (%)": df["r2"].map(_pct),
    })


def _published_comparison(output_dir: Path) -> pd.DataFrame:
    """Reshape the 31-column published-comparison CSV into a compact table."""
    filename = "table1_published_comparison.csv"
    df = _read(output_dir, filename)
    required = ["horizon"]
    for suffix in ("1996_2022", "2012_2022"):
        required.extend([
            f"alpha_rep_{suffix}", f"alpha_pub_{suffix}",
            f"beta_rep_{suffix}", f"beta_pub_{suffix}",
            f"r2_rep_{suffix}", f"r2_pub_{suffix}",
        ])
    _require(df, required, filename)
    df = _sort_horizon(df)

    parts = []
    for label, suffix in (
        ("1996--2022", "1996_2022"),
        ("2012--2022", "2012_2022"),
    ):
        parts.append(pd.DataFrame({
            "Sample": label,
            "Horizon": df["horizon"],
            "Alpha Rep.": df[f"alpha_rep_{suffix}"].map(_num),
            "Alpha Pub.": df[f"alpha_pub_{suffix}"].map(_num),
            "Beta Rep.": df[f"beta_rep_{suffix}"].map(_num),
            "Beta Pub.": df[f"beta_pub_{suffix}"].map(_num),
            "R-squared Rep. (%)": df[f"r2_rep_{suffix}"].map(_pct),
            "R-squared Pub. (%)": df[f"r2_pub_{suffix}"].map(_pct),
        }))
    return pd.concat(parts, ignore_index=True)


def _table1_updated(output_dir: Path) -> pd.DataFrame:
    """Build the full updated-sample regression table."""
    filename = "table1_updated.csv"
    df = _read(output_dir, filename)
    cols = ["horizon", "last_usable_date", "nobs", "alpha", "beta", "beta_t_nw", "r2"]
    _require(df, cols, filename)
    df = _sort_horizon(df)
    return pd.DataFrame({
        "Horizon": df["horizon"],
        "Last usable date": df["last_usable_date"].astype(str),
        "N": df["nobs"].map(_count),
        "Alpha": df["alpha"].map(_num),
        "Beta": df["beta"].map(_num),
        "NW t-stat Beta": df["beta_t_nw"].map(_num),
        "R-squared (%)": df["r2"].map(_pct),
    })


def _table1_post2022(output_dir: Path) -> pd.DataFrame:
    """Build the post-2022 regression table with inference diagnostics."""
    filename = "table1_post2022.csv"
    df = _read(output_dir, filename)
    cols = [
        "horizon", "last_usable_date", "nobs", "beta", "beta_se_nw",
        "beta_t_nw", "r2", "independent_periods", "inference_reliable",
    ]
    _require(df, cols, filename)
    df = _sort_horizon(df)
    return pd.DataFrame({
        "Horizon": df["horizon"],
        "Last usable date": df["last_usable_date"].astype(str),
        "N": df["nobs"].map(_count),
        "Beta": df["beta"].map(_num),
        "NW SE Beta": df["beta_se_nw"].map(_num),
        "NW t-stat Beta": df["beta_t_nw"].map(_num),
        "R-squared (%)": df["r2"].map(_pct),
        "Independent periods": df["independent_periods"].map(lambda x: _num(x, 2)),
        "Reliable inference": df["inference_reliable"].map(_yes_no),
    })


def _svix_summary(output_dir: Path) -> pd.DataFrame:
    """Build the full-sample SVIX descriptive-statistics table."""
    filename = "svix_summary_stats.csv"
    df = _read(output_dir, filename)
    cols = ["sample", "measure", "horizon", "mean", "std", "p5", "p50", "p95", "max", "n"]
    _require(df, cols, filename)
    df = df[
        (df["sample"].astype(str).str.lower() == "full")
        & (df["measure"].astype(str).str.lower() == "svix")
    ].copy()
    if df.empty:
        raise ValueError("No rows with sample='full' and measure='svix' were found.")
    df = _sort_horizon(df)
    return pd.DataFrame({
        "Horizon": df["horizon"],
        "Mean (%)": df["mean"].map(lambda x: _num(x, 2)),
        "Std. dev. (%)": df["std"].map(lambda x: _num(x, 2)),
        "5th pct. (%)": df["p5"].map(lambda x: _num(x, 2)),
        "Median (%)": df["p50"].map(lambda x: _num(x, 2)),
        "95th pct. (%)": df["p95"].map(lambda x: _num(x, 2)),
        "Max (%)": df["max"].map(lambda x: _num(x, 2)),
        "N": df["n"].map(_count),
    })


def _horizon_comparison(output_dir: Path) -> pd.DataFrame:
    """Build the in-sample versus out-of-sample horizon table."""
    filename = "horizon_comparison.csv"
    df = _read(output_dir, filename)
    cols = [
        "horizon", "nobs", "in_sample_r2", "correlation",
        "oos_nobs", "oos_r2", "oos_rmse", "oos_mae",
    ]
    _require(df, cols, filename)
    df = _sort_horizon(df)
    return pd.DataFrame({
        "Horizon": df["horizon"],
        "In-sample N": df["nobs"].map(_count),
        "In-sample R-squared (%)": df["in_sample_r2"].map(_pct),
        "Correlation": df["correlation"].map(_num),
        "OOS N": df["oos_nobs"].map(_count),
        "OOS R-squared (%)": df["oos_r2"].map(_pct),
        "OOS RMSE": df["oos_rmse"].map(_num),
        "OOS MAE": df["oos_mae"].map(_num),
    })


def _regime_analysis(output_dir: Path) -> pd.DataFrame:
    """Build the regime-specific forecasting table."""
    filename = "regime_analysis.csv"
    df = _read(output_dir, filename)
    cols = ["horizon", "regime_type", "regime", "nobs", "beta", "beta_t_nw", "r2"]
    _require(df, cols, filename)
    df = _sort_horizon(df)
    return pd.DataFrame({
        "Horizon": df["horizon"],
        "Regime type": df["regime_type"].map(_human),
        "Regime": df["regime"].map(_human),
        "N": df["nobs"].map(_count),
        "Beta": df["beta"].map(_num),
        "NW t-stat Beta": df["beta_t_nw"].map(_num),
        "R-squared (%)": df["r2"].map(_pct),
    })


def _crisis_window(output_dir: Path) -> pd.DataFrame:
    """Build the crisis-window robustness table."""
    filename = "crisis_window_analysis.csv"
    df = _read(output_dir, filename)
    cols = [
        "horizon", "beta_full", "beta_ex_crisis", "beta_change",
        "r2_full", "r2_ex_crisis", "nobs_full", "nobs_ex_crisis",
        "crisis_obs_dropped",
    ]
    _require(df, cols, filename)
    df = _sort_horizon(df)
    return pd.DataFrame({
        "Horizon": df["horizon"],
        "Beta full": df["beta_full"].map(_num),
        "Beta ex-crisis": df["beta_ex_crisis"].map(_num),
        "Beta change": df["beta_change"].map(_num),
        "R-squared full (%)": df["r2_full"].map(_pct),
        "R-squared ex-crisis (%)": df["r2_ex_crisis"].map(_pct),
        "N full": df["nobs_full"].map(_count),
        "N ex-crisis": df["nobs_ex_crisis"].map(_count),
        "Crisis obs. dropped": df["crisis_obs_dropped"].map(_count),
    })


def _forward_discrepancy(output_dir: Path) -> pd.DataFrame:
    """Build the forward-price discrepancy summary by DTE bucket."""
    filename = "forward_price_discrepancy.csv"
    df = _read(output_dir, filename)
    cols = [
        "dte_bucket", "n", "mean_rel_diff_bp",
        "median_abs_rel_diff_bp", "p95_abs_rel_diff_bp",
    ]
    _require(df, cols, filename)
    return pd.DataFrame({
        "DTE bucket": df["dte_bucket"].map(_dte_label),
        "N": df["n"].map(_count),
        "Mean diff. (bp)": df["mean_rel_diff_bp"].map(lambda x: _num(x, 2)),
        "Median abs. diff. (bp)": df["median_abs_rel_diff_bp"].map(lambda x: _num(x, 2)),
        "95th pct. abs. diff. (bp)": df["p95_abs_rel_diff_bp"].map(lambda x: _num(x, 2)),
    })


def _forward_robustness(output_dir: Path) -> pd.DataFrame:
    """Build the Table 1 comparison across forward-price conventions."""
    filename = "forward_robustness_table1.csv"
    df = _read(output_dir, filename)
    cols = [
        "horizon", "beta_parity_forward", "beta_om_forward", "beta_change",
        "r2_parity_forward", "r2_om_forward", "nobs_parity", "nobs_om",
    ]
    _require(df, cols, filename)
    df = _sort_horizon(df)
    return pd.DataFrame({
        "Horizon": df["horizon"],
        "Beta parity": df["beta_parity_forward"].map(_num),
        "Beta OptionMetrics": df["beta_om_forward"].map(_num),
        "Beta change": df["beta_change"].map(lambda x: _num(x, 6)),
        "R-squared parity (%)": df["r2_parity_forward"].map(_pct),
        "R-squared OptionMetrics (%)": df["r2_om_forward"].map(_pct),
        "N parity": df["nobs_parity"].map(_count),
        "N OptionMetrics": df["nobs_om"].map(_count),
    })


def build_latex_tables() -> list[Path]:
    """Generate every curated LaTeX table fragment used by the final report."""
    output_dir, table_dir = _paths()
    builders = [
        ("table1_replication.tex", _table1_replication),
        ("table1_published_comparison.tex", _published_comparison),
        ("table1_updated.tex", _table1_updated),
        ("table1_post2022.tex", _table1_post2022),
        ("svix_summary_stats.tex", _svix_summary),
        ("horizon_comparison.tex", _horizon_comparison),
        ("regime_analysis.tex", _regime_analysis),
        ("crisis_window_analysis.tex", _crisis_window),
        ("forward_price_discrepancy.tex", _forward_discrepancy),
        ("forward_robustness_table1.tex", _forward_robustness),
    ]

    written: list[Path] = []
    for filename, builder in builders:
        destination = table_dir / filename
        _write(builder(output_dir), destination)
        written.append(destination)
    return written


if __name__ == "__main__":
    for path in build_latex_tables():
        print(path)