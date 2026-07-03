import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useState } from "react";

import {
  ActionObject,
  Evidence,
  getAction,
  getActionMutationReadiness,
  getEvidenceById,
  getOpportunities,
  Opportunity
} from "../lib/api";
import { LoadingBand } from "../components/OperatorPrimitives";
import { ActionPreviewCard } from "../components/ActionPreviewCard";
import { StatusBadge } from "../components/StatusBadge";
import {
  ActionHumanReviewControls,
  ActionPreviewControls,
  ActionReviewGatePanel,
  ActionValidationControls
} from "./ActionPanels";

export function ActionDetailSurface({ actionId }: { actionId: string }) {
  const action = useQuery({
    queryKey: ["actions", actionId],
    queryFn: () => getAction(actionId)
  });
  const mutationReadiness = useQuery({
    queryKey: ["actions", actionId, "mutation-readiness"],
    queryFn: () => getActionMutationReadiness(actionId)
  });

  if (action.isLoading) return <LoadingBand />;
  if (action.error) return <ErrorState />;

  if (action.data) {
    return (
      <ActionDetail
        action={action.data}
        mutationReadiness={mutationReadiness.data}
        mutationReadinessError={mutationReadiness.error}
        mutationReadinessLoading={mutationReadiness.isLoading}
      />
    );
  }
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

function ActionDetail({
  action,
  mutationReadiness,
  mutationReadinessError,
  mutationReadinessLoading
}: {
  action: ActionObject;
  mutationReadiness: Awaited<ReturnType<typeof getActionMutationReadiness>> | undefined;
  mutationReadinessError: unknown;
  mutationReadinessLoading: boolean;
}) {
  const visibleAuditEvents = action.audit_events.slice(0, 6);
  const hiddenAuditEventCount = Math.max(0, action.audit_events.length - visibleAuditEvents.length);

  return (
    <main className="mx-auto max-w-5xl px-4 py-6 lg:px-8">
      <h1 className="text-2xl font-semibold tracking-normal">{action.title}</h1>
      <div className="mt-3 flex flex-wrap gap-2">
        <StatusBadge value={action.status} label={action.status_label} />
        <StatusBadge value={action.validation_status} label={action.validation_status_label} />
        <StatusBadge value={action.risk} label={action.risk_label} />
      </div>
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Dowody i diagnoza" />
        <p className="text-sm leading-6 text-slate-700">{action.human_diagnosis}</p>
        <div className="mt-4 text-xs text-slate-600">
          Dowody: {action.evidence_summary_label}
        </div>
        <ActionReviewGatePanel action={action} />
        <ActionHumanReviewControls action={action} />
        <ActionPreviewControls action={action} />
        <ActionValidationControls action={action} />
      </section>
      <ActionMutationReadinessPanel
        loading={mutationReadinessLoading}
        error={mutationReadinessError}
        readiness={mutationReadiness}
      />
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Podgląd zmian" />
        <ActionChangePreviewSummary action={action} />
        <TechnicalDetailsPanel
          openLabel="Pokaż dane techniczne akcji"
          closeLabel="Ukryj dane techniczne akcji"
        >
          <pre className="mt-3 max-h-96 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100">
            {JSON.stringify(action.payload, null, 2)}
          </pre>
        </TechnicalDetailsPanel>
      </section>
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Historia audytu" />
        {action.audit_events.length === 0 ? (
          <p className="text-sm text-slate-600">
            Nie ma zapisanych zdarzeń audytu; nie traktuj akcji jako wykonanej.
          </p>
        ) : (
          <div className="grid gap-3">
            {hiddenAuditEventCount > 0 ? (
              <p className="text-xs text-slate-500">
                Pokazano 6 najnowszych z {action.audit_events.length} zdarzeń audytu.
              </p>
            ) : null}
            {visibleAuditEvents.map((event) => (
              <div key={event.id} className="rounded-md border border-line p-3 text-sm">
                <div className="font-medium">{event.event_type_label}</div>
                <div className="mt-1 text-slate-600">
                  {event.summary}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}

function ActionMutationReadinessPanel({
  loading,
  error,
  readiness
}: {
  loading: boolean;
  error: unknown;
  readiness: Awaited<ReturnType<typeof getActionMutationReadiness>> | undefined;
}) {
  if (loading) {
    return (
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Gotowość zapisu tej akcji" />
        <p className="text-sm leading-6 text-slate-600">
          WILQ sprawdza tryb, dowody, preview, confirm, impact check i adapter zapisu.
        </p>
      </section>
    );
  }
  if (error || !readiness) {
    return (
      <section className="mt-6 rounded-md border border-wait/30 bg-wait/10 p-4">
        <SectionHeading title="Gotowość zapisu tej akcji" />
        <p className="text-sm leading-6 text-slate-700">
          Nie udało się pobrać readiness zapisu. Nie traktuj tej akcji jako gotowej do zmian.
        </p>
      </section>
    );
  }
  const blockerLabels = readiness.blockers.slice(0, 6).map((blocker) => blocker.label);
  return (
    <section className="mt-6 rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <SectionHeading title="Gotowość zapisu tej akcji" />
          <p className="text-sm leading-6 text-slate-700">
            {readiness.operator_next_step}
          </p>
        </div>
        <StatusBadge
          value={readiness.vendor_write_possible ? "ready" : "blocked"}
          label={readiness.vendor_write_possible ? "write możliwy" : "write zablokowany"}
        />
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <ReadinessTile label="Tryb" value={readiness.mode_label} />
        <ReadinessTile
          label="Adapter"
          value={readiness.mutation_adapter ?? "brak adaptera"}
        />
        <ReadinessTile
          label="Próba zapisu"
          value={readiness.would_attempt_vendor_write ? "możliwa po confirm" : "nie"}
        />
      </div>
      {blockerLabels.length > 0 ? (
        <div className="mt-4 rounded-md border border-line bg-slate-50 p-3 text-sm leading-6 text-slate-700">
          <div className="font-semibold text-ink">Co blokuje zapis</div>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {blockerLabels.map((label) => (
              <li key={label}>{label}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

function ReadinessTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-line bg-slate-50 p-3 text-sm">
      <div className="text-xs font-medium uppercase tracking-normal text-slate-500">{label}</div>
      <div className="mt-1 font-semibold text-ink">{value}</div>
    </div>
  );
}

function ActionChangePreviewSummary({ action }: { action: ActionObject }) {
  if (action.preview_cards.length > 0) {
    return (
      <div className="mb-4 grid gap-3">
        {action.preview_cards.map((card) => (
          <ActionPreviewCard key={card.id} card={card} />
        ))}
      </div>
    );
  }
  return null;
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
      <h1 className="break-words text-2xl font-semibold tracking-normal">
        {evidence.title_label}
      </h1>
      <div className="mt-3 flex flex-wrap gap-2">
        <NeutralLabelChip>{evidence.source_connector_label}</NeutralLabelChip>
        <NeutralLabelChip>{evidence.source_type_label}</NeutralLabelChip>
        <StatusBadge value={evidence.freshness.state} label={evidence.freshness_label} />
      </div>
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Podsumowanie dowodu" />
        <p className="text-sm leading-6 text-slate-700">{evidence.summary}</p>
        <div className="mt-4 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
          <div>Źródło: {evidence.source_connector_label}</div>
          <div>Typ źródła: {evidence.source_type_label}</div>
          <div>Zebrano: {evidence.collected_at}</div>
          <div>Świeżość: {evidence.freshness_label}</div>
        </div>
        <TechnicalDetailsPanel
          className="mt-4"
          openLabel="Pokaż szczegóły techniczne dowodu"
          closeLabel="Ukryj szczegóły techniczne dowodu"
        >
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <div>Klucz dowodu w WILQ: {evidence.id}</div>
            <div>Klucz źródła: {evidence.source_id}</div>
            <div>
              Referencja źródłowa:{" "}
              {evidence.raw_ref ??
                "WILQ nie dostał osobnej referencji od źródła; decyzja musi opierać się na podsumowaniu, świeżości i śladzie dowodu."}
            </div>
          </div>
        </TechnicalDetailsPanel>
      </section>
    </main>
  );
}

function OpportunityDetail({ opportunity }: { opportunity: Opportunity }) {
  return (
    <main className="mx-auto max-w-5xl px-4 py-6 lg:px-8">
      <h1 className="text-2xl font-semibold tracking-normal">{opportunity.title}</h1>
      <div className="mt-3 flex flex-wrap gap-2">
        <NeutralLabelChip>{opportunity.domain_label}</NeutralLabelChip>
        <StatusBadge value={opportunity.risk} label={opportunity.risk_label} />
      </div>
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Diagnoza" />
        <p className="text-sm leading-6 text-slate-700">{opportunity.human_diagnosis}</p>
        <div className="mt-4 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
          <div>Dowody: {opportunity.evidence_summary_label}</div>
          <div>Źródła: {opportunity.source_connector_labels.join(", ")}</div>
        </div>
      </section>
      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Metryki z dowodów" />
        {opportunity.metrics.length === 0 ? (
          <p className="text-sm text-slate-600">
            Nie ma realnych metryk z dowodami; nie oceniaj wpływu tej szansy.
          </p>
        ) : (
          <>
            <MetricTileSummary tiles={opportunity.metric_tiles} />
            <TechnicalDetailsPanel
              className="mt-4"
              openLabel="Pokaż szczegóły techniczne metryk"
              closeLabel="Ukryj szczegóły techniczne metryk"
            >
              <pre className="mt-3 max-h-96 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100">
                {JSON.stringify(opportunity.metrics, null, 2)}
              </pre>
            </TechnicalDetailsPanel>
          </>
        )}
      </section>
    </main>
  );
}

function MetricTileSummary({ tiles }: { tiles: Record<string, string | number> }) {
  const entries = Object.entries(tiles).slice(0, 8);
  if (entries.length === 0) {
    return <p className="text-sm text-slate-600">Metryki są dostępne w szczegółach technicznych.</p>;
  }
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {entries.map(([label, value]) => (
        <span
          key={label}
          className="rounded border border-line bg-slate-50 px-2 py-1 text-xs text-slate-700"
        >
          {label}: {value}
        </span>
      ))}
    </div>
  );
}

function NeutralLabelChip({ children }: { children: ReactNode }) {
  return (
    <span className="rounded border border-line bg-slate-50 px-2 py-1 text-xs font-medium text-slate-700">
      {children}
    </span>
  );
}

function TechnicalDetailsPanel({
  openLabel,
  closeLabel,
  className = "",
  children
}: {
  openLabel: string;
  closeLabel: string;
  className?: string;
  children: ReactNode;
}) {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <div className={`${className} rounded-md border border-line bg-slate-50 p-3 text-xs text-slate-700`}>
      <button
        type="button"
        onClick={() => setIsOpen((current) => !current)}
        className="font-medium text-ink"
      >
        {isOpen ? closeLabel : openLabel}
      </button>
      {isOpen ? children : null}
    </div>
  );
}

function SectionHeading({ title }: { title: string }) {
  return <h2 className="mb-3 text-sm font-semibold uppercase tracking-normal text-slate-600">{title}</h2>;
}

function ErrorState() {
  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="rounded-md border border-risk/30 bg-risk/10 p-4 text-sm text-risk">
        Nie udało się połączyć z WILQ.
      </div>
    </main>
  );
}
