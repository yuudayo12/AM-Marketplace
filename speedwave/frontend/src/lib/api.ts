export interface AppConfig {
  max_upload_mb: number;
  max_duration_minutes: number;
  file_ttl_minutes: number;
  input_formats: string[];
  input_extensions: string[];
  output_formats: OutputFormat[];
  mp3_bitrates: number[];
  speed: { default: number; min: number; max: number };
  quality_modes: { id: QualityMode; label: string; description: string }[];
  default_quality: QualityMode;
  r3_available: boolean;
  platform_import: { enabled: boolean; yt_dlp: string | null; js_runtime: boolean };
}

export interface ImportTask {
  id: string;
  url: string;
  kind: "direct" | "platform";
  platform: string | null;
  status: "downloading" | "analyzing" | "completed" | "failed" | "cancelled";
  stage: string;
  downloaded_bytes: number;
  total_bytes: number | null;
  progress: number | null;
  speed_bps: number | null;
  eta_seconds: number | null;
  error: string | null;
  source: Source | null;
}

export type OutputFormat = "mp3" | "ogg";
export type QualityMode = "studio" | "fast";

export interface Source {
  id: string;
  filename: string;
  size: number;
  origin: "upload" | "url" | "platform";
  format: string;
  codec: string;
  duration: number;
  sample_rate: number;
  channels: number;
  channel_layout: string | null;
  bit_rate: number | null;
  preview_url: string;
  waveform_url: string;
}

export interface JobSettings {
  speed: number;
  formats: OutputFormat[];
  mp3_bitrate: number;
  ogg_quality: number;
  quality: QualityMode;
  clip_protection: boolean;
}

export interface JobOutput {
  filename: string;
  mime: string;
  duration: number;
  sample_rate: number;
  channels: number;
  bit_rate: number | null;
  size: number;
  download_url: string;
  preview_url: string;
  waveform_url: string;
}

export type JobStatus = "queued" | "processing" | "finalizing" | "completed" | "failed" | "cancelled";

export interface Job {
  id: string;
  source_id: string;
  status: JobStatus;
  stage: string;
  progress: number;
  eta_seconds: number | null;
  elapsed_seconds: number | null;
  realtime_factor: number | null;
  error: string | null;
  settings: JobSettings & { engine: string };
  original_duration: number;
  expected_duration: number;
  outputs: Partial<Record<OutputFormat, JobOutput>>;
  duplicate?: boolean;
}

export const isActive = (s: JobStatus) => s === "queued" || s === "processing" || s === "finalizing";

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

async function parseError(res: Response): Promise<ApiError> {
  let msg = `Request failed (${res.status})`;
  try {
    const body = await res.json();
    if (typeof body.detail === "string") msg = body.detail;
    else if (Array.isArray(body.detail)) msg = body.detail.map((d: { msg: string }) => d.msg).join("; ");
  } catch {
    /* not JSON */
  }
  if (res.status === 413 && msg.startsWith("Request failed")) msg = "The file is too large.";
  return new ApiError(msg, res.status);
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, { credentials: "same-origin", ...init });
  } catch {
    throw new ApiError("Cannot reach the SpeedWave server. Is the backend running?", 0);
  }
  if (!res.ok) throw await parseError(res);
  return res.status === 204 ? (undefined as T) : res.json();
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  config: () => request<AppConfig>("/api/config"),
  health: () => request<{ ok: boolean; ffmpeg: string | null; rubberband_engine: string | null }>("/api/health"),
  importUrl: (url: string, signal?: AbortSignal) => request<Source>("/api/sources/url", { ...json({ url }), signal }),
  startImport: (url: string) => request<ImportTask>("/api/imports", json({ url })),
  getImport: (id: string) => request<ImportTask>(`/api/imports/${id}`),
  cancelImport: (id: string) => request<ImportTask>(`/api/imports/${id}/cancel`, { method: "POST" }),
  deleteSource: (id: string) => request<void>(`/api/sources/${id}`, { method: "DELETE" }),
  waveform: (url: string) => request<{ peaks: number[] }>(url).then((r) => r.peaks),
  createJob: (source_id: string, s: JobSettings) => request<Job>("/api/jobs", json({ source_id, ...s })),
  job: (id: string) => request<Job>(`/api/jobs/${id}`),
  cancelJob: (id: string) => request<Job>(`/api/jobs/${id}/cancel`, { method: "POST" }),

  /** Upload with real byte-level progress (fetch() cannot report upload progress). */
  upload(file: File, onProgress: (fraction: number) => void): { promise: Promise<Source>; abort: () => void } {
    const xhr = new XMLHttpRequest();
    const promise = new Promise<Source>((resolve, reject) => {
      xhr.open("POST", "/api/sources/upload");
      xhr.withCredentials = true;
      xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(e.loaded / e.total);
      xhr.onload = async () => {
        const res = new Response(xhr.responseText, { status: xhr.status });
        if (xhr.status >= 200 && xhr.status < 300) resolve(JSON.parse(xhr.responseText));
        else reject(await parseError(res));
      };
      xhr.onerror = () => reject(new ApiError("Upload failed: cannot reach the server.", 0));
      xhr.onabort = () => reject(new ApiError("Upload cancelled.", 0));
      const form = new FormData();
      form.append("file", file, file.name);
      xhr.send(form);
    });
    return { promise, abort: () => xhr.abort() };
  },
};
