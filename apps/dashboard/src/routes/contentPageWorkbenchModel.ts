import type {
  ContentOpportunityEnrichment,
  ContentWorkItemQueueCandidate
} from "../lib/api";
import type { WordPressAuthoringDevContentObject } from "./contentWorkflowTarget";
import type { ContentWorkflowSnapshot } from "./contentWorkflowRuntime";

function unique(values: string[]) {
  return [...new Set(values)];
}

export function environmentLabel(value: string) {
  try {
    const url = new URL(value);
    return url.hostname.replace(/^www\./, "");
  } catch {
    return value.replace(/^https?:\/\//, "").replace(/\/.*$/, "");
  }
}

export function planningPageAssetsReady(
  pageAssets:
    | {
        title?: string | null;
        h1?: string | null;
        lead?: string | null;
        meta_title?: string | null;
        meta_description?: string | null;
      }
    | null
    | undefined
): boolean {
  return Boolean(
    pageAssets &&
      [
        pageAssets.title,
        pageAssets.h1,
        pageAssets.lead,
        pageAssets.meta_title,
        pageAssets.meta_description
      ].every((value) => Boolean(value?.trim()))
  );
}

export function contentMetricTilesForWorkbench(
  item: ContentWorkflowSnapshot["preflight"]["item"],
  devPage: WordPressAuthoringDevContentObject | null
) {
  const wordpressSectionCount = item.wordpress_section_count ?? item.wordpress_section_headings.length;
  return [
    { label: "Dowody", value: `${unique(item.evidence_ids).length}` },
    { label: "Źródła", value: `${unique(item.source_connectors).length}` },
    { label: "Sekcje WP", value: wordpressSectionCount ? `${wordpressSectionCount}` : "brak" },
    { label: "Sekcje dev", value: devPage ? `${devPage.section_count}` : "brak" }
  ];
}

export function contentSignalRows(
  data: ContentWorkflowSnapshot,
  enrichment: ContentOpportunityEnrichment | null,
  candidate: ContentWorkItemQueueCandidate | undefined
) {
  const brief = data.salesBrief.sales_brief_result.brief;
  const rows: { label: string; summary: string; tone: string }[] = [];
  if (candidate?.reason) rows.push({ label: "Decyzja", summary: candidate.reason, tone: "border-action/20 bg-action/5" });
  if (brief?.source_facts[0]) rows.push({ label: sourceConnectorLabel(brief.source_facts[0].source_connector), summary: brief.source_facts[0].summary, tone: "border-success/20 bg-success/5" });
  if (enrichment?.source_facts[0]) rows.push({ label: enrichment.source_facts[0].label, summary: enrichment.source_facts[0].summary, tone: "border-wait/25 bg-wait/10" });
  if (brief?.signal_quality.reason) rows.push({ label: "Jakość briefu", summary: brief.signal_quality.reason, tone: "border-line bg-surface" });
  if (!rows.length) rows.push({ label: "Następny krok", summary: data.preflight.preflight_verdict.next_step, tone: "border-line bg-surface" });
  return rows.slice(0, 4);
}

export function queryChipsForWorkbench(
  data: ContentWorkflowSnapshot,
  enrichment: ContentOpportunityEnrichment | null,
  candidate: ContentWorkItemQueueCandidate | undefined
) {
  const item = data.preflight.item;
  const brief = data.salesBrief.sales_brief_result.brief;
  const candidates = [item.topic, candidate?.topic, brief?.search_intent, brief?.buyer_problem, ...(brief?.source_facts.map((fact) => fact.summary) ?? []), ...(enrichment?.source_facts.map((fact) => fact.summary) ?? [])];
  const chips = candidates.flatMap((value) => extractReadablePhrases(value ?? "")).filter((value) => value.length >= 4 && value.length <= 34);
  return unique(chips).slice(0, 5);
}

function extractReadablePhrases(value: string) {
  const quoted = [...value.matchAll(/"([^"]+)"/g)].map((match) => match[1] ?? "");
  if (quoted.length) return quoted;
  return value.split(/[;,.|/]/).map((part) => part.trim().replace(/\s+/g, " ")).filter(Boolean).slice(0, 2);
}

export function blockedClaimsForWorkbench(data: ContentWorkflowSnapshot) {
  const blocked = data.claimLedger.entries.filter((entry) => entry.status === "blocked" || entry.status === "blocked_until_measurement");
  return blocked.length ? blocked.slice(0, 4) : data.claimLedger.entries.filter((entry) => entry.status === "needs_human_review").slice(0, 4);
}

export function evidenceRowsForWorkbench(data: ContentWorkflowSnapshot, enrichment: ContentOpportunityEnrichment | null) {
  const brief = data.salesBrief.sales_brief_result.brief;
  const rows = [
    ...(brief?.source_facts.map((fact) => ({ label: sourceConnectorLabel(fact.source_connector), summary: fact.summary })) ?? []),
    ...(enrichment?.source_facts.map((fact) => ({ label: fact.label, summary: fact.summary })) ?? [])
  ];
  if (rows.length) return rows.slice(0, 5);
  return unique(data.preflight.item.evidence_ids).slice(0, 5).map((evidenceId) => ({ label: "Dowód WILQ", summary: evidenceId }));
}

function sourceConnectorLabel(connector: string) {
  const labels: Record<string, string> = {
    google_search_console: "GSC",
    wordpress_ekologus: "WordPress",
    ahrefs: "Ahrefs",
    google_analytics_4: "GA4",
    google_ads: "Google Ads"
  };
  return labels[connector] ?? connector;
}
