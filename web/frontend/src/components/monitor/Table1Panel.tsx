import { useMemo, useState } from "react";
import type { MonitorTable1 } from "../../api/client";
import { HORIZONS, fmtNum, fmtPct } from "./helpers";

type Props = { data: MonitorTable1 };

const DEFAULT_SAMPLE = "January 2023-latest usable";

export function Table1Panel({ data }: Props) {
  const [sample, setSample] = useState(
    data.samples.includes(DEFAULT_SAMPLE)
      ? DEFAULT_SAMPLE
      : (data.samples[0] ?? ""),
  );

  const rows = useMemo(
    () =>
      data.rows
        .filter((r) => r.sample === sample)
        .sort((a, b) => a.horizon_m - b.horizon_m),
    [data.rows, sample],
  );

  const winner = data.winners[sample];
  const label = data.labels[sample] ?? sample;

  return (
    <section className="flex flex-col gap-3">
      <div>
        <h2 className="text-base font-semibold tracking-tight">
          Table 1 — forecasting the market
        </h2>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Excess return on SVIX² with Newey–West standard errors. Toggle samples
          to race horizons — the winner earns its place on the Monitor.
        </p>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {data.samples.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setSample(s)}
            className={`rounded border px-2.5 py-1 text-xs ${
              s === sample
                ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                : "border-[var(--line)] bg-white text-[var(--muted)] hover:border-[var(--accent)]"
            }`}
          >
            {data.labels[s] ?? s}
          </button>
        ))}
      </div>

      {winner && (
        <p className="rounded border border-[var(--accent)] bg-[var(--accent-soft)] px-3 py-2 text-sm">
          <span className="font-medium">Horizon race · {label}:</span>{" "}
          <span className="mono">{winner.horizon_m}m</span> leads with R² ={" "}
          <span className="mono">{fmtPct(winner.r2_pct)}</span>
          {winner.beta_t != null && (
            <>
              {" "}
              · β t-stat <span className="mono">{fmtNum(winner.beta_t, 2)}</span>
            </>
          )}
        </p>
      )}

      <div className="overflow-x-auto rounded border border-[var(--line)] bg-white">
        <table className="w-full min-w-[36rem] text-left text-sm">
          <thead className="border-b border-[var(--line)] bg-[var(--bg)] text-xs uppercase tracking-wide text-[var(--muted)]">
            <tr>
              <th className="px-3 py-2 font-medium">Horizon</th>
              <th className="px-3 py-2 font-medium">α</th>
              <th className="px-3 py-2 font-medium">β</th>
              <th className="px-3 py-2 font-medium">β t</th>
              <th className="px-3 py-2 font-medium">R²</th>
              <th className="px-3 py-2 font-medium">N</th>
              <th className="px-3 py-2 font-medium">Pub. R²</th>
            </tr>
          </thead>
          <tbody>
            {HORIZONS.map((h) => {
              const r = rows.find((x) => x.horizon_m === h);
              if (!r) {
                return (
                  <tr key={h} className="border-t border-[var(--line)]">
                    <td className="px-3 py-2 mono">{h}m</td>
                    <td colSpan={6} className="px-3 py-2 text-[var(--muted)]">
                      —
                    </td>
                  </tr>
                );
              }
              const isWin = winner?.horizon_m === h;
              return (
                <tr
                  key={h}
                  className={`border-t border-[var(--line)] ${isWin ? "bg-[var(--accent-soft)]" : ""}`}
                >
                  <td className="px-3 py-2 mono font-medium">
                    {h}m{isWin ? " ★" : ""}
                  </td>
                  <td className="px-3 py-2 mono">{fmtNum(r.alpha, 3)}</td>
                  <td className="px-3 py-2 mono">{fmtNum(r.beta, 3)}</td>
                  <td className="px-3 py-2 mono">{fmtNum(r.beta_t, 2)}</td>
                  <td className="px-3 py-2 mono font-medium">
                    {fmtPct(r.r2_pct)}
                  </td>
                  <td className="px-3 py-2 mono text-[var(--muted)]">
                    {r.nobs.toLocaleString()}
                  </td>
                  <td className="px-3 py-2 mono text-[var(--muted)]">
                    {r.pub_r2 != null ? fmtPct(r.pub_r2) : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-[var(--muted)]">
        Sample window: {rows[0]?.start ?? "—"} → {rows[0]?.end ?? "—"}. Published
        R² from Martin (2025) Table 1 where available.
      </p>
    </section>
  );
}
