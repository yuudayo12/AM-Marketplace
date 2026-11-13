import type { Job } from "../lib/api";
import { isActive } from "../lib/api";
import { formatDuration, formatEta } from "../lib/format";
import { Alert, Panel, Spinner } from "./ui";

export function ProcessingStatus({ job, onCancel }: { job: Job; onCancel: () => void }) {
  const active = isActive(job.status);
  const pct = Math.round(job.progress * 100);
  const processed = job.progress * job.expected_duration;

  return (
    <Panel
      step="04"
      title="Processing Status"
      subtitle={`${job.settings.engine} · ${job.settings.formats.map((f) => f.toUpperCase()).join(" + ")}`}
      right={active && (
        <button onClick={onCancel} className="rounded-lg px-2.5 py-1.5 text-xs text-slate-400 transition hover:bg-ink-700 hover:text-rose-300">
          Cancel
        </button>
      )}
    >
      {active && (
        <div aria-live="polite">
          <div className="mb-3 flex items-end justify-between">
            <div className="flex items-center gap-2.5 text-sm text-slate-200">
              <Spinner className="h-4 w-4 text-violet-400" />
              {job.stage}
            </div>
            <div className="font-mono text-2xl font-semibold tabular-nums text-slate-100">
              {job.status === "queued" ? "—" : `${pct}%`}
            </div>
          </div>
          <div
            className="relative h-3 overflow-hidden rounded-full bg-ink-700"
            role="progressbar"
            aria-valuenow={pct}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div
              className="relative h-full rounded-full bg-gradient-to-r from-violet-500 to-azure-500 transition-[width] duration-300 ease-out"
              style={{ width: `${job.status === "finalizing" ? 100 : pct}%` }}
            >
              <div className="absolute inset-0 animate-shimmer bg-[linear-gradient(90deg,transparent,rgba(255,255,255,.35),transparent)] bg-[length:200%_100%]" />
            </div>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-2.5 sm:grid-cols-4">
            <Metric label="Remaining" value={job.status === "processing" ? formatEta(job.eta_seconds) : job.status === "queued" ? "waiting" : "—"} />
            <Metric label="Elapsed" value={job.elapsed_seconds != null ? `${job.elapsed_seconds.toFixed(1)} s` : "—"} />
            <Metric label="Rendered" value={`${formatDuration(processed)} / ${formatDuration(job.expected_duration)}`} />
            <Metric label="Speed" value={job.realtime_factor ? `${job.realtime_factor}× realtime` : "—"} />
          </div>
        </div>
      )}
      {job.status === "completed" && (
        <Alert kind="success">
          Conversion complete in {job.elapsed_seconds?.toFixed(1)} s. All outputs were verified: duration, codec and channels checked.
        </Alert>
      )}
      {job.status === "failed" && <Alert kind="error"><strong className="font-semibold">Processing failed.</strong> {job.error}</Alert>}
      {job.status === "cancelled" && <Alert kind="info">Conversion cancelled. No files were kept.</Alert>}
    </Panel>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-ink-700 bg-ink-850 px-3 py-2">
      <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">{label}</div>
      <div className="mt-0.5 truncate font-mono text-xs text-slate-200">{value}</div>
    </div>
  );
}
