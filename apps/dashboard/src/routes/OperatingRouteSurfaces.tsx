import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { useState } from "react";

import {
  type ActionObject,
  getActions,
  getEvidence,
  getOpportunities,
  getWorkflowRuns,
  getWorkflows
} from "../lib/api";
import { BlockerNotice, LoadingBand, MetricTile } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import { ActionList, EvidenceList, OpportunityList } from "./RegistryPanels";
import { WorkflowRegistryList, WorkflowRunList } from "./WorkflowPanels";

const PRIORITY_ACTION_IDS = [
  "act_review_merchant_feed_issues",
  "act_prepare_content_refresh_queue",
  "act_review_ga4_tracking_quality",
  "act_prepare_ads_campaign_review_queue",
  "act_prepare_negative_keyword_review_queue"
];

export function OpportunitiesSurface() {
  const opportunities = useQuery({ queryKey: ["opportunities"], queryFn: getOpportunities });
  const actions = useQuery({ queryKey: ["actions"], queryFn: getActions });
  const evidence = useQuery({ queryKey: ["evidence"], queryFn: getEvidence });
  const [showRelatedActions, setShowRelatedActions] = useState(false);
  const [showEvidenceDetails, setShowEvidenceDetails] = useState(false);

  if (opportunities.error) return <ErrorState />;

  const items = opportunities.data ?? [];
  const evidenceIds = new Set(items.flatMap((item) => item.evidence_ids));
  const actionEvidenceIds = new Set((actions.data ?? []).flatMap((action) => action.evidence_ids));
  const relatedActions = (actions.data ?? []).filter(
    (action) =>
      actionEvidenceIds.size === 0 ||
      action.evidence_ids.some((id) => evidenceIds.has(id))
  );
  const liveItems = items.filter((item) => !item.is_fixture);

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Szanse i decyzje</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Kolejka szans z danych WILQ oparta o te same decyzje, które widzi Command Center.
            Każda karta musi mieć dowody, źródła, liczby i bezpieczny następny krok.
            Sam dostęp do źródła danych albo dane testowe nie są rekomendacją marketingową.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Decyzje" value={opportunities.isLoading ? "..." : items.length} />
          <MetricTile label="Aktywne" value={opportunities.isLoading ? "..." : liveItems.length} />
          <MetricTile label="Dowody" value={opportunities.isLoading ? "..." : evidenceIds.size} />
        </div>
      </div>

      <div className="grid gap-8">
        <section>
          <SectionHeading title="Kolejka decyzji z WILQ" />
          {opportunities.isLoading ? <LoadingBand /> : <OpportunityList opportunities={items} />}
        </section>
        <section>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <SectionHeading title="Powiązane akcje" />
            {!actions.isLoading && !actions.error ? (
              <button
                type="button"
                onClick={() => setShowRelatedActions((value) => !value)}
                className="inline-flex min-h-9 items-center rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-ink hover:bg-slate-100"
              >
                {showRelatedActions
                  ? "Ukryj powiązane akcje"
                  : `Pokaż powiązane akcje (${relatedActions.length})`}
              </button>
            ) : null}
          </div>
          {actions.isLoading ? (
            <LoadingBand />
          ) : actions.error ? (
            <InlineErrorState message="Nie udało się pobrać powiązanych akcji." />
          ) : showRelatedActions ? (
            <ActionList actions={relatedActions} />
          ) : (
            <p className="mt-2 rounded-md border border-line bg-white p-3 text-sm leading-6 text-slate-600">
              Powiązane akcje są dostępne po rozwinięciu. Domyślny widok skupia się
              na decyzjach i dowodach, nie na pełnym rejestrze akcji.
            </p>
          )}
        </section>
        <section>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <SectionHeading title="Dowody użyte przez karty" />
            {!evidence.isLoading && !evidence.error ? (
              <button
                type="button"
                onClick={() => setShowEvidenceDetails((value) => !value)}
                className="inline-flex min-h-9 items-center rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-ink hover:bg-slate-100"
              >
                {showEvidenceDetails ? "Ukryj szczegóły dowodów" : "Pokaż szczegóły dowodów"}
              </button>
            ) : null}
          </div>
          {evidence.isLoading ? (
            <LoadingBand />
          ) : evidence.error ? (
            <InlineErrorState message="Nie udało się pobrać dowodów dla kart." />
          ) : showEvidenceDetails ? (
            <EvidenceList
              evidenceItems={(evidence.data ?? [])
                .filter((item) => evidenceIds.has(item.id))
                .slice(0, 12)}
            />
          ) : (
            <p className="mt-2 rounded-md border border-line bg-white p-3 text-sm leading-6 text-slate-600">
              Szczegóły dowodów są dostępne po rozwinięciu. Domyślny widok pokazuje
              liczbę dowodów i źródła w kartach decyzji bez surowych identyfikatorów.
            </p>
          )}
        </section>
      </div>
    </main>
  );
}

export function ActionsSurface() {
  const actions = useQuery({ queryKey: ["actions"], queryFn: getActions });
  const [showFullList, setShowFullList] = useState(false);

  if (actions.isLoading) return <LoadingBand />;
  if (actions.error) return <ErrorState />;

  const items = actions.data ?? [];
  const evidenceIds = new Set(items.flatMap((action) => action.evidence_ids));
  const needsValidation = items.filter(
    (action) => action.validation_status !== "valid"
  );
  const priorityActions = getPriorityActions(items);
  const remainingActions = items.filter(
    (action) => !priorityActions.some((focusAction) => focusAction.id === action.id)
  );

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Akcje do sprawdzenia</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Kolejka sprawdzeń przygotowana przez WILQ. Na wejściu pokazuje
            tylko najważniejsze decyzje, dowody, ryzyko i następny krok.
            Zapis zmian pozostaje zablokowany bez sprawdzenia w WILQ, jawnej zgody i audytu.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Akcje" value={items.length} />
          <MetricTile label="Do sprawdzenia" value={needsValidation.length} />
          <MetricTile label="Dowody" value={evidenceIds.size} />
        </div>
      </div>

      <div className="grid gap-8">
        <section>
          <SectionHeading title="Najważniejsze na start" />
          <p className="mb-3 max-w-3xl text-sm leading-6 text-slate-600">
            Zacznij od sprawdzeń, które odpowiadają core path: Merchant, Content,
            GA4 i Ads. Pełna lista zostaje schowana, dopóki nie jest potrzebna.
          </p>
          <ActionPriorityFocus actions={priorityActions} />
        </section>
        <section>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <SectionHeading title="Pozostałe akcje" />
            <button
              type="button"
              onClick={() => setShowFullList((value) => !value)}
              className="inline-flex min-h-9 items-center rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-ink hover:bg-slate-100"
            >
              {showFullList ? "Ukryj pozostałe akcje" : `Pokaż pozostałe akcje (${remainingActions.length})`}
            </button>
          </div>
          {showFullList ? (
            <ActionList actions={remainingActions} />
          ) : (
            <p className="mt-2 rounded-md border border-line bg-white p-3 text-sm leading-6 text-slate-600">
              Pozostałe akcje są dostępne po rozwinięciu. Domyślny widok ma pomagać wybrać
              następne sprawdzenie, nie przeglądać całego rejestru technicznego naraz.
            </p>
          )}
        </section>
      </div>
    </main>
  );
}

function getPriorityActions(actions: ActionObject[]) {
  const byId = new Map(actions.map((action) => [action.id, action]));
  return PRIORITY_ACTION_IDS.map((id) => byId.get(id)).filter(
    (action): action is ActionObject => Boolean(action)
  );
}

function ActionPriorityFocus({ actions }: { actions: ActionObject[] }) {
  if (actions.length === 0) {
    return (
      <BlockerNotice message="Brak priorytetowych akcji z core path. Pełna lista niżej nadal pokazuje dostępne akcje do sprawdzenia." />
    );
  }

  return (
    <div className="grid gap-3 xl:grid-cols-2">
      {actions.map((action) => (
        <article key={action.id} className="rounded-md border border-action/30 bg-action/5 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold">{action.title}</h3>
              <p className="mt-1 text-xs leading-5 text-slate-500">
                Sprawdzenie przed zapisem zmian. Szczegóły techniczne są dostępne po otwarciu akcji.
              </p>
            </div>
            <StatusBadge value={action.validation_status} />
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-700">
            {action.recommended_reason}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <StatusBadge value={action.status} />
            <StatusBadge value={action.risk} />
          </div>
          <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
            <div>Dowody: {formatEvidenceCount(action.evidence_ids.length)}</div>
            <div>Metryki: {action.metrics.length}</div>
          </div>
          <Link
            to="/actions/$actionId"
            params={{ actionId: action.id }}
            className="mt-4 inline-flex min-h-9 items-center rounded-md border border-action bg-white px-3 py-2 text-xs font-medium text-action hover:bg-action/10"
          >
            Otwórz akcję
          </Link>
        </article>
      ))}
    </div>
  );
}

function formatEvidenceCount(count: number) {
  if (count === 0) return "brak";
  if (count === 1) return "1 dowód źródłowy";
  if (count >= 2 && count <= 4) return `${count} dowody źródłowe`;
  return `${count} dowodów źródłowych`;
}

export function WorkflowsSurface() {
  const workflows = useQuery({ queryKey: ["workflows"], queryFn: getWorkflows });
  const workflowRuns = useQuery({ queryKey: ["workflow-runs"], queryFn: getWorkflowRuns });
  const [showRelatedActions, setShowRelatedActions] = useState(false);
  const [showWorkflowRuns, setShowWorkflowRuns] = useState(false);
  const [showWorkflowOutcomes, setShowWorkflowOutcomes] = useState(false);
  const actions = useQuery({
    queryKey: ["actions"],
    queryFn: getActions,
    enabled: showRelatedActions
  });

  if (workflows.isLoading || workflowRuns.isLoading || actions.isLoading) {
    return <LoadingBand />;
  }
  if (workflows.error || workflowRuns.error || actions.error) {
    return <ErrorState />;
  }

  const runs = workflowRuns.data ?? [];
  const workflowItems = workflows.data ?? [];
  const readyWorkflows = workflowItems.filter((workflow) => workflow.status === "ready");
  const workflowEvidenceIds = new Set([
    ...runs.flatMap((run) => run.output.evidence_ids),
    ...workflowItems.flatMap((workflow) => workflow.evidence_ids)
  ]);
  const workflowActionIds = new Set([
    ...runs.flatMap((run) => run.output.action_ids),
    ...workflowItems.flatMap((workflow) => workflow.action_ids)
  ]);
  const workflowLabelsById = new Map(workflowItems.map((workflow) => [workflow.id, workflow.label]));
  const relatedActions = (actions.data ?? []).filter((action) => workflowActionIds.has(action.id));

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Procesy WILQ</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Procesy łączą decyzje, dowody i akcje do sprawdzenia. Gotowe prowadzą
            do pracy marketera, a zablokowane pokazują, czego WILQ nie może jeszcze
            bezpiecznie obiecać ani zapisać.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Procesy" value={workflowItems.length} />
          <MetricTile label="Gotowe" value={readyWorkflows.length} />
          <MetricTile label="Uruchomienia" value={runs.length} />
        </div>
      </div>

      <div className="grid gap-8">
        <section>
          <SectionHeading title="Procesy decyzyjne" />
          <WorkflowRegistryList workflows={workflowItems} />
        </section>
        <section>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <SectionHeading title="Ostatnie uruchomienia" />
            <button
              type="button"
              onClick={() => setShowWorkflowRuns((value) => !value)}
              className="inline-flex min-h-9 items-center rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-ink hover:bg-slate-100"
            >
              {showWorkflowRuns ? "Ukryj uruchomienia" : `Pokaż uruchomienia (${runs.length})`}
            </button>
          </div>
          {showWorkflowRuns ? (
            <WorkflowRunList runs={runs} workflowLabelsById={workflowLabelsById} />
          ) : (
            <p className="mt-2 rounded-md border border-line bg-white p-3 text-sm leading-6 text-slate-600">
              Historia uruchomień jest schowana na wejściu. Najpierw wybierz proces
              albo przejdź do widoku pracy, a runy sprawdzaj tylko przy audycie.
            </p>
          )}
        </section>
        <section>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <SectionHeading title="Wyniki procesów" />
            <button
              type="button"
              onClick={() => setShowWorkflowOutcomes((value) => !value)}
              className="inline-flex min-h-9 items-center rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-ink hover:bg-slate-100"
            >
              {showWorkflowOutcomes ? "Ukryj wyniki" : "Pokaż wyniki procesów"}
            </button>
          </div>
          {showWorkflowOutcomes ? (
            <div className="grid gap-3 xl:grid-cols-2">
              <article className="rounded-md border border-line bg-white p-4 text-sm text-slate-700">
                <h3 className="font-semibold text-ink">Dowody z procesów</h3>
                <p className="mt-2 leading-6">
                  WILQ ma {workflowEvidenceIds.size || "brak"} powiązanych dowodów.
                  Szczegółowe ID zostają w widokach technicznych.
                </p>
              </article>
              <article className="rounded-md border border-line bg-white p-4 text-sm text-slate-700">
                <h3 className="font-semibold text-ink">Akcje z procesów</h3>
                <p className="mt-2 leading-6">
                  WILQ ma {workflowActionIds.size || "brak"} powiązanych akcji do
                  sprawdzenia. Pełne szczegóły są niżej w kartach akcji.
                </p>
              </article>
            </div>
          ) : (
            <p className="mt-2 rounded-md border border-line bg-white p-3 text-sm leading-6 text-slate-600">
              Wyniki procesów są dostępne po rozwinięciu. Domyślny widok pokazuje
              priorytet, status i bezpieczny następny krok.
            </p>
          )}
        </section>
        <section>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <SectionHeading title="Powiązane akcje" />
            <button
              type="button"
              onClick={() => setShowRelatedActions((value) => !value)}
              className="inline-flex min-h-9 items-center rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-ink hover:bg-slate-100"
            >
              {showRelatedActions
                ? "Ukryj powiązane akcje"
                : `Pokaż powiązane akcje (${workflowActionIds.size})`}
            </button>
          </div>
          {actions.isLoading ? (
            <LoadingBand />
          ) : actions.error ? (
            <InlineErrorState message="Nie udało się pobrać powiązanych akcji." />
          ) : showRelatedActions ? (
            <ActionList actions={relatedActions} />
          ) : (
            <p className="mt-2 rounded-md border border-line bg-white p-3 text-sm leading-6 text-slate-600">
              Pełne karty akcji są dostępne po rozwinięciu. Wejście w procesy ma
              najpierw pokazać, co jest gotowe, co jest zablokowane i gdzie przejść dalej.
            </p>
          )}
        </section>
      </div>
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
        Nie udało się połączyć z WILQ.
      </div>
    </main>
  );
}

function InlineErrorState({ message }: { message: string }) {
  return <BlockerNotice message={message} />;
}
