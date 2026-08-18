import { MonitorView } from "./components/monitor/MonitorView";

export default function App() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-[var(--line)] bg-[var(--surface)]">
        <div className="mx-auto flex max-w-6xl flex-wrap items-baseline justify-between gap-2 px-4 py-4">
          <h1 className="text-lg font-semibold tracking-tight">SVIX Monitor</h1>
          <p className="text-xs text-[var(--muted)]">
            Martin (2025) · P06 replication
          </p>
        </div>
      </header>

      <main className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-6">
        <MonitorView />

        <footer className="border-t border-[var(--line)] py-6 text-xs text-[var(--muted)]">
          Daily equity premium from S&amp;P 500 option prices · OptionMetrics and
          CRSP via WRDS · not the brokerage ETF ticker SVIX
        </footer>
      </main>
    </div>
  );
}
