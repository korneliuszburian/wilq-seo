import { ArrowRight, ExternalLink, FileText } from "lucide-react";
import type { ReactNode } from "react";

type ContentPageIdentityCardProps = {
  pageTitle: string;
  publicUrl: string;
  sourceSummary: string;
  recommendedModeLabel: string;
  fallbackDescription: string;
  children: ReactNode;
};

export function ContentPageIdentityCard({
  pageTitle,
  publicUrl,
  sourceSummary,
  recommendedModeLabel,
  fallbackDescription,
  children
}: ContentPageIdentityCardProps) {
  return (
    <div className="rounded-md border border-line bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 gap-4">
          <div className="hidden h-12 w-12 shrink-0 items-center justify-center rounded-full bg-action/10 text-action sm:flex">
            <FileText aria-hidden="true" size={22} />
          </div>
          <div className="min-w-0">
            <h2 className="text-2xl font-semibold tracking-normal text-ink">{pageTitle}</h2>
            {publicUrl ? (
              <a
                href={publicUrl}
                target="_blank"
                rel="noreferrer"
                className="mt-2 inline-flex max-w-full items-center gap-2 truncate rounded-md bg-action/10 px-2 py-1 text-sm font-semibold text-action"
              >
                {publicUrl}
                <ExternalLink aria-hidden="true" size={14} />
              </a>
            ) : null}
            <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-700">
              {sourceSummary || fallbackDescription}
            </p>
          </div>
        </div>
        <button
          type="button"
          className="inline-flex h-10 items-center gap-2 rounded-md border border-action/35 bg-white px-3 text-sm font-semibold text-action"
        >
          {recommendedModeLabel}
          <ArrowRight aria-hidden="true" size={15} />
        </button>
      </div>
      {children}
    </div>
  );
}
