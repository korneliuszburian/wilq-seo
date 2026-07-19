import { BarChart3, Code2, Globe2, Layers3, Megaphone, Search, Stamp } from "lucide-react";
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
  const sourceItems = contentSourceStatusItems(data);
  return <div className="mb-3 flex gap-2 overflow-x-auto pb-1 sm:grid sm:grid-cols-2 sm:gap-3 lg:grid-cols-5">
    <SourceStatusChip icon={<Globe2 aria-hidden="true" size={18} />} label="Public" status={publicUrl ? environmentLabel(publicUrl) : "brak URL"} tone="success" />
    <SourceStatusChip icon={<Code2 aria-hidden="true" size={18} />} label="Dev" status={devPage ? environmentLabel(devPage.link) : profile?.dev_content.status ?? "sprawdzam"} tone={devPage ? "success" : "wait"} />
    {sourceItems.map((source) => (
      <SourceStatusChip key={source.id} icon={source.icon} label={source.label} status={source.status} tone={source.tone} />
    ))}
    <SourceStatusChip icon={<Stamp aria-hidden="true" size={18} />} label="WP dev draft" status={devPage ? `${devPage.section_count} sekcji` : "czeka"} tone={devPage ? "success" : "wait"} />
  </div>;
}

export type ContentSourceStatusItem = {
  id: string;
  label: string;
  status: string;
  tone: "success" | "wait";
  icon: ReactNode;
};

export function contentSourceStatusItems(data: ContentWorkflowSnapshot): ContentSourceStatusItem[] {
  const item = data.preflight.item;
  const connectorLabels: Record<string, { label: string; icon: ReactNode }> = {
    google_search_console: { label: "GSC", icon: <Search aria-hidden="true" size={18} /> },
    google_analytics_4: { label: "GA4", icon: <BarChart3 aria-hidden="true" size={18} /> },
    google_ads: { label: "Ads", icon: <Megaphone aria-hidden="true" size={18} /> },
    ahrefs: { label: "Ahrefs", icon: <Layers3 aria-hidden="true" size={18} /> }
  };
  return item.source_connectors
    .map((id) => {
      const definition = connectorLabels[id];
      if (!definition) return null;
      const stale = data.freshnessAssessment.stale_connector_ids.includes(id);
      const blocked = data.freshnessAssessment.blocked_connector_ids.includes(id);
      return {
        id,
        ...definition,
        status: blocked ? "zablokowane" : stale ? "wymaga odświeżenia" : "w dowodach",
        tone: blocked || stale ? "wait" : "success"
      } satisfies ContentSourceStatusItem;
    })
    .filter((item): item is ContentSourceStatusItem => item !== null);
}

function SourceStatusChip({ icon, label, status, tone }: { icon: ReactNode; label: string; status: string; tone: "success" | "wait" }) {
  const dotClass = tone === "success" ? "bg-success" : "bg-wait";
  return <div className="flex h-10 min-w-[156px] items-center justify-between gap-2 rounded-md border border-line bg-white px-3 text-xs shadow-sm sm:h-12 sm:min-w-0 sm:text-sm">
    <div className="flex min-w-0 items-center gap-2"><span className="shrink-0 text-action">{icon}</span><span className="truncate font-semibold leading-5 text-ink">{label}</span></div>
    <div className="flex shrink-0 items-center gap-2 text-xs text-slate-600"><span className={`h-2 w-2 rounded-full ${dotClass}`} /><span className="max-w-32 truncate">{status}</span></div>
  </div>;
}

function environmentLabel(value: string) {
  try { return new URL(value).hostname.replace(/^www\./, ""); }
  catch { return value.replace(/^https?:\/\//, "").replace(/\/.*$/, ""); }
}
