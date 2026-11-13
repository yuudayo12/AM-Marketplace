export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const v = bytes / 1024 ** i;
  return `${v >= 100 || i === 0 ? v.toFixed(0) : v.toFixed(1)} ${units[i]}`;
}

/** 83.4 -> "1:23.4" ; 3725 -> "1:02:05" */
export function formatDuration(seconds: number, precise = false): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "--:--";
  // Round first so 89.99 s reads 1:30, not 1:29.
  seconds = precise ? Math.round(seconds * 10) / 10 : Math.round(seconds);
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  const ss = precise ? s.toFixed(1).padStart(4, "0") : Math.floor(s).toString().padStart(2, "0");
  return h > 0 ? `${h}:${m.toString().padStart(2, "0")}:${ss}` : `${m}:${ss}`;
}

export function formatEta(seconds: number | null): string {
  if (seconds == null) return "calculating…";
  if (seconds < 1) return "< 1 s";
  if (seconds < 60) return `${Math.ceil(seconds)} s`;
  return `${Math.floor(seconds / 60)} min ${Math.ceil(seconds % 60)} s`;
}

export function formatBitrate(bps: number | null): string {
  return bps ? `${Math.round(bps / 1000)} kbps` : "—";
}

export function channelLabel(n: number): string {
  return n === 1 ? "Mono" : n === 2 ? "Stereo" : `${n} ch`;
}

export function speedLabel(speed: number): string {
  return `${Number(speed.toFixed(2))}x`;
}
