import { Code2, Globe2, Layers3, Search, Stamp } from "lucide-react";
import type { ReactNode } from "react";

import type { WordPressAuthoringProfile } from "../lib/api";
import type { ContentWorkflowSnapshot } from "./contentWorkflowRuntime";
import type { WordPressAuthoringDevPage } from "./contentWorkflowTarget";

export function ContentSourceStatusBar({ data, devPage, profile }: {
  data: ContentWorkflowSnapshot;
  devPage: WordPressAuthoringDevPage | null;
  profile: WordPressAuthoringProfile | null;
}) {
  const item = data.preflight.item;
  const publicUrl = item.source_public_url ?? item.final_canonical_url ?? item.intended_final_url ?? "";
  const hasGsc = item.source_connectors.includes("google_search_console");
  const hasAhrefs = item.source_connectors.includes("ahrefs");
  return <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
    <SourceStatusChip icon={<Globe2 aria-hidden="true" size={18} />} label="Public" status={publicUrl ? environmentLabel(publicUrl) : "brak URL"} tone="success" />
    <SourceStatusChip icon={<Code2 aria-hidden="true" size={18} />} label="Dev" status={devPage ? environmentLabel(devPage.link) : profile?.dev_content.status ?? "sprawdzam"} tone={devPage ? "success" : "wait"} />
    <SourceStatusChip icon={<Search aria-hidden="true" size={18} />} label="GSC" status={hasGsc ? "w dowodach" : "brak"} tone={hasGsc ? "success" : "wait"} />
    <SourceStatusChip icon={<Layers3 aria-hidden="true" size={18} />} label="Ahrefs" status={hasAhrefs ? "pomocniczo" : "brak"} tone="wait" />
    <SourceStatusChip icon={<Stamp aria-hidden="true" size={18} />} label="WP dev draft" status={devPage ? `${devPage.section_count} sekcji` : "czeka"} tone={devPage ? "success" : "wait"} />
  </div>;
}

function SourceStatusChip({ icon, label, status, tone }: { icon: ReactNode; label: string; status: string; tone: "success" | "wait" }) {
  const dotClass = tone === "success" ? "bg-success" : "bg-wait";
  return <div className="flex h-12 items-center justify-between gap-3 rounded-md border border-line bg-white px-3 text-sm shadow-sm">
    <div className="flex min-w-0 items-center gap-2"><span className="shrink-0 text-action">{icon}</span><span className="truncate font-semibold leading-5 text-ink">{label}</span></div>
    <div className="flex shrink-0 items-center gap-2 text-xs text-slate-600"><span className={`h-2 w-2 rounded-full ${dotClass}`} /><span className="max-w-32 truncate">{status}</span></div>
  </div>;
}

function environmentLabel(value: string) {
  try { return new URL(value).hostname.replace(/^www\./, ""); }
  catch { return value.replace(/^https?:\/\//, "").replace(/\/.*$/, ""); }
}
