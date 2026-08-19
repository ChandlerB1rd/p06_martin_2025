import type { EChartsOption } from "echarts";
import { useMemo, useState } from "react";
import type { MonitorHistory, MonitorSnapshot } from "../../api/client";
import { EChart } from "../charts/EChart";
import {
  HORIZONS,
  axisTooltipFormatter,
  crisisMarkArea,
  crisisMarkLine,
  fmtPct,
  regimeBadgeClass,
  regimeClass,
} from "./helpers";

type Props = {
  snapshot: MonitorSnapshot;
  history: MonitorHistory;
  horizon: number;
  onHorizonChange: (h: number) => void;
};

export function MonitorHero({
  snapshot,
  history,
  horizon,
  onHorizonChange,
}: Props) {
  const [metric, setMetric] = useState<"ep_ann_pct" | "ann_vol">("ep_ann_pct");

  const print = snapshot.by_horizon[String(horizon)] ?? snapshot.primary;

  const chartOpt: EChartsOption = useMemo(() => {
    const colors = ["#1f4e79", "#c45c26", "#0b6e4f", "#5b6b7c"];
    const series = HORIZONS.map((h, i) => ({
      name: `${h}m`,
      type: "line" as const,
      showSymbol: false,
      color: colors[i],
      lineStyle: {
        width: h === horizon ? 2.2 : 1.1,
        opacity: h === horizon ? 1 : 0.45,
      },
      data: history.rows
        .filter((r) => r.horizon_m === h)
        .map((r) => [
          r.date,
          metric === "ep_ann_pct" ? r.ep_ann_pct : r.ann_vol,
        ])
        .filter((d) => d[1] != null),
      markLine: h === horizon ? crisisMarkLine(history.events) : undefined,
      markArea: h === horizon ? crisisMarkArea(history.events) : undefined,
    }));

    return {
      title: {
        text:
          metric === "ep_ann_pct"
            ? "Option-implied equity premium (ann. %)"
            : "Annualized SVIX (vol points)",
        left: 0,
        top: 0,
        textStyle: { fontSize: 13, fontWeight: 600 },
      },
      tooltip: {
        trigger: "axis",
        formatter: axisTooltipFormatter(2, "%"),
      },
      legend: {
        top: 0,
        right: 0,
        itemWidth: 14,
        itemHeight: 8,
        textStyle: { fontSize: 11 },
      },
      grid: { left: 52, right: 20, top: 44, bottom: 48 },
      xAxis: { type: "time" },
      yAxis: {
        type: "value",
        name: "%",
        nameLocation: "end",
        nameGap: 8,
        nameTextStyle: { padding: [0, 0, 0, 0], align: "right" },
        splitNumber: 5,
      },
      series,
    };
  }, [history, horizon, metric]);

  // Compact regime strip
  const regimeStrip = useMemo(() => {
    const tl = snapshot.regime_timeline;
    if (!tl.length) return null;
    const colors: Record<string, string> = {
      calm: "#0b6e4f",
      elevated: "#b45309",
      stress: "#b42318",
    };
    return (
      <div className="flex h-2 w-full overflow-hidden rounded-sm border border-[var(--line)]">
        {tl.map((p, i) => (
          <div
            key={`${p.date}-${i}`}
            title={`${p.date}: ${p.regime}`}
            style={{
              flex: 1,
              background: colors[p.regime] ?? "#5b6b7c",
              opacity: 0.75,
            }}
          />
        ))}
      </div>
    );
  }, [snapshot.regime_timeline]);

  return (
    <section className="flex flex-col gap-5">
      <div className="flex flex-col gap-4 border-b border-[var(--line)] pb-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-[var(--muted)]">
            As of {print.date} · OptionMetrics (WRDS)
          </p>

          <div className="mt-1 flex flex-wrap items-baseline gap-3">
            <p className="text-5xl font-semibold tracking-tight tabular-nums text-[var(--ink)]">
              {fmtPct(print.ep_ann_pct)}
            </p>
            <p className="text-sm text-[var(--muted)]">
              expected excess return · {horizon}m · annualized R<sub>f</sub>
              ·SVIX²
            </p>
          </div>

          <p className="mt-2 max-w-xl text-sm leading-relaxed text-[var(--muted)]">
            <span className={`font-medium ${regimeClass(print.regime)}`}>
              {print.regime.charAt(0).toUpperCase() + print.regime.slice(1)}
            </span>
            {" — "}
            {print.regime_blurb}{" "}
            {print.percentile_full != null && (
              <>
                (SVIX vol at the{" "}
                <span className="mono">
                  {print.percentile_full.toFixed(0)}th
                </span>{" "}
                percentile of the OptionMetrics sample since{" "}
                {snapshot.sample_start.slice(0, 4)};{" "}
                <span className="mono">
                  {print.percentile_5y?.toFixed(0) ?? "—"}th
                </span>{" "}
                vs its last 5y.)
              </>
            )}
          </p>
        </div>

        <div className="flex flex-col items-start gap-2 sm:items-end">
          <div className="flex gap-1">
            {HORIZONS.map((h) => (
              <button
                key={h}
                type="button"
                onClick={() => onHorizonChange(h)}
                className={`rounded border px-2.5 py-1 text-xs ${
                  h === horizon
                    ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--ink)]"
                    : "border-[var(--line)] bg-white text-[var(--muted)] hover:border-[var(--accent)]"
                }`}
              >
                {h}m
              </button>
            ))}
          </div>
          <span
            className={`rounded border px-2 py-0.5 text-xs font-medium capitalize ${regimeBadgeClass(print.regime)}`}
          >
            {print.regime} regime
          </span>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-4">
        {HORIZONS.map((h) => {
          const p = snapshot.by_horizon[String(h)];
          if (!p) return null;
          return (
            <button
              key={h}
              type="button"
              onClick={() => onHorizonChange(h)}
              className={`rounded border px-3 py-2 text-left transition ${
                h === horizon
                  ? "border-[var(--accent)] bg-white"
                  : "border-[var(--line)] bg-[color-mix(in_srgb,var(--surface)_80%,var(--bg))] hover:border-[var(--accent)]"
              }`}
            >
              <p className="text-[10px] uppercase tracking-wide text-[var(--muted)]">
                {h}m
              </p>
              <p className="mono text-lg font-semibold tabular-nums">
                {fmtPct(p.ep_ann_pct)}
              </p>
              <p className="text-[11px] text-[var(--muted)]">
                SVIX vol {fmtPct(p.ann_vol, 1)}
              </p>
            </button>
          );
        })}
      </div>

      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="text-[var(--muted)]">Chart</span>
        {(
          [
            ["ep_ann_pct", "Equity premium"],
            ["ann_vol", "SVIX vol"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => setMetric(id)}
            className={`rounded border px-2 py-1 ${
              metric === id
                ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                : "border-[var(--line)] bg-white text-[var(--muted)]"
            }`}
          >
            {label}
          </button>
        ))}
        <span className="text-[var(--muted)]">
          OptionMetrics series through {snapshot.sample_end}
        </span>
      </div>

      <EChart option={chartOpt} height={360} />

      <div className="flex flex-col gap-1">
        <div className="flex justify-between text-[10px] uppercase tracking-wide text-[var(--muted)]">
          <span>Regime path ({horizon}m SVIX vol)</span>
          <span className="normal-case tracking-normal">
            <span className="text-[var(--ok)]">calm</span>
            {" · "}
            <span className="text-[var(--warn)]">elevated</span>
            {" · "}
            <span className="text-[var(--danger)]">stress</span>
          </span>
        </div>
        {regimeStrip}
        <p className="text-[11px] text-[var(--muted)]">
          Shaded bands mark 2008, 2020, and post-2022 stress windows.
        </p>
      </div>
    </section>
  );
}
