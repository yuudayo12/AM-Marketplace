import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import { formatDuration } from "../lib/format";
import { IconPause, IconPlay, Spinner } from "./ui";

// Only one preview plays at a time across the page.
let current: HTMLAudioElement | null = null;

interface Props {
  src: string;
  waveformUrl: string;
  duration: number;
  accent?: "violet" | "azure";
  label?: string;
}

/** Audio preview drawn over the file's real waveform (peaks computed by the server). */
export function WaveformPlayer({ src, waveformUrl, duration, accent = "violet", label }: Props) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const [peaks, setPeaks] = useState<number[] | null>(null);
  const [playing, setPlaying] = useState(false);
  const [time, setTime] = useState(0);
  const [buffering, setBuffering] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setPeaks(null);
    api.waveform(waveformUrl).then((p) => alive && setPeaks(p)).catch(() => alive && setPeaks([]));
    return () => {
      alive = false;
    };
  }, [waveformUrl]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const wrap = wrapRef.current;
    if (!canvas || !wrap) return;
    const dpr = window.devicePixelRatio || 1;
    const w = wrap.clientWidth;
    const h = wrap.clientHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);
    const bar = 3, gap = 1.5;
    const n = Math.max(1, Math.floor(w / (bar + gap)));
    const data = peaks && peaks.length ? peaks : null;
    const played = duration > 0 ? time / duration : 0;
    const [c1, c2] = accent === "violet" ? ["#a78bfa", "#60a5fa"] : ["#60a5fa", "#a78bfa"];
    const grad = ctx.createLinearGradient(0, 0, w, 0);
    grad.addColorStop(0, c1);
    grad.addColorStop(1, c2);
    for (let i = 0; i < n; i++) {
      let v = 0.08;
      if (data) {
        const a = Math.floor((i / n) * data.length);
        const b = Math.max(a + 1, Math.floor(((i + 1) / n) * data.length));
        v = Math.max(0.04, ...data.slice(a, b));
      }
      const bh = Math.max(2, v * (h - 6));
      const x = i * (bar + gap);
      ctx.fillStyle = i / n <= played ? grad : "rgba(148,163,184,0.22)";
      ctx.beginPath();
      ctx.roundRect(x, (h - bh) / 2, bar, bh, 1.5);
      ctx.fill();
    }
  }, [peaks, time, duration, accent]);

  useEffect(() => {
    draw();
    const ro = new ResizeObserver(draw);
    if (wrapRef.current) ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, [draw]);

  useEffect(() => () => audioRef.current?.pause(), []);

  const toggle = async () => {
    const a = audioRef.current;
    if (!a) return;
    if (a.paused) {
      if (current && current !== a) current.pause();
      current = a;
      try {
        await a.play();
      } catch {
        setError("This browser cannot play this format. You can still convert and download it.");
      }
    } else a.pause();
  };

  const seek = (e: React.PointerEvent<HTMLDivElement>) => {
    const a = audioRef.current;
    const wrap = wrapRef.current;
    if (!a || !wrap || !duration) return;
    const r = wrap.getBoundingClientRect();
    const t = Math.min(Math.max((e.clientX - r.left) / r.width, 0), 1) * duration;
    a.currentTime = t;
    setTime(t);
  };

  return (
    <div className="rounded-xl border border-ink-700 bg-ink-850 p-3">
      <div className="flex items-center gap-3">
        <button
          onClick={toggle}
          aria-label={playing ? `Pause ${label ?? "preview"}` : `Play ${label ?? "preview"}`}
          className={`grid h-10 w-10 shrink-0 place-items-center rounded-full text-white transition active:scale-95 ${
            accent === "violet" ? "bg-violet-500 hover:bg-violet-400" : "bg-azure-500 hover:bg-azure-400"
          }`}
        >
          {buffering ? <Spinner /> : playing ? <IconPause /> : <IconPlay className="ml-0.5" />}
        </button>
        <div
          ref={wrapRef}
          onPointerDown={seek}
          className="relative h-12 min-w-0 flex-1 cursor-pointer touch-none"
          role="slider"
          aria-label="Seek"
          aria-valuemin={0}
          aria-valuemax={Math.round(duration)}
          aria-valuenow={Math.round(time)}
          tabIndex={0}
          onKeyDown={(e) => {
            const a = audioRef.current;
            if (!a) return;
            if (e.key === "ArrowRight") a.currentTime = Math.min(duration, a.currentTime + 5);
            if (e.key === "ArrowLeft") a.currentTime = Math.max(0, a.currentTime - 5);
            if (e.key === " ") { e.preventDefault(); toggle(); }
          }}
        >
          <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" />
          {peaks === null && <div className="absolute inset-0 animate-shimmer rounded bg-[linear-gradient(90deg,transparent,rgba(255,255,255,.05),transparent)] bg-[length:200%_100%]" />}
        </div>
        <div className="hidden shrink-0 text-right font-mono text-xs tabular-nums text-slate-400 sm:block">
          {formatDuration(time)} <span className="text-slate-600">/ {formatDuration(duration)}</span>
        </div>
      </div>
      {error && <p className="mt-2 text-xs text-amber-300/90">{error}</p>}
      <audio
        ref={audioRef}
        src={src}
        preload="metadata"
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        onWaiting={() => setBuffering(true)}
        onPlaying={() => setBuffering(false)}
        onCanPlay={() => setBuffering(false)}
        onTimeUpdate={(e) => setTime(e.currentTarget.currentTime)}
        onError={() => setError("Preview unavailable in this browser for this format. Conversion still works.")}
      />
    </div>
  );
}
