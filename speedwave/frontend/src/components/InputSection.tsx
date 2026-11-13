import { useRef, useState } from "react";
import type { AppConfig } from "../lib/api";
import { formatBytes } from "../lib/format";
import { IconLink, IconUpload, Panel, Spinner } from "./ui";

export type Intake =
  | { kind: "idle" }
  | { kind: "uploading"; name: string; size: number; progress: number }
  | { kind: "analyzing"; name: string }
  | { kind: "importing"; url: string };

interface Props {
  config: AppConfig | null;
  intake: Intake;
  disabled: boolean;
  onFile: (f: File) => void;
  onUrl: (url: string) => void;
  onCancel: () => void;
}

export function InputSection({ config, intake, disabled, onFile, onUrl, onCancel }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  const [url, setUrl] = useState("");
  const busy = intake.kind !== "idle";
  const accept = (config?.input_extensions ?? [".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac"]).join(",");

  const pick = (files: FileList | null) => {
    if (files && files[0]) onFile(files[0]);
  };

  return (
    <Panel step="01" title="Input" subtitle="Upload a file or import a direct audio link">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          if (!busy && !disabled) setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          if (!busy && !disabled) pick(e.dataTransfer.files);
        }}
        className={`relative overflow-hidden rounded-2xl border-2 border-dashed px-6 py-10 text-center transition ${
          drag ? "border-violet-400 bg-violet-500/10" : "border-ink-600 bg-ink-850 hover:border-ink-500"
        }`}
      >
        {intake.kind === "uploading" ? (
          <div className="mx-auto max-w-md">
            <div className="mb-1 truncate text-sm font-medium text-slate-100">{intake.name}</div>
            <div className="mb-4 font-mono text-xs text-slate-500">
              Uploading {formatBytes(intake.size * intake.progress)} / {formatBytes(intake.size)}
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-ink-700">
              <div className="h-full rounded-full bg-gradient-to-r from-violet-500 to-azure-500 transition-[width] duration-200" style={{ width: `${intake.progress * 100}%` }} />
            </div>
            <div className="mt-3 flex items-center justify-between font-mono text-xs text-slate-400">
              <span>{Math.round(intake.progress * 100)}%</span>
              <button onClick={onCancel} className="text-slate-400 underline-offset-2 hover:text-rose-300 hover:underline">Cancel</button>
            </div>
          </div>
        ) : intake.kind === "analyzing" || intake.kind === "importing" ? (
          <div className="flex flex-col items-center gap-3 text-sm text-slate-300">
            <Spinner className="h-6 w-6 text-violet-400" />
            <div>
              {intake.kind === "analyzing" ? (
                <>Analyzing <span className="font-medium text-slate-100">{intake.name}</span>…</>
              ) : (
                <>Downloading and validating the linked file…</>
              )}
            </div>
            <div className="text-xs text-slate-500">
              {intake.kind === "analyzing" ? "Reading metadata and checking the audio decodes correctly" : intake.url}
            </div>
          </div>
        ) : (
          <>
            <div className="mx-auto mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br from-violet-500/20 to-azure-500/20 text-violet-300 ring-1 ring-violet-500/30">
              <IconUpload width={26} height={26} />
            </div>
            <p className="text-base font-medium text-slate-100">Drag & drop your audio file here</p>
            <p className="mt-1 text-sm text-slate-500">
              {(config?.input_formats ?? ["MP3", "WAV", "OGG", "FLAC", "M4A", "AAC"]).join(" · ")} — up to {config?.max_upload_mb ?? 500} MB
            </p>
            <button
              onClick={() => inputRef.current?.click()}
              disabled={disabled}
              className="mt-5 inline-flex items-center gap-2 rounded-xl bg-ink-700 px-5 py-2.5 text-sm font-semibold text-slate-100 ring-1 ring-ink-600 transition hover:bg-ink-600 disabled:opacity-50"
            >
              <IconUpload /> Browse Files
            </button>
            <input ref={inputRef} type="file" accept={accept} className="hidden" onChange={(e) => { pick(e.target.files); e.target.value = ""; }} />
          </>
        )}
      </div>

      <div className="my-5 flex items-center gap-3 text-[11px] uppercase tracking-[0.2em] text-slate-600">
        <span className="h-px flex-1 bg-ink-700" /> or <span className="h-px flex-1 bg-ink-700" />
      </div>

      <form
        className="flex flex-col gap-3 sm:flex-row"
        onSubmit={(e) => {
          e.preventDefault();
          if (url.trim() && !busy) onUrl(url.trim());
        }}
      >
        <label className="relative flex-1">
          <span className="sr-only">Audio URL</span>
          <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500"><IconLink /></span>
          <input
            type="url"
            inputMode="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://drive.google.com/file/d/… or https://…/track.mp3"
            disabled={busy || disabled}
            className="w-full rounded-xl border border-ink-600 bg-ink-850 py-3 pl-11 pr-4 font-mono text-sm text-slate-100 placeholder:text-slate-600 focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-500/30 disabled:opacity-50"
          />
        </label>
        <button
          type="submit"
          disabled={!url.trim() || busy || disabled}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-azure-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-azure-400 disabled:cursor-not-allowed disabled:bg-ink-700 disabled:text-slate-500"
        >
          {intake.kind === "importing" ? <Spinner /> : <IconLink />} Import URL
        </button>
      </form>
      <p className="mt-2 text-xs text-slate-500">
        Direct file links and public Google Drive / Dropbox share links (set to “Anyone with the link”). Streaming
        platform pages (YouTube, Spotify, SoundCloud…) and login-protected or DRM content are not supported.
      </p>
    </Panel>
  );
}
