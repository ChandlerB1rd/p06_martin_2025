import { useEffect, useState } from "react";
import {
  api,
  type MonitorHistory,
  type MonitorSnapshot,
  type MonitorTable1,
} from "../../api/client";
import { MonitorHero } from "./MonitorHero";
import { Table1Panel } from "./Table1Panel";

export function MonitorView() {
  const [horizon, setHorizon] = useState(1);
  const [snapshot, setSnapshot] = useState<MonitorSnapshot | null>(null);
  const [history, setHistory] = useState<MonitorHistory | null>(null);
  const [table1, setTable1] = useState<MonitorTable1 | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // History and Table 1 do not depend on the selected horizon.
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([api.monitorHistory(), api.monitorTable1()])
      .then(([hist, t1]) => {
        if (!cancelled) {
          setHistory(hist);
          setTable1(t1);
          setError(null);
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // The snapshot carries the regime timeline for the primary horizon.
  useEffect(() => {
    let cancelled = false;
    api
      .monitorSnapshot(horizon)
      .then((snap) => {
        if (!cancelled) setSnapshot(snap);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [horizon]);

  if (error) {
    return (
      <div className="rounded border border-red-200 bg-red-50 px-4 py-3 text-sm text-[var(--danger)]">
        Failed to load Monitor: {error}
      </div>
    );
  }

  if (loading || !snapshot || !history || !table1) {
    return <p className="text-sm text-[var(--muted)]">Loading SVIX Monitor…</p>;
  }

  return (
    <div className="flex flex-col gap-10">
      <div id="hero" className="scroll-mt-24 max-w-2xl">
        <h2 className="text-2xl font-semibold tracking-tight">
          Is the market cheap or expensive?
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-[var(--muted)]">
          Option prices hand you an expected excess return every trading day via
          Martin’s SVIX. Read today’s number and its regime, then check whether
          the signal survives across samples and horizons.
        </p>
      </div>

      <div className="scroll-mt-24">
        <MonitorHero
          snapshot={snapshot}
          history={history}
          horizon={horizon}
          onHorizonChange={setHorizon}
        />
      </div>

      <div id="table1" className="scroll-mt-24 border-t border-[var(--line)] pt-8">
        <Table1Panel data={table1} />
      </div>
    </div>
  );
}
