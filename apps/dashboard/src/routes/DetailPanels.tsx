import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";

import {
  type ActionObject,
  type Evidence,
  getEvidenceById,
  getOpportunities,
  type Opportunity
} from "../lib/api";
import { LoadingBand } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import {
  ActionHumanReviewControls,
  ActionPreviewControls,
  ActionReviewGatePanel,
  ActionValidationControls
} from "./ActionPanels";
import { useActionDetailQueries } from "./actionDetailQueries";
import { ActionOperatorDecisionHero } from "./DetailPanelsSections/DecisionHeroSection";
import {
  ActionChangePreviewSummary,
  ActionMutationReadinessPanel
} from "./DetailPanelsSections/MutationReadinessSection";
import {
  SectionHeading,
  type ActionMutationReadiness
} from "./DetailPanelsSections/Shared";
import { TechnicalDetailsPanel } from "./DetailPanelsSections/TechnicalSection";

export function ActionDetailSurface({ actionId }: { actionId: string }) {
  const { action, mutationReadiness } = useActionDetailQueries(actionId);

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
  mutationReadiness: ActionMutationReadiness | undefined;
  mutationReadinessError: unknown;
  mutationReadinessLoading: boolean;
}) {
  const visibleAuditEvents = action.audit_events.slice(0, 6);
  const hiddenAuditEventCount = Math.max(0, action.audit_events.length - visibleAuditEvents.length);

  return (
    <main className="mx-auto max-w-6xl px-4 py-6 lg:px-8">
      <ActionOperatorDecisionHero
        action={action}
        mutationReadiness={mutationReadiness}
        mutationReadinessLoading={mutationReadinessLoading}
        mutationReadinessError={mutationReadinessError}
      />
      <section id="action-review" className="mt-6 rounded-md border border-line bg-white p-4">
        <SectionHeading title="Podgląd, review i walidacja" />
        <p className="text-sm leading-6 text-slate-700">
          Tu wykonujesz bezpieczną część pracy: sprawdzenie, podgląd, review i potwierdzenie.
          Zapis zmian pozostaje blokowany, dopóki WILQ nie ma pełnej ścieżki zgody i audytu.
        </p>
        <ActionReviewGatePanel
          action={action}
          lastCreatedDraft={mutationReadiness?.last_created_draft}
        />
        <ActionHumanReviewControls action={action} />
        <ActionPreviewControls action={action} />
        <ActionValidationControls action={action} />
      </section>
      <ActionMutationReadinessPanel
        loading={mutationReadinessLoading}
        error={mutationReadinessError}
        readiness={mutationReadiness}
      />
      <section id="action-preview" className="mt-6 rounded-md border border-line bg-white p-4">
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
        <SectionHeading title="Dowody i audyt" />
        <div className="rounded-md border border-line bg-slate-50 p-3 text-sm leading-6 text-slate-700">
          <div className="font-semibold text-ink">Dlaczego WILQ pokazał tę akcję</div>
          <p className="mt-1">{action.human_diagnosis}</p>
          <p className="mt-2 text-xs text-slate-600">Dowody: {action.evidence_summary_label}</p>
        </div>
        {action.audit_events.length === 0 ? (
          <p className="mt-3 text-sm text-slate-600">
            Brak zapisanych zdarzeń audytu. Traktuj akcję jako przygotowaną do pracy, nie jako wykonaną.
          </p>
        ) : (
          <TechnicalDetailsPanel
            className="mt-3"
            openLabel="Pokaż historię audytu"
            closeLabel="Ukryj historię audytu"
          >
            <div className="mt-3 grid gap-3">
              {hiddenAuditEventCount > 0 ? (
                <p className="text-xs text-slate-500">
                  Pokazano 6 najnowszych z {action.audit_events.length} zdarzeń audytu.
                </p>
              ) : null}
              {visibleAuditEvents.map((event) => (
                <div key={event.id} className="rounded-md border border-line bg-white p-3 text-sm">
                  <div className="font-medium">{event.event_type_label}</div>
                  <div className="mt-1 text-slate-600">
                    {event.summary}
                  </div>
                </div>
              ))}
            </div>
          </TechnicalDetailsPanel>
        )}
      </section>
    </main>
  );
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

function ErrorState() {
  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="rounded-md border border-risk/30 bg-risk/10 p-4 text-sm text-risk">
        Nie udało się połączyć z WILQ.
      </div>
    </main>
  );
}
