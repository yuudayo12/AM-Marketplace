import type { ReactNode, SVGProps } from "react";

export function Panel({
  step,
  title,
  subtitle,
  right,
  children,
  className = "",
}: {
  step?: string;
  title: string;
  subtitle?: string;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`animate-fade-up rounded-2xl border border-ink-700 bg-ink-800/80 shadow-panel backdrop-blur ${className}`}>
      <header className="flex items-start justify-between gap-4 border-b border-ink-700/70 px-5 py-4 sm:px-6">
        <div className="flex items-center gap-3">
          {step && (
            <span className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-ink-700 font-mono text-xs font-semibold text-violet-300">
              {step}
            </span>
          )}
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-slate-100">{title}</h2>
            {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
          </div>
        </div>
        {right}
      </header>
      <div className="p-5 sm:p-6">{children}</div>
    </section>
  );
}

export function Stat({ label, value, mono = true }: { label: string; value: ReactNode; mono?: boolean }) {
  return (
    <div className="rounded-xl border border-ink-700 bg-ink-850 px-3.5 py-2.5">
      <div className="text-[10px] font-medium uppercase tracking-[0.16em] text-slate-500">{label}</div>
      <div className={`mt-1 truncate text-sm text-slate-100 ${mono ? "font-mono" : ""}`}>{value}</div>
    </div>
  );
}

export function Alert({ kind, children, onClose }: { kind: "error" | "success" | "info"; children: ReactNode; onClose?: () => void }) {
  const styles = {
    error: "border-rose-500/40 bg-rose-500/10 text-rose-200",
    success: "border-emerald-500/40 bg-emerald-500/10 text-emerald-200",
    info: "border-azure-500/40 bg-azure-500/10 text-azure-300",
  }[kind];
  const icon = { error: <IconAlert />, success: <IconCheck />, info: <IconInfo /> }[kind];
  return (
    <div role={kind === "error" ? "alert" : "status"} className={`animate-fade-up flex items-start gap-3 rounded-xl border px-4 py-3 text-sm ${styles}`}>
      <span className="mt-0.5 shrink-0">{icon}</span>
      <div className="min-w-0 flex-1 leading-relaxed">{children}</div>
      {onClose && (
        <button onClick={onClose} className="shrink-0 rounded p-0.5 opacity-70 hover:opacity-100" aria-label="Dismiss">
          <IconX />
        </button>
      )}
    </div>
  );
}

export function Spinner({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity=".25" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

/* ------------------------------------------------------------------ icons */

type P = SVGProps<SVGSVGElement>;
const base = (p: P) => ({ width: 18, height: 18, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, "aria-hidden": true, ...p });

export const IconUpload = (p: P) => (<svg {...base(p)}><path d="M12 16V4m0 0-4 4m4-4 4 4" /><path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" /></svg>);
export const IconLink = (p: P) => (<svg {...base(p)}><path d="M10 14a4 4 0 0 0 5.66 0l3-3a4 4 0 0 0-5.66-5.66l-1 1" /><path d="M14 10a4 4 0 0 0-5.66 0l-3 3a4 4 0 0 0 5.66 5.66l1-1" /></svg>);
export const IconPlay = (p: P) => (<svg {...base(p)} fill="currentColor" stroke="none"><path d="M8 5.5v13a1 1 0 0 0 1.53.85l10.2-6.5a1 1 0 0 0 0-1.7L9.53 4.65A1 1 0 0 0 8 5.5Z" /></svg>);
export const IconPause = (p: P) => (<svg {...base(p)} fill="currentColor" stroke="none"><rect x="6" y="5" width="4" height="14" rx="1" /><rect x="14" y="5" width="4" height="14" rx="1" /></svg>);
export const IconDownload = (p: P) => (<svg {...base(p)}><path d="M12 4v12m0 0-4-4m4 4 4-4" /><path d="M4 20h16" /></svg>);
export const IconCheck = (p: P) => (<svg {...base(p)}><path d="m5 12 5 5 9-10" /></svg>);
export const IconAlert = (p: P) => (<svg {...base(p)}><path d="M12 9v4m0 4h.01" /><path d="M10.3 3.9 2.4 17.5A2 2 0 0 0 4.1 20.5h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" /></svg>);
export const IconInfo = (p: P) => (<svg {...base(p)}><circle cx="12" cy="12" r="9" /><path d="M12 11v5m0-8h.01" /></svg>);
export const IconX = (p: P) => (<svg {...base(p)}><path d="M6 6l12 12M18 6 6 18" /></svg>);
export const IconLock = (p: P) => (<svg {...base(p)}><rect x="5" y="11" width="14" height="9" rx="2" /><path d="M8 11V8a4 4 0 0 1 8 0v3" /></svg>);
export const IconBolt = (p: P) => (<svg {...base(p)}><path d="M13 3 4 14h7l-1 7 9-11h-7l1-7Z" /></svg>);
export const IconMusic = (p: P) => (<svg {...base(p)}><path d="M9 18V5l12-2v13" /><circle cx="6" cy="18" r="3" /><circle cx="18" cy="16" r="3" /></svg>);
export const IconTrash = (p: P) => (<svg {...base(p)}><path d="M4 7h16M10 11v6m4-6v6M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12M9 7V4h6v3" /></svg>);
