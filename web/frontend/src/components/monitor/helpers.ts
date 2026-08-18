import type { MonitorEvent } from "../../api/client";

export const HORIZONS = [1, 3, 6, 12] as const;

export function regimeClass(regime: string): string {
  if (regime === "calm") return "text-[var(--ok)]";
  if (regime === "stress") return "text-[var(--danger)]";
  return "text-[var(--warn)]";
}

export function regimeBadgeClass(regime: string): string {
  if (regime === "calm")
    return "border-[var(--ok)] bg-[var(--accent-soft)] text-[var(--ok)]";
  if (regime === "stress")
    return "border-red-300 bg-red-50 text-[var(--danger)]";
  return "border-amber-300 bg-amber-50 text-[var(--warn)]";
}

export function fmtPct(v: number | null | undefined, digits = 2): string {
  if (v == null || !Number.isFinite(v)) return "—";
  return `${v.toFixed(digits)}%`;
}

export function fmtNum(v: number | null | undefined, digits = 3): string {
  if (v == null || !Number.isFinite(v)) return "—";
  return v.toFixed(digits);
}

type AxisTooltipParam = {
  marker?: string;
  seriesName?: string;
  axisType?: string;
  axisValue?: string | number;
  axisValueLabel?: string;
  value?: unknown;
};

function seriesValue(p: AxisTooltipParam): number | null {
  const v = Array.isArray(p.value) ? p.value[p.value.length - 1] : p.value;
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

/** Axis tooltips: ECharts prints full float precision without a formatter. */
export function axisTooltipFormatter(digits = 2, suffix = "%") {
  return (params: unknown) => {
    const list = (Array.isArray(params) ? params : [params]) as AxisTooltipParam[];
    const head = list[0];
    if (!head) return "";
    const label =
      head.axisType?.includes("time") || typeof head.axisValue !== "number"
        ? (head.axisValueLabel ?? "")
        : head.axisValue.toFixed(digits);
    const rows = list
      .map((p) => {
        const v = seriesValue(p);
        if (v == null) return null;
        const name = p.seriesName ? `${p.seriesName} ` : "";
        return `${p.marker ?? ""}${name}<b>${v.toFixed(digits)}${suffix}</b>`;
      })
      .filter((row): row is string => row != null);
    return [label, ...rows].join("<br/>");
  };
}

/** Short chart labels — full names stay on tooltips. */
const EVENT_SHORT: Record<string, string> = {
  gfc: "GFC",
  covid: "COVID",
  banks_2023: "Banks '23",
  aug_2024: "Aug '24",
  tariffs_2025: "Apr '25",
};

/**
 * Vertical event markers with staggered labels so clustered post-2022
 * windows (and GFC near the legend) don't pile on top of each other.
 */
export function crisisMarkLine(events: MonitorEvent[]) {
  // Alternate top / bottom, with increasing offset within each band.
  const topSlots = [8, 22, 36];
  const bottomSlots = [8, 22, 36];
  let ti = 0;
  let bi = 0;

  return {
    symbol: "none" as const,
    silent: true,
    animation: false,
    label: {
      show: true,
      fontSize: 10,
      color: "#5b6b7c",
      backgroundColor: "rgba(244,246,248,0.88)",
      padding: [1, 3] as [number, number],
      borderRadius: 2,
    },
    lineStyle: { type: "dashed" as const, color: "#9aa8b5", width: 1 },
    data: events.map((e, i) => {
      const short = EVENT_SHORT[e.id] ?? e.label;
      // Prefer bottom for late-sample events (right side is denser).
      const preferBottom = e.kind === "post2022" || i >= 2;
      const atTop = !preferBottom;
      const dist = atTop
        ? topSlots[ti++ % topSlots.length]
        : bottomSlots[bi++ % bottomSlots.length];
      return {
        xAxis: e.start,
        name: short,
        label: {
          formatter: short,
          position: atTop ? ("insideEndTop" as const) : ("insideStartBottom" as const),
          distance: dist,
        },
      };
    }),
  };
}

export function crisisMarkArea(events: MonitorEvent[]) {
  return {
    itemStyle: { color: "rgba(196, 92, 38, 0.06)" },
    // No area labels — markLine owns the names (avoids duplicate overlap).
    label: { show: false },
    // ECharts types the 2D form as a fixed pair, so widen to a tuple.
    data: events.map(
      (e) =>
        [{ xAxis: e.start }, { xAxis: e.end }] as [
          { xAxis: string },
          { xAxis: string },
        ],
    ),
  };
}
