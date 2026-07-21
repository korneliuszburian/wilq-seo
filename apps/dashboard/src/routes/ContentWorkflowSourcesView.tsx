import type { ReactNode } from "react";

import type { ContentWorkflowSnapshot } from "./contentWorkflowRuntime";

const CONNECTOR_LABELS: Record<string, string> = {
  google_search_console: "Google Search Console",
  google_analytics_4: "GA4",
  google_ads: "Google Ads",
  ahrefs: "Ahrefs",
  localo: "Localo",
  wordpress_ekologus: "WordPress Ekologus",
  wordpress_sklep: "WordPress sklep",
  merchant_center: "Merchant Center"
};

type ContentWorkflowSourcesViewProps = {
  data: ContentWorkflowSnapshot;
};

export function ContentWorkflowSourcesView({ data }: ContentWorkflowSourcesViewProps) {
  const item = data.preflight.item;
  const revision = data.revisionWorkspace.latest_revision;
  const evidenceIds = unique([
    ...(item.evidence_ids ?? []),
    ...(revision?.sections.flatMap((section) => section.evidence_ids ?? []) ?? []),
    ...(revision?.faq?.flatMap((faq) => faq.evidence_ids ?? []) ?? []),
    ...(revision?.cta_blocks?.flatMap((cta) => cta.evidence_ids ?? []) ?? []),
    ...(revision?.internal_links?.flatMap((link) => link.evidence_ids ?? []) ?? [])
  ]);
  const claimCounts = claimLedgerCounts(data);
  const sourceRows = sourceRowsFor(data);
  const limitations = contentLimitations(data, revision);
  const pageTitle = item.wordpress_title_or_h1 ?? item.final_canonical_url ?? item.intended_final_url ?? item.id;
  const pageUrl = item.source_public_url ?? item.final_canonical_url ?? item.intended_final_url ?? "adres niepotwierdzony";

  return (
    <section
      aria-labelledby="content-workflow-sources-title"
      className="mb-6 rounded-md border border-line bg-white p-4 shadow-sm sm:p-5"
      data-testid="content-workflow-sources-view"
    >
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line pb-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Źródła i ograniczenia</p>
          <h2 id="content-workflow-sources-title" className="mt-1 text-xl font-semibold text-ink">{pageTitle}</h2>
          <p className="mt-1 break-all text-sm text-slate-600">{pageUrl}</p>
        </div>
        <span className="rounded-md border border-line bg-surface px-3 py-2 text-xs font-semibold text-slate-600">
          Widok read-only
        </span>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <SourceGroup title="Źródła danych">
          <div className="space-y-2">
            {sourceRows.length ? sourceRows.map((source) => (
              <div key={source.id} className="flex items-center justify-between gap-3 rounded-md border border-line bg-surface px-3 py-2 text-sm">
                <span className="font-semibold text-ink">{source.label}</span>
                <span className={source.tone === "good" ? "text-success" : "text-wait"}>{source.status}</span>
              </div>
            )) : <p className="text-sm text-slate-600">Brak rozpoznanych konektorów dla tej strony.</p>}
          </div>
        </SourceGroup>

        <SourceGroup title="Dowody i twierdzenia">
          <div className="grid gap-2 sm:grid-cols-3">
            <SummaryTile label="Dowody" value={evidenceIds.length} />
            <SummaryTile label="Do review" value={claimCounts.review} />
            <SummaryTile label="Zablokowane" value={claimCounts.blocked} />
          </div>
          <p className="mt-3 text-xs leading-5 text-slate-600">
            Identyfikatory dowodów są przypisane do bieżącego odczytu i zapisanej rewizji; nie są metryką jakości treści.
          </p>
        </SourceGroup>

        <SourceGroup title="Rewizja i pochodzenie">
          {revision ? (
            <dl className="grid gap-2 text-sm sm:grid-cols-2">
              <Definition label="Rewizja" value={revision.revision_id} />
              <Definition label="Digest" value={revision.content_digest} />
              <Definition label="Kontekst" value={data.revisionWorkspace.context_current ? "aktualny" : "wymaga odświeżenia"} />
              <Definition label="Materiały źródłowe" value={String(revision.source_material_ids?.length ?? 0)} />
            </dl>
          ) : (
            <p className="text-sm text-slate-600">Brak zapisanej rewizji dla tej strony.</p>
          )}
        </SourceGroup>

        <SourceGroup title="Ograniczenia interpretacji">
          <ul className="space-y-2 text-sm leading-6 text-slate-700">
            {limitations.map((limitation) => <li key={limitation} className="rounded-md border border-wait/20 bg-wait/5 px-3 py-2">{limitation}</li>)}
          </ul>
        </SourceGroup>
      </div>

      <details className="mt-4 rounded-md border border-line bg-surface px-3 py-2">
        <summary className="cursor-pointer text-sm font-semibold text-action">Pokaż identyfikatory lineage</summary>
        <div className="mt-3 grid gap-3 text-xs text-slate-600 sm:grid-cols-2">
          <Definition label="Evidence IDs" value={evidenceIds.join(", ") || "brak"} />
          <Definition label="Karty wiedzy" value={revision?.knowledge_card_ids?.join(", ") || "brak"} />
          <Definition label="Materiały" value={revision?.source_material_ids?.join(", ") || "brak"} />
          <Definition label="Konektory" value={item.source_connectors.map((id) => CONNECTOR_LABELS[id] ?? id).join(", ") || "brak"} />
        </div>
      </details>
    </section>
  );
}

function SourceGroup({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-md border border-line bg-white p-3" aria-label={title}>
      <h3 className="text-sm font-semibold text-ink">{title}</h3>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function SummaryTile({ label, value }: { label: string; value: number }) {
  return <div className="rounded-md border border-line bg-surface px-3 py-2"><div className="text-xs text-slate-500">{label}</div><div className="mt-1 text-lg font-semibold text-ink">{value}</div></div>;
}

function Definition({ label, value }: { label: string; value: string }) {
  return <div className="min-w-0"><dt className="font-semibold text-slate-500">{label}</dt><dd className="mt-1 break-all text-slate-700">{value}</dd></div>;
}

function sourceRowsFor(data: ContentWorkflowSnapshot) {
  const quality = data.freshnessAssessment.connector_quality_states ?? {};
  const stale = new Set(data.freshnessAssessment.stale_connector_ids ?? []);
  const blocked = new Set(data.freshnessAssessment.blocked_connector_ids ?? []);
  return data.preflight.item.source_connectors.map((id) => {
    const state = quality[id];
    const status = blocked.has(id) ? "zablokowane" : stale.has(id) ? "wymaga odświeżenia" : state === "partial" ? "odczyt częściowy" : state === "verified" ? "zweryfikowane" : "stan do sprawdzenia";
    return { id, label: CONNECTOR_LABELS[id] ?? id, status, tone: blocked.has(id) || stale.has(id) || state === "partial" ? "warn" as const : "good" as const };
  });
}

function claimLedgerCounts(data: ContentWorkflowSnapshot) {
  return data.claimLedger.entries.reduce(
    (counts, entry) => {
      if (entry.status === "blocked" || entry.status === "blocked_until_measurement") counts.blocked += 1;
      if (entry.status === "needs_human_review" || entry.strength === "weak") counts.review += 1;
      return counts;
    },
    { review: 0, blocked: 0 }
  );
}

function contentLimitations(data: ContentWorkflowSnapshot, revision: ContentWorkflowSnapshot["revisionWorkspace"]["latest_revision"]) {
  const limitations: string[] = [];
  const qualityStates = Object.entries(data.freshnessAssessment.connector_quality_states ?? {})
    .filter(([, state]) => state !== "verified" && state !== "unknown")
    .map(([id, state]) => `${CONNECTOR_LABELS[id] ?? id}: ${state === "partial" ? "odczyt częściowy" : "jakość do sprawdzenia"}`);
  limitations.push(...qualityStates);
  if (!data.preflight.item.metric_facts?.some((fact) => fact.source_connector === "google_analytics_4")) {
    limitations.push("Brak exact danych GA4 ogranicza ocenę zachowania i efektu.");
  }
  if (!revision) limitations.push("Brak zapisanej rewizji; lineage dotyczy bieżącego odczytu strony.");
  else if (!data.revisionWorkspace.context_current) limitations.push("Zapisana rewizja pochodzi ze starszego kontekstu i wymaga odświeżenia.");
  return limitations.length ? limitations : ["Brak dodatkowych ograniczeń w bieżącym odczycie."];
}

function unique(values: string[]) {
  return [...new Set(values)];
}
