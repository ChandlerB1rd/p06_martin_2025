async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

function qs(params: Record<string, string | number | undefined | null>) {
  const u = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") u.set(k, String(v));
  }
  const s = u.toString();
  return s ? `?${s}` : "";
}

export const api = {
  health: () => getJson<{ ok: boolean }>("/api/health"),
  monitorSnapshot: (horizon_m = 1) =>
    getJson<MonitorSnapshot>(`/api/monitor/snapshot${qs({ horizon_m })}`),
  monitorHistory: (horizon_m?: number) =>
    getJson<MonitorHistory>(`/api/monitor/history${qs({ horizon_m })}`),
  monitorTable1: () => getJson<MonitorTable1>("/api/monitor/table1"),
};

export type MonitorEvent = {
  id: string;
  label: string;
  start: string;
  end: string;
  kind: string;
};

export type MonitorHorizonPrint = {
  date: string;
  horizon_m: number;
  svix2: number;
  svix: number | null;
  ep_ann: number | null;
  ep_ann_pct: number | null;
  ann_vol: number | null;
  Rf: number | null;
  percentile_full: number | null;
  percentile_5y: number | null;
  regime: "calm" | "elevated" | "stress" | string;
  regime_blurb: string;
  quantiles_ann_vol: { p50: number; p75: number; p90: number };
};

export type MonitorSnapshot = {
  as_of: string;
  horizon_m: number;
  primary: MonitorHorizonPrint;
  by_horizon: Record<string, MonitorHorizonPrint>;
  regime_timeline: Array<{ date: string; regime: string; ann_vol: number }>;
  events: MonitorEvent[];
  sample_start: string;
  sample_end: string;
};

export type MonitorHistory = {
  metric: string;
  n: number;
  rows: Array<{
    date: string;
    horizon_m: number;
    svix2: number;
    ep_ann: number | null;
    ep_ann_pct: number | null;
    ann_vol: number | null;
  }>;
  events: MonitorEvent[];
};

export type MonitorTable1Row = {
  sample: string;
  horizon_m: number;
  start: string;
  end: string;
  alpha: number | null;
  alpha_se: number | null;
  beta: number | null;
  beta_se: number | null;
  beta_t: number | null;
  r2_pct: number | null;
  nobs: number;
  pub_alpha: number | null;
  pub_beta: number | null;
  pub_r2: number | null;
};

export type MonitorTable1 = {
  rows: MonitorTable1Row[];
  samples: string[];
  winners: Record<string, MonitorTable1Row>;
  labels: Record<string, string>;
};
