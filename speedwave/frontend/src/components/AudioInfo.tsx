import type { Source } from "../lib/api";
import { channelLabel, formatBitrate, formatBytes, formatDuration } from "../lib/format";
import { WaveformPlayer } from "./WaveformPlayer";
import { IconMusic, IconTrash, Panel, Stat } from "./ui";

export function AudioInfo({ source, onRemove, locked }: { source: Source; onRemove: () => void; locked: boolean }) {
  return (
    <Panel
      step="02"
      title="Audio Information"
      subtitle={source.origin === "platform" ? "Imported from a media platform" : source.origin === "url" ? "Imported from URL" : "Uploaded file"}
      right={
        <button
          onClick={onRemove}
          disabled={locked}
          className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs text-slate-400 transition hover:bg-ink-700 hover:text-rose-300 disabled:opacity-40"
        >
          <IconTrash width={14} height={14} /> Remove
        </button>
      }
    >
      <div className="mb-4 flex items-center gap-3">
        <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-violet-500/15 text-violet-300 ring-1 ring-violet-500/30">
          <IconMusic />
        </div>
        <div className="min-w-0">
          <div className="truncate font-medium text-slate-100" title={source.filename}>{source.filename}</div>
          <div className="text-xs text-slate-500">{source.codec.toUpperCase()} · {source.sample_rate.toLocaleString()} Hz</div>
        </div>
      </div>
      <div className="mb-4 grid grid-cols-2 gap-2.5 sm:grid-cols-5">
        <Stat label="Format" value={source.format} />
        <Stat label="Size" value={formatBytes(source.size)} />
        <Stat label="Duration" value={formatDuration(source.duration, true)} />
        <Stat label="Channels" value={channelLabel(source.channels)} />
        <Stat label="Bitrate" value={formatBitrate(source.bit_rate)} />
      </div>
      <div className="mb-1.5 text-[10px] font-medium uppercase tracking-[0.16em] text-slate-500">Original preview</div>
      <WaveformPlayer src={source.preview_url} waveformUrl={source.waveform_url} duration={source.duration} label="original" />
    </Panel>
  );
}
