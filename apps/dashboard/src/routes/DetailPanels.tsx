import { useQuery } from "@tanstack/react-query";

import {
  ActionObject,
  Evidence,
  getAction,
  getEvidenceById,
  getOpportunities,
  Opportunity
} from "../lib/api";
import { LoadingBand } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import { LinkedTraceLine } from "../components/TraceLine";
import {
  ActionHumanReviewControls,
  ActionPreviewControls,
  ActionReviewGatePanel,
  ActionValidationControls
} from "./ActionObjectPanels";

export function ActionDetailSurface({ actionId }: { actionId: string }) {
  const action = useQuery({
    queryKey: ["actions", actionId],
    queryFn: () => getAction(actionId)
  });

  if (action.isLoading) return <LoadingBand />;
  if (action.error) return <ErrorState />;

  if (action.data) return <ActionDetail action={action.data} />;
  return <ErrorState />;
}

export function OpportunityDetailSurface({ opportunityId }: { opportunityId: string }) {
  const opportunities = useQuery({ queryKey: ["opportunities"], queryFn: getOpportunities });

  if (opportunities.isLoading) return <LoadingBand />;
  if (opportunities.error) return <ErrorState />;

  const opportunity = (opportunities.data ?? []).find((item) => item.id === opportunityId);
  if (opportunity) return <OpportunityDetail opportunity={opportunity} />;
  return <ErrorState />;
}

function ActionDetail({ action }: { action: ActionObject }) {
  const visibleAuditEvents = action.audit_events.slice(0, 6);
  const hiddenAuditEventCount = Math.max(0, action.audit_events.length - visibleAuditEvents.length);

  return (
    <main className="mx-auto max-w-5xl px-4 py-6 lg:px-8">
      <h1 className="text-2xl font-semibold tracking-normal">{action.title}</h1>
      <div className="mt-3 flex flex-wrap gap-2">
        <StatusBadge value={action.status} />
        <StatusBadge value={action.validation_status} />
        <StatusBadge value={action.risk} />
      </div>
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Dowody i diagnoza" />
        <p className="text-sm leading-6 text-slate-700">{action.human_diagnosis}</p>
        <div className="mt-4 text-xs text-slate-600">
          <LinkedTraceLine label="Dowody" values={action.evidence_ids} kind="evidence" />
        </div>
        <ActionReviewGatePanel action={action} />
        <ActionHumanReviewControls action={action} />
        <ActionPreviewControls action={action} />
        <ActionValidationControls action={action} />
      </section>
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Podgląd payloadu" />
        <ActionPayloadPreviewSummary action={action} />
        <pre className="max-h-96 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100">
          {JSON.stringify(action.payload, null, 2)}
        </pre>
      </section>
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Historia audytu" />
        {action.audit_events.length === 0 ? (
          <p className="text-sm text-slate-600">Brak zapisanych zdarzeń audytu.</p>
        ) : (
          <div className="grid gap-3">
            {hiddenAuditEventCount > 0 ? (
              <p className="text-xs text-slate-500">
                Pokazano 6 najnowszych z {action.audit_events.length} zdarzeń audytu.
              </p>
            ) : null}
            {visibleAuditEvents.map((event) => (
              <div key={event.id} className="rounded-md border border-line p-3 text-sm">
                <div className="font-medium">{event.event_type}</div>
                <div className="mt-1 text-slate-600">{event.summary}</div>
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}

function ActionPayloadPreviewSummary({ action }: { action: ActionObject }) {
  const previewItems = Array.isArray(action.payload.payload_preview)
    ? action.payload.payload_preview.filter(isRecord)
    : [];
  if (previewItems.length === 0) {
    return null;
  }
  return (
    <div className="mb-4 grid gap-3">
      {prioritizePayloadPreviewItems(previewItems)
        .slice(0, 4)
        .map((item, index) => (
          <article
            key={payloadPreviewKey(item, index)}
            className="rounded-md border border-line bg-slate-50 p-3"
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h3 className="text-sm font-semibold text-ink">Review-only podgląd</h3>
                <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
                  {previewIssueLabel(item)}
                </p>
              </div>
              <StatusBadge value={item.apply_allowed === true ? "ready" : "blocked"} />
            </div>
            <div className="mt-3 grid gap-1.5 text-xs text-slate-700">
              <div>
                Apply zablokowany: {item.apply_allowed === true ? "nie" : "tak"}; mutacja API:{" "}
                {item.api_mutation_ready === true ? "gotowa" : "zablokowana"}
              </div>
              <PreviewValues
                label="Przykładowe produkty"
                values={asStringArray(item.sample_product_ids)}
              />
              <PreviewValues label="Tytuły próbek" values={asStringArray(item.sample_titles)} />
            </div>
          </article>
        ))}
    </div>
  );
}

function prioritizePayloadPreviewItems(items: Array<Record<string, unknown>>) {
  return [...items].sort((left, right) => {
    const leftHasSamples = asStringArray(left.sample_product_ids).length > 0;
    const rightHasSamples = asStringArray(right.sample_product_ids).length > 0;
    if (leftHasSamples === rightHasSamples) return 0;
    return leftHasSamples ? -1 : 1;
  });
}

function PreviewValues({ label, values }: { label: string; values: string[] }) {
  if (values.length === 0) {
    return (
      <div>
        {label}: <span className="text-slate-500">brak</span>
      </div>
    );
  }
  return (
    <div>
      {label}: {values.slice(0, 4).join(", ")}
      {values.length > 4 ? ` +${values.length - 4}` : ""}
    </div>
  );
}

function previewIssueLabel(item: Record<string, unknown>) {
  const issueType = typeof item.issue_type === "string" ? item.issue_type : "problem";
  const attribute =
    typeof item.affected_attribute === "string" ? item.affected_attribute : "atrybut";
  return `${issueType} / ${attribute}`;
}

function payloadPreviewKey(item: Record<string, unknown>, index: number) {
  return typeof item.id === "string" ? item.id : `payload-preview-${index}`;
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function EvidenceDetailSurface({ evidenceId }: { evidenceId: string }) {
  const evidence = useQuery({
    queryKey: ["evidence", evidenceId],
    queryFn: () => getEvidenceById(evidenceId),
    enabled: evidenceId.length > 0
  });

  if (evidence.isLoading) return <LoadingBand />;
  if (evidence.error || !evidence.data) return <ErrorState />;
  return <EvidenceDetail evidence={evidence.data} />;
}

function EvidenceDetail({ evidence }: { evidence: Evidence }) {
  return (
    <main className="mx-auto max-w-5xl px-4 py-6 lg:px-8">
      <h1 className="break-words text-2xl font-semibold tracking-normal">{evidence.id}</h1>
      <div className="mt-3 flex flex-wrap gap-2">
        <StatusBadge value={evidence.source_connector} />
        <StatusBadge value={evidence.source_type} />
        <StatusBadge value={evidence.freshness.state} />
      </div>
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Podsumowanie dowodu" />
        <p className="text-sm leading-6 text-slate-700">{evidence.summary}</p>
        <div className="mt-4 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
          <div>Źródło: {evidence.source_connector}</div>
          <div>Typ źródła: {evidence.source_type}</div>
          <div>ID źródła: {evidence.source_id}</div>
          <div>Zebrano: {evidence.collected_at}</div>
          <div>Świeżość: {evidence.freshness.state}</div>
          <div>Referencja raw: {evidence.raw_ref ?? "brak"}</div>
        </div>
      </section>
    </main>
  );
}

function OpportunityDetail({ opportunity }: { opportunity: Opportunity }) {
  return (
    <main className="mx-auto max-w-5xl px-4 py-6 lg:px-8">
      <h1 className="text-2xl font-semibold tracking-normal">{opportunity.title}</h1>
      <div className="mt-3 flex flex-wrap gap-2">
        <StatusBadge value={opportunity.domain} />
        <StatusBadge value={opportunity.risk} />
      </div>
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Diagnoza" />
        <p className="text-sm leading-6 text-slate-700">{opportunity.human_diagnosis}</p>
        <div className="mt-4 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
          <div>Dowody: {opportunity.evidence_ids.join(", ")}</div>
          <div>Źródła: {opportunity.source_connectors.join(", ")}</div>
        </div>
      </section>
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Surowe metryki" />
        {opportunity.metrics.length === 0 ? (
          <p className="text-sm text-slate-600">Brak realnych metric facts.</p>
        ) : (
          <pre className="max-h-96 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100">
            {JSON.stringify(opportunity.metrics, null, 2)}
          </pre>
        )}
      </section>
    </main>
  );
}

function SectionHeading({ title }: { title: string }) {
  return <h2 className="mb-3 text-sm font-semibold uppercase tracking-normal text-slate-600">{title}</h2>;
}

function ErrorState() {
  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="rounded-md border border-risk/30 bg-risk/10 p-4 text-sm text-risk">
        WILQ API is not reachable.
      </div>
    </main>
  );
}
