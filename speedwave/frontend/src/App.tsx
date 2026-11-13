import { useCallback, useEffect, useRef, useState } from "react";
import { AudioInfo } from "./components/AudioInfo";
import { DownloadSection } from "./components/DownloadSection";
import { Header } from "./components/Header";
import { InputSection, type Intake } from "./components/InputSection";
import { ProcessingStatus } from "./components/ProcessingStatus";
import { SettingsPanel } from "./components/SettingsPanel";
import { Alert, IconBolt, Spinner } from "./components/ui";
import { api, ApiError, isActive, type AppConfig, type Job, type JobSettings, type Source } from "./lib/api";
import { speedLabel } from "./lib/format";

const DEFAULT_SETTINGS: JobSettings = {
  speed: 2,
  formats: ["mp3", "ogg"],
  mp3_bitrate: 320,
  ogg_quality: 8,
  quality: "studio",
  clip_protection: true,
};

const POLL_MS = 400;

export default function App() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [engine, setEngine] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [intake, setIntake] = useState<Intake>({ kind: "idle" });
  const [source, setSource] = useState<Source | null>(null);
  const [settings, setSettings] = useState<JobSettings>(DEFAULT_SETTINGS);
  const [job, setJob] = useState<Job | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<() => void>(() => {});
  const resultsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.config().then((c) => {
      setConfig(c);
      setSettings((s) => ({ ...s, quality: c.default_quality }));
    }).catch((e: ApiError) => setServerError(e.message));
    api.health().then((h) => {
      setEngine(h.rubberband_engine);
      if (!h.ok) setServerError("The server's audio engine is incomplete (FFmpeg with Rubber Band, LAME and Vorbis is required). See README → Troubleshooting.");
    }).catch(() => {});
  }, []);

  // Poll the job while it is running; the server reports real FFmpeg progress.
  useEffect(() => {
    if (!job || !isActive(job.status)) return;
    let stopped = false;
    const t = setInterval(async () => {
      try {
        const next = await api.job(job.id);
        if (!stopped) setJob(next);
      } catch (e) {
        if (!stopped) {
          setError((e as Error).message);
          clearInterval(t);
        }
      }
    }, POLL_MS);
    return () => {
      stopped = true;
      clearInterval(t);
    };
  }, [job?.id, job?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (job?.status === "completed") setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 150);
  }, [job?.status]);

  const accept = useCallback((s: Source) => {
    setSource(s);
    setJob(null);
    setIntake({ kind: "idle" });
  }, []);

  const replaceSource = useCallback(() => {
    if (source) api.deleteSource(source.id).catch(() => {});
    setSource(null);
    setJob(null);
  }, [source]);

  const onFile = async (file: File) => {
    setError(null);
    const ext = "." + (file.name.split(".").pop() ?? "").toLowerCase();
    if (config && !config.input_extensions.includes(ext)) {
      setError(`Unsupported file type "${ext}". Supported: ${config.input_formats.join(", ")}.`);
      return;
    }
    if (config && file.size > config.max_upload_mb * 1024 * 1024) {
      setError(`This file is larger than the ${config.max_upload_mb} MB upload limit.`);
      return;
    }
    replaceSource();
    setIntake({ kind: "uploading", name: file.name, size: file.size, progress: 0 });
    const { promise, abort } = api.upload(file, (p) => {
      setIntake(p >= 1 ? { kind: "analyzing", name: file.name } : { kind: "uploading", name: file.name, size: file.size, progress: p });
    });
    abortRef.current = abort;
    try {
      accept(await promise);
    } catch (e) {
      setIntake({ kind: "idle" });
      if ((e as Error).message !== "Upload cancelled.") setError((e as Error).message);
    }
  };

  const onUrl = async (url: string) => {
    setError(null);
    replaceSource();
    setIntake({ kind: "importing", url });
    const ctrl = new AbortController();
    abortRef.current = () => ctrl.abort();
    try {
      accept(await api.importUrl(url, ctrl.signal));
    } catch (e) {
      setIntake({ kind: "idle" });
      if ((e as Error).name !== "AbortError") setError((e as Error).message);
    }
  };

  const convert = async () => {
    if (!source || submitting || (job && isActive(job.status))) return;
    setError(null);
    setSubmitting(true);
    try {
      setJob(await api.createJob(source.id, settings));
    } catch (e) {
      setError((e as Error).message);
      if ((e as ApiError).status === 404) setSource(null);
    } finally {
      setSubmitting(false);
    }
  };

  const running = !!job && isActive(job.status);
  // The same file + settings was already converted: show it instead of re-running.
  const alreadyDone = job?.status === "completed" && sameSettings(job.settings, settings);

  return (
    <div className="relative min-h-screen overflow-x-hidden">
      <div className="pointer-events-none fixed inset-0 -z-10">
        <div className="absolute -top-40 left-1/2 h-[520px] w-[900px] -translate-x-1/2 rounded-full bg-violet-600/15 blur-[120px]" />
        <div className="absolute bottom-0 right-0 h-[400px] w-[500px] rounded-full bg-azure-500/10 blur-[120px]" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,.018)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.018)_1px,transparent_1px)] bg-[size:48px_48px]" />
      </div>

      <main className="mx-auto max-w-4xl space-y-5 px-4 py-8 sm:px-6 sm:py-12">
        <Header engine={engine} />

        {serverError && <Alert kind="error">{serverError}</Alert>}

        <InputSection config={config} intake={intake} disabled={running} onFile={onFile} onUrl={onUrl} onCancel={() => abortRef.current()} />

        {error && <Alert kind="error" onClose={() => setError(null)}>{error}</Alert>}

        {source && (
          <>
            <AudioInfo source={source} onRemove={replaceSource} locked={running} />
            <SettingsPanel config={config} value={settings} onChange={setSettings} duration={source.duration} disabled={running} />

            <button
              onClick={convert}
              disabled={running || submitting || alreadyDone}
              className="group relative w-full overflow-hidden rounded-2xl bg-gradient-to-r from-violet-600 via-violet-500 to-azure-500 px-6 py-5 text-base font-extrabold uppercase tracking-[0.2em] text-white shadow-glow transition hover:brightness-110 active:scale-[0.995] disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:brightness-100 sm:text-lg"
            >
              <span className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent transition-transform duration-700 group-hover:translate-x-full" />
              <span className="relative inline-flex items-center gap-3">
                {running || submitting ? <Spinner className="h-5 w-5" /> : <IconBolt width={22} height={22} />}
                {running ? "Converting…" : alreadyDone ? "Converted — change settings to re-run" : `Convert audio to ${speedLabel(settings.speed)}`}
              </span>
            </button>

            {job && <ProcessingStatus job={job} onCancel={() => api.cancelJob(job.id).then(setJob).catch(() => {})} />}
            <div ref={resultsRef} className="scroll-mt-6">
              {job?.status === "completed" && <DownloadSection job={job} />}
            </div>
          </>
        )}

        <footer className="pt-6 text-center text-xs text-slate-600">
          Files are private to your browser session and deleted automatically after {config?.file_ttl_minutes ?? 60} minutes of inactivity.
        </footer>
      </main>
    </div>
  );
}

function sameSettings(a: JobSettings, b: JobSettings) {
  return (
    a.speed === b.speed &&
    a.formats.join() === [...b.formats].sort().join() &&
    a.mp3_bitrate === b.mp3_bitrate &&
    a.ogg_quality === b.ogg_quality &&
    a.quality === b.quality &&
    a.clip_protection === b.clip_protection
  );
}
