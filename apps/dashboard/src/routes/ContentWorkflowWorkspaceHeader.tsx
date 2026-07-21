import type { ReactNode } from "react";

export function ContentWorkflowWorkspaceHeader({ children }: { children?: ReactNode }) {
  return (
    <header className="mb-3 flex flex-wrap items-end justify-between gap-3 sm:mb-4">
      <div className="hidden lg:block">
        <h1 className="text-2xl font-semibold tracking-tight text-ink sm:text-3xl">Treści i SEO</h1>
      </div>
      {children}
    </header>
  );
}
