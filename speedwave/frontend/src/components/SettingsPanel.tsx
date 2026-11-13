import type { AppConfig, JobSettings, OutputFormat } from "../lib/api";
import { formatDuration, speedLabel } from "../lib/format";
import { IconLock, Panel } from "./ui";

const SPEEDS = [1.25, 1.5, 1.75, 2, 2.5, 3];
const OGG_QUALITIES = [
  { q: 6, label: "q6 ≈192k" },
  { q: 8, label: "q8 ≈256k" },
  { q: 10, label: "q10 ≈500k" },
];

interface Props {
  config: AppConfig | null;
  value: JobSettings;
  onChange: (s: JobSettings) => void;
  duration: number | null;
  disabled: boolean;
}

export function SettingsPanel({ config, value, onChange, duration, disabled }: Props) {
  const set = (patch: Partial<JobSettings>) => onChange({ ...value, ...patch });
  const toggleFormat = (f: OutputFormat) => {
    const has = value.formats.includes(f);
    if (has && value.formats.length === 1) return; // at least one format
    set({ formats: has ? value.formats.filter((x) => x !== f) : [...value.formats, f].sort() as OutputFormat[] });
  };

  return (
    <Panel step="03" title="Processing Settings" subtitle="Pitch-preserving time-stretch">
      <fieldset disabled={disabled} className="space-y-6 disabled:opacity-60">
        {/* Speed */}
        <div>
          <div className="mb-2.5 flex items-baseline justify-between">
            <Label>Playback speed</Label>
            {duration != null && (
              <span className="font-mono text-xs text-slate-500">
                {formatDuration(duration)} → <span className="text-violet-300">{formatDuration(duration / value.speed)}</span>
              </span>
            )}
          </div>
          <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
            {SPEEDS.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => set({ speed: s })}
                className={`rounded-xl border py-2.5 font-mono text-sm font-semibold transition ${
                  value.speed === s
                    ? "border-violet-400 bg-violet-500/15 text-violet-200 shadow-glow"
                    : "border-ink-600 bg-ink-850 text-slate-400 hover:border-ink-500 hover:text-slate-200"
                }`}
              >
                {speedLabel(s)}
                {s === 2 && <span className="ml-1 text-[9px] uppercase tracking-wider text-violet-400/80">def</span>}
              </button>
            ))}
          </div>
        </div>

        {/* Pitch lock */}
        <div className="flex items-center justify-between gap-4 rounded-xl border border-emerald-500/25 bg-emerald-500/[0.06] px-4 py-3">
          <div>
            <div className="flex items-center gap-2 text-sm font-medium text-emerald-200"><IconLock width={15} height={15} /> Pitch preservation</div>
            <p className="mt-0.5 text-xs text-emerald-200/60">Always on. Key and pitch stay exactly as the original; only tempo changes.</p>
          </div>
          <div className="relative h-6 w-11 shrink-0 rounded-full bg-emerald-500/80" aria-label="Pitch preservation always enabled">
            <span className="absolute right-0.5 top-0.5 h-5 w-5 rounded-full bg-white" />
          </div>
        </div>

        {/* Output format */}
        <div className="grid gap-6 sm:grid-cols-2">
          <div>
            <Label>Output format</Label>
            <div className="mt-2.5 grid grid-cols-2 gap-2">
              {(config?.output_formats ?? ["mp3", "ogg"]).map((f) => {
                const on = value.formats.includes(f);
                return (
                  <button
                    key={f}
                    type="button"
                    role="checkbox"
                    aria-checked={on}
                    onClick={() => toggleFormat(f)}
                    className={`flex items-center justify-center gap-2 rounded-xl border py-2.5 text-sm font-semibold uppercase tracking-wider transition ${
                      on ? "border-azure-400 bg-azure-500/15 text-azure-300" : "border-ink-600 bg-ink-850 text-slate-500 hover:text-slate-300"
                    }`}
                  >
                    <span className={`grid h-4 w-4 place-items-center rounded border ${on ? "border-azure-400 bg-azure-500" : "border-ink-500"}`}>
                      {on && <svg viewBox="0 0 12 12" className="h-3 w-3 text-white"><path d="m2.5 6 2.5 2.5 4.5-5" fill="none" stroke="currentColor" strokeWidth="2" /></svg>}
                    </span>
                    {f}
                  </button>
                );
              })}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <SelectField
              label="MP3 bitrate"
              disabled={!value.formats.includes("mp3")}
              value={value.mp3_bitrate}
              onChange={(v) => set({ mp3_bitrate: v })}
              options={(config?.mp3_bitrates ?? [128, 192, 256, 320]).map((b) => ({ value: b, label: `${b} kbps${b === 320 ? " ★" : ""}` }))}
            />
            <SelectField
              label="OGG quality"
              disabled={!value.formats.includes("ogg")}
              value={value.ogg_quality}
              onChange={(v) => set({ ogg_quality: v })}
              options={OGG_QUALITIES.map((o) => ({ value: o.q, label: o.label }))}
            />
          </div>
        </div>

        {/* Engine */}
        <div>
          <Label>Stretch engine</Label>
          <div className="mt-2.5 grid gap-2 sm:grid-cols-2">
            {(config?.quality_modes ?? []).map((m) => {
              const unavailable = m.id === "studio" && config && !config.r3_available;
              return (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => set({ quality: m.id })}
                  className={`rounded-xl border p-3.5 text-left transition ${
                    value.quality === m.id ? "border-violet-400 bg-violet-500/10" : "border-ink-600 bg-ink-850 hover:border-ink-500"
                  }`}
                >
                  <div className="flex items-center justify-between text-sm font-semibold text-slate-100">
                    {m.label}
                    {m.id === config?.default_quality && <span className="rounded bg-violet-500/20 px-1.5 py-0.5 text-[9px] uppercase tracking-wider text-violet-300">Recommended</span>}
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-slate-500">
                    {unavailable ? "Rubber Band 3 not found on the server — falls back to R2." : m.description}
                  </p>
                </button>
              );
            })}
          </div>
        </div>

        {/* Clip protection */}
        <label className="flex cursor-pointer items-center justify-between gap-4 rounded-xl border border-ink-600 bg-ink-850 px-4 py-3">
          <div>
            <div className="text-sm font-medium text-slate-100">Clip protection</div>
            <p className="mt-0.5 text-xs text-slate-500">Transparent peak limiter at −1 dBFS. Only acts on peaks that would clip; it never changes the overall volume.</p>
          </div>
          <input type="checkbox" className="peer sr-only" checked={value.clip_protection} onChange={(e) => set({ clip_protection: e.target.checked })} />
          <span className="relative h-6 w-11 shrink-0 rounded-full bg-ink-600 transition peer-checked:bg-violet-500 peer-focus-visible:ring-2 peer-focus-visible:ring-violet-400 after:absolute after:left-0.5 after:top-0.5 after:h-5 after:w-5 after:rounded-full after:bg-white after:transition peer-checked:after:translate-x-5" />
        </label>
      </fieldset>
    </Panel>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">{children}</div>;
}

function SelectField({ label, value, onChange, options, disabled }: {
  label: string; value: number; onChange: (v: number) => void; options: { value: number; label: string }[]; disabled?: boolean;
}) {
  return (
    <label className={`block ${disabled ? "opacity-40" : ""}`}>
      <Label>{label}</Label>
      <select
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-2.5 w-full appearance-none rounded-xl border border-ink-600 bg-ink-850 bg-[url('data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 20 20%22 fill=%22%2394a3b8%22><path d=%22M5.5 7.5 10 12l4.5-4.5%22 stroke=%22%2394a3b8%22 fill=%22none%22 stroke-width=%221.8%22/></svg>')] bg-[length:16px] bg-[right_10px_center] bg-no-repeat py-2.5 pl-3 pr-8 font-mono text-sm text-slate-100 focus:border-violet-500 focus:outline-none"
      >
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </label>
  );
}
