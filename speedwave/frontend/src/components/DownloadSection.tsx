import type { Job, OutputFormat } from "../lib/api";
import { channelLabel, formatBitrate, formatBytes, formatDuration, speedLabel } from "../lib/format";
import { WaveformPlayer } from "./WaveformPlayer";
import { IconDownload, Panel } from "./ui";

export function DownloadSection({ job }: { job: Job }) {
  const formats = (["mp3", "ogg"] as OutputFormat[]).filter((f) => job.outputs[f]);
  const processed = job.outputs[formats[0]]?.duration ?? job.expected_duration;
  const ratio = processed / job.original_duration;

  return (
    <Panel step="05" title="Download" subtitle={`${speedLabel(job.settings.speed)} · pitch preserved`}>
      {/* Duration comparison */}
      <div className="mb-6 rounded-xl border border-ink-700 bg-ink-850 p-4">
        <div className="space-y-3">
          <Bar label="Original" seconds={job.original_duration} fraction={1} className="bg-slate-600" />
          <Bar label={`Processed ${speedLabel(job.settings.speed)}`} seconds={processed} fraction={ratio} className="bg-gradient-to-r from-violet-500 to-azure-500" />
        </div>
        <div className="mt-3 text-right font-mono text-xs text-slate-500">
          {(ratio * 100).toFixed(1)}% of original length · saved {formatDuration(job.original_duration - processed)}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {formats.map((f) => {
          const o = job.outputs[f]!;
          return (
            <div key={f} className="animate-fade-up rounded-2xl border border-ink-700 bg-ink-850/60 p-4">
              <div className="mb-3 flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`rounded-md px-2 py-0.5 font-mono text-xs font-bold uppercase ${f === "mp3" ? "bg-violet-500/20 text-violet-300" : "bg-azure-500/20 text-azure-300"}`}>{f}</span>
                    <span className="truncate text-sm font-medium text-slate-100" title={o.filename}>{o.filename}</span>
                  </div>
                  <div className="mt-1.5 font-mono text-[11px] text-slate-500">
                    {formatBytes(o.size)} · {formatBitrate(o.bit_rate)} · {(o.sample_rate / 1000).toFixed(1)} kHz · {channelLabel(o.channels)} · {formatDuration(o.duration, true)}
                  </div>
                </div>
              </div>
              <WaveformPlayer src={o.preview_url} waveformUrl={o.waveform_url} duration={o.duration} accent={f === "mp3" ? "violet" : "azure"} label={`${f} result`} />
              <a
                href={o.download_url}
                download={o.filename}
                className={`mt-3 flex w-full items-center justify-center gap-2 rounded-xl py-3 text-sm font-bold uppercase tracking-wider text-white transition hover:brightness-110 active:scale-[0.99] ${
                  f === "mp3" ? "bg-violet-500" : "bg-azure-500"
                }`}
              >
                <IconDownload /> Download {f.toUpperCase()}
              </a>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}

function Bar({ label, seconds, fraction, className }: { label: string; seconds: number; fraction: number; className: string }) {
  return (
    <div className="grid grid-cols-[96px_1fr_64px] items-center gap-3 sm:grid-cols-[120px_1fr_72px]">
      <span className="truncate text-xs text-slate-400">{label}</span>
      <div className="h-2.5 overflow-hidden rounded-full bg-ink-700">
        <div className={`h-full rounded-full ${className} transition-[width] duration-700`} style={{ width: `${Math.min(fraction, 1) * 100}%` }} />
      </div>
      <span className="text-right font-mono text-xs tabular-nums text-slate-200">{formatDuration(seconds, true)}</span>
    </div>
  );
}
