import type { ReactNode } from "react";

export function ContentWorkflowWorkspaceHeader({ children }: { children?: ReactNode }) {
  return (
    <header className="mb-3 flex flex-wrap items-end justify-between gap-3 sm:mb-4">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-action">WILQ · Ekologus</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-ink sm:text-3xl">Treści i SEO</h1>
        <p className="mt-1 text-sm text-slate-600">Content workflow</p>
      </div>
      {children}
    </header>
  );
}
