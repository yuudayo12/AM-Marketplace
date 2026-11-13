export function Header({ engine }: { engine: string | null }) {
  return (
    <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="flex items-center gap-4">
        <div className="relative grid h-12 w-12 place-items-center rounded-2xl bg-gradient-to-br from-violet-500 to-azure-500 shadow-glow">
          <div className="flex h-5 items-center gap-[3px]">
            {[0.5, 0.9, 0.6, 1, 0.7].map((h, i) => (
              <span key={i} className="w-[3px] origin-center animate-bar-pulse rounded-full bg-white" style={{ height: `${h * 100}%`, animationDelay: `${i * 0.12}s` }} />
            ))}
          </div>
        </div>
        <div>
          <h1 className="bg-gradient-to-r from-white via-violet-200 to-azure-300 bg-clip-text text-2xl font-extrabold tracking-[0.22em] text-transparent sm:text-3xl">
            SPEEDWAVE
          </h1>
          <p className="text-sm text-slate-400">Professional Audio Speed Converter</p>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2 text-[11px] font-medium uppercase tracking-[0.12em]">
        <span className="rounded-full border border-ink-600 bg-ink-800 px-3 py-1 text-slate-400">FFmpeg</span>
        <span className="rounded-full border border-violet-500/40 bg-violet-500/10 px-3 py-1 text-violet-300">
          Rubber Band {engine ?? "…"}
        </span>
        <span className="flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-emerald-300">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" /> Pitch locked
        </span>
      </div>
    </header>
  );
}
