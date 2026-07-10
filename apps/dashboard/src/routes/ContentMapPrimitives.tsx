import type { ReactNode } from "react";

export function ContentMapColumn({ children, icon, subtitle, title }: { children: ReactNode; icon: ReactNode; subtitle: string; title: string }) {
  return <div className="relative z-10 rounded-md border border-line bg-white p-4 shadow-sm"><div className="mb-3 flex items-start gap-3"><div className="rounded-md border border-line bg-surface p-2 text-action">{icon}</div><div><h2 className="text-base font-semibold text-ink">{title}</h2><p className="mt-1 text-xs text-slate-500">{subtitle}</p></div></div>{children}</div>;
}

export function ContentMapConnectors() {
  return <div className="pointer-events-none absolute inset-x-0 top-24 z-0 hidden h-72 lg:block"><div className="absolute left-[31.5%] top-10 h-px w-[4.5%] bg-action/25" /><div className="absolute left-[31.5%] top-24 h-px w-[4.5%] bg-action/20" /><div className="absolute left-[31.5%] top-[9.5rem] h-px w-[4.5%] bg-action/15" /><div className="absolute right-[31.5%] top-12 h-px w-[4.5%] bg-success/25" /><div className="absolute right-[31.5%] top-28 h-px w-[4.5%] bg-success/20" /><div className="absolute right-[31.5%] top-44 h-px w-[4.5%] bg-success/15" /></div>;
}

export function ContentSectionRow({ badge, icon, meta, subtitle, summary, title, tone = "public" }: { badge?: string; icon: ReactNode; meta?: string; subtitle: string; summary?: string; title: string; tone?: "public" | "dev" }) {
  const iconClass = tone === "dev" ? "bg-success/10 text-success" : "bg-action/10 text-action";
  return <li className="rounded-md border border-line bg-white p-2.5 shadow-sm"><div className="flex items-center gap-2.5"><div className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-md ${iconClass}`}>{icon}</div><div className="min-w-0 flex-1"><div className="flex items-center justify-between gap-2"><div className="min-w-0"><div className="truncate text-sm font-semibold leading-5 text-ink" title={title}>{title}</div><div className="mt-0.5 truncate text-xs text-slate-500">{subtitle}</div></div><div className="flex shrink-0 items-center gap-2">{badge ? <span className="rounded-md bg-success/10 px-2 py-1 text-xs font-semibold text-success">{badge}</span> : null}{meta ? <span className="max-w-20 truncate text-right text-xs text-slate-500">{meta}</span> : null}</div></div>{summary ? <p className="mt-2 line-clamp-1 text-xs leading-5 text-slate-600">{summary}</p> : null}</div></div></li>;
}
