import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
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

type CurrentDispositionReceipt = {
  publicUrl: string;
  canonicalPath: string;
  proposedFinalDisposition: "keep";
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function getCurrentDispositionReceipt(action: ActionObject): CurrentDispositionReceipt | null {
  if (action.payload.action_type !== "content_current_disposition_receipt") return null;

  const authority: unknown = action.payload.current_disposition_authority;
  if (!isRecord(authority)) return null;

  const publicUrl = authority.public_url;
  const canonicalPath = authority.canonical_path;
  const proposedFinalDisposition = authority.proposed_final_disposition;
  if (
    typeof publicUrl !== "string" ||
    !publicUrl.trim() ||
    typeof canonicalPath !== "string" ||
    !canonicalPath.trim() ||
    typeof proposedFinalDisposition !== "string" ||
    proposedFinalDisposition !== "keep"
  ) {
    return null;
  }

  try {
    const parsedUrl = new URL(publicUrl);
    if (parsedUrl.protocol !== "http:" && parsedUrl.protocol !== "https:") return null;
  } catch {
    return null;
  }

  return {
    publicUrl,
    canonicalPath,
    proposedFinalDisposition
  };
}

function CurrentDispositionCard({ receipt }: { receipt: CurrentDispositionReceipt }) {
  return (
    <article className="current-disposition-card" data-state={receipt.proposedFinalDisposition}>
      <h1 className="current-disposition-card__title">
        Czy zachowujemy tę stronę do dalszej aktualizacji?
      </h1>
      <div className="current-disposition-card__content">
        <div className="current-disposition-card__field">
          <div className="current-disposition-card__label">Adres strony</div>
          <a
            className="current-disposition-card__url"
            href={receipt.publicUrl}
            rel="noreferrer"
            target="_blank"
          >
            {receipt.publicUrl}
          </a>
          <div className="current-disposition-card__meta">
            Ścieżka kanoniczna: {receipt.canonicalPath}
          </div>
        </div>
        <p>
          <span className="current-disposition-card__label">Decyzja:</span>{" "}
          Zachowujemy obecny adres i przygotowujemy nową treść.
        </p>
        <div className="current-disposition-card__field">
          <div className="current-disposition-card__label">Od Ciebie / Wilka</div>
          <p>Potwierdź, że strona ma zostać pod tym adresem.</p>
        </div>
        <div className="current-disposition-card__field">
          <div className="current-disposition-card__label">Po zatwierdzeniu</div>
          <p>WILQ zapisze kierunek dalszych prac. Tekst jeszcze nie powstał.</p>
        </div>
        <p className="current-disposition-card__emphasis">
          Zatwierdzenie nie zmienia ani nie publikuje niczego w WordPressie.
        </p>
      </div>
      <div className="current-disposition-card__actions">
        <a
          className="current-disposition-card__primary-action"
          href="#action-review"
        >
          Przejdź do zatwierdzenia
        </a>
        <Link
          className="current-disposition-card__secondary-action"
          search={{
            work_item_id: undefined,
            section_heading: undefined,
            planning_digest: undefined,
            workspace: undefined,
            text: undefined,
            review: undefined,
            browse: undefined,
            new_page: undefined,
            view: undefined
          }}
          to="/content-workflow"
        >
          Nie — wróć do decyzji
        </Link>
      </div>
    </article>
  );
}

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
  const currentDispositionReceipt = getCurrentDispositionReceipt(action);
  const genericActionContent = (
    <>
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
    </>
  );

  return (
    <main className="mx-auto max-w-6xl px-4 py-6 lg:px-8">
      {currentDispositionReceipt ? (
        <>
          <CurrentDispositionCard receipt={currentDispositionReceipt} />
          <details className="mt-6 rounded-md border border-line bg-white p-4">
            <summary className="cursor-pointer font-semibold text-ink">
              Szczegóły techniczne i etapy audytu
            </summary>
            <div className="mt-4">{genericActionContent}</div>
          </details>
        </>
      ) : (
        genericActionContent
      )}
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
