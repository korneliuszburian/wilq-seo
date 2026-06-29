import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { useState, type ReactNode } from "react";

import {
  type ActionObject,
  type Evidence,
  type Opportunity,
  type WorkflowRun,
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
  const relatedActions = getRelatedOpportunityActions(actions.data ?? [], evidenceIds);
  const liveItems = items.filter((item) => !item.is_fixture);

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <SurfaceIntro
        title="Szanse i decyzje"
        description="Kolejka szans z danych WILQ oparta o te same decyzje, które widzi Centrum pracy. Każda karta musi mieć dowody, źródła, liczby i bezpieczny następny krok. Sam dostęp do źródła danych albo dane testowe nie są rekomendacją marketingową."
        metrics={[
          { label: "Decyzje", value: opportunities.isLoading ? "..." : items.length },
          { label: "Aktywne", value: opportunities.isLoading ? "..." : liveItems.length },
          { label: "Dowody", value: opportunities.isLoading ? "..." : evidenceIds.size }
        ]}
      />

      <div className="grid gap-8">
        <OpportunityDecisionSection isLoading={opportunities.isLoading} items={items} />
        <OpportunityActionsSection
          actions={relatedActions}
          isLoading={actions.isLoading}
          error={actions.error}
          expanded={showRelatedActions}
          onToggle={() => setShowRelatedActions((value) => !value)}
        />
        <OpportunityEvidenceSection
          evidenceItems={evidence.data ?? []}
          evidenceIds={evidenceIds}
          isLoading={evidence.isLoading}
          error={evidence.error}
          expanded={showEvidenceDetails}
          onToggle={() => setShowEvidenceDetails((value) => !value)}
        />
      </div>
    </main>
  );
}

function getRelatedOpportunityActions(actions: ActionObject[], evidenceIds: Set<string>) {
  const actionEvidenceIds = new Set(actions.flatMap((action) => action.evidence_ids));
  return actions.filter(
    (action) =>
      actionEvidenceIds.size === 0 ||
      action.evidence_ids.some((id) => evidenceIds.has(id))
  );
}

function OpportunityDecisionSection({
  isLoading,
  items
}: {
  isLoading: boolean;
  items: Opportunity[];
}) {
  return (
    <section>
      <SectionHeading title="Kolejka decyzji z WILQ" />
      {isLoading ? <LoadingBand /> : <OpportunityList opportunities={items} />}
    </section>
  );
}

function OpportunityActionsSection({
  actions,
  isLoading,
  error,
  expanded,
  onToggle
}: {
  actions: ActionObject[];
  isLoading: boolean;
  error: unknown;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <section>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SectionHeading title="Powiązane akcje" />
        {!isLoading && !error ? (
          <ToggleButton onClick={onToggle}>
            {expanded ? "Ukryj powiązane akcje" : `Pokaż powiązane akcje (${actions.length})`}
          </ToggleButton>
        ) : null}
      </div>
      {isLoading ? (
        <LoadingBand />
      ) : error ? (
        <InlineErrorState message="Nie udało się pobrać powiązanych akcji." />
      ) : expanded ? (
        <ActionList actions={actions} />
      ) : (
        <MutedExpandableText>
          Powiązane akcje są dostępne po rozwinięciu. Domyślny widok skupia się
          na decyzjach i dowodach, nie na pełnym rejestrze akcji.
        </MutedExpandableText>
      )}
    </section>
  );
}

function OpportunityEvidenceSection({
  evidenceItems,
  evidenceIds,
  isLoading,
  error,
  expanded,
  onToggle
}: {
  evidenceItems: Evidence[];
  evidenceIds: Set<string>;
  isLoading: boolean;
  error: unknown;
  expanded: boolean;
  onToggle: () => void;
}) {
  const visibleEvidence = evidenceItems.filter((item) => evidenceIds.has(item.id)).slice(0, 12);

  return (
    <section>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SectionHeading title="Dowody użyte przez karty" />
        {!isLoading && !error ? (
          <ToggleButton onClick={onToggle}>
            {expanded ? "Ukryj szczegóły dowodów" : "Pokaż szczegóły dowodów"}
          </ToggleButton>
        ) : null}
      </div>
      {isLoading ? (
        <LoadingBand />
      ) : error ? (
        <InlineErrorState message="Nie udało się pobrać dowodów dla kart." />
      ) : expanded ? (
        <EvidenceList evidenceItems={visibleEvidence} />
      ) : (
        <MutedExpandableText>
          Szczegóły dowodów są dostępne po rozwinięciu. Domyślny widok pokazuje
          liczbę dowodów i źródła w kartach decyzji bez surowych identyfikatorów.
        </MutedExpandableText>
      )}
    </section>
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
      <SurfaceIntro
        title="Akcje do sprawdzenia"
        description="Kolejka sprawdzeń przygotowana przez WILQ. Na wejściu pokazuje tylko najważniejsze decyzje, dowody, ryzyko i następny krok. Zapis zmian pozostaje zablokowany bez sprawdzenia w WILQ, jawnej zgody i audytu."
        metrics={[
          { label: "Akcje", value: items.length },
          { label: "Do sprawdzenia", value: needsValidation.length },
          { label: "Dowody", value: evidenceIds.size }
        ]}
      />

      <div className="grid gap-8">
        <section>
          <SectionHeading title="Najważniejsze na start" />
          <p className="mb-3 max-w-3xl text-sm leading-6 text-slate-600">
            Zacznij od sprawdzeń, które odpowiadają głównej ścieżce pracy:
            Merchant, treści, GA4 i Google Ads. Pełna lista zostaje schowana,
            dopóki nie jest potrzebna.
          </p>
          <ActionPriorityFocus actions={priorityActions} />
        </section>
        <section>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <SectionHeading title="Pozostałe akcje" />
            <ToggleButton onClick={() => setShowFullList((value) => !value)}>
              {showFullList ? "Ukryj pozostałe akcje" : `Pokaż pozostałe akcje (${remainingActions.length})`}
            </ToggleButton>
          </div>
          {showFullList ? (
            <ActionList actions={remainingActions} />
          ) : (
            <MutedExpandableText>
              Pozostałe akcje są dostępne po rozwinięciu. Domyślny widok ma pomagać wybrać
              następne sprawdzenie, nie przeglądać całej kolejki naraz.
            </MutedExpandableText>
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
      <BlockerNotice message="Brak priorytetowych akcji z głównej ścieżki pracy. Pełna lista niżej nadal pokazuje dostępne akcje do sprawdzenia." />
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
                Zanim cokolwiek zapiszesz, otwórz akcję i sprawdź dowody, podgląd zmian
                oraz decyzję człowieka.
              </p>
            </div>
            <StatusBadge value={action.validation_status} label={action.validation_status_label} />
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-700">
            {action.recommended_reason}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <StatusBadge value={action.status} label={action.status_label} />
            <StatusBadge value={action.risk} label={action.risk_label} />
          </div>
          <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
            <div>Dowody: {action.evidence_summary_label}</div>
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

  if (workflows.isLoading || workflowRuns.isLoading || (showRelatedActions && actions.isLoading)) {
    return <LoadingBand />;
  }
  if (workflows.error || workflowRuns.error || (showRelatedActions && actions.error)) {
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
      <SurfaceIntro
        title="Procesy WILQ"
        description="Procesy łączą decyzje, dowody i akcje do sprawdzenia. Gotowe prowadzą do pracy marketera, a zablokowane pokazują, czego WILQ nie może jeszcze bezpiecznie obiecać ani zapisać."
        metrics={[
          { label: "Procesy", value: workflowItems.length },
          { label: "Gotowe", value: readyWorkflows.length },
          { label: "Uruchomienia", value: runs.length }
        ]}
      />

      <div className="grid gap-8">
        <section>
          <SectionHeading title="Procesy decyzyjne" />
          <WorkflowRegistryList workflows={workflowItems} />
        </section>
        <WorkflowRunsSection
          runs={runs}
          workflowLabelsById={workflowLabelsById}
          expanded={showWorkflowRuns}
          onToggle={() => setShowWorkflowRuns((value) => !value)}
        />
        <WorkflowOutcomesSection
          evidenceCount={workflowEvidenceIds.size}
          actionCount={workflowActionIds.size}
          expanded={showWorkflowOutcomes}
          onToggle={() => setShowWorkflowOutcomes((value) => !value)}
        />
        <RelatedWorkflowActionsSection
          actionCount={workflowActionIds.size}
          actions={relatedActions}
          isLoading={actions.isLoading}
          error={actions.error}
          expanded={showRelatedActions}
          onToggle={() => setShowRelatedActions((value) => !value)}
        />
      </div>
    </main>
  );
}

type SurfaceMetric = {
  label: string;
  value: string | number;
};

function SurfaceIntro({
  title,
  description,
  metrics
}: {
  title: string;
  description: string;
  metrics: SurfaceMetric[];
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-normal">{title}</h1>
        <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">{description}</p>
      </div>
      <div className="grid grid-cols-3 gap-2 text-center text-xs">
        {metrics.map((metric) => (
          <MetricTile key={metric.label} label={metric.label} value={metric.value} />
        ))}
      </div>
    </div>
  );
}

function ToggleButton({ children, onClick }: { children: ReactNode; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex min-h-9 items-center rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-ink hover:bg-slate-100"
    >
      {children}
    </button>
  );
}

function MutedExpandableText({ children }: { children: ReactNode }) {
  return (
    <p className="mt-2 rounded-md border border-line bg-white p-3 text-sm leading-6 text-slate-600">
      {children}
    </p>
  );
}

function WorkflowRunsSection({
  runs,
  workflowLabelsById,
  expanded,
  onToggle
}: {
  runs: WorkflowRun[];
  workflowLabelsById: Map<string, string>;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <section>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SectionHeading title="Ostatnie uruchomienia" />
        <ToggleButton onClick={onToggle}>
          {expanded ? "Ukryj uruchomienia" : `Pokaż uruchomienia (${runs.length})`}
        </ToggleButton>
      </div>
      {expanded ? (
        <WorkflowRunList runs={runs} workflowLabelsById={workflowLabelsById} />
      ) : (
        <MutedExpandableText>
          Historia uruchomień jest schowana na wejściu. Najpierw wybierz proces albo
          przejdź do widoku pracy, a uruchomienia sprawdzaj tylko przy audycie.
        </MutedExpandableText>
      )}
    </section>
  );
}

function WorkflowOutcomesSection({
  evidenceCount,
  actionCount,
  expanded,
  onToggle
}: {
  evidenceCount: number;
  actionCount: number;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <section>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SectionHeading title="Wyniki procesów" />
        <ToggleButton onClick={onToggle}>
          {expanded ? "Ukryj wyniki" : "Pokaż wyniki procesów"}
        </ToggleButton>
      </div>
      {expanded ? (
        <div className="grid gap-3 xl:grid-cols-2">
          <WorkflowOutcomeCard
            title="Dowody z procesów"
            count={evidenceCount}
            suffix="powiązanych dowodów"
            detail="Szczegółowe ID zostają w widokach technicznych."
          />
          <WorkflowOutcomeCard
            title="Akcje z procesów"
            count={actionCount}
            suffix="powiązanych akcji do sprawdzenia"
            detail="Pełne szczegóły są niżej w kartach akcji."
          />
        </div>
      ) : (
        <MutedExpandableText>
          Wyniki procesów są dostępne po rozwinięciu. Domyślny widok pokazuje
          priorytet, status i bezpieczny następny krok.
        </MutedExpandableText>
      )}
    </section>
  );
}

function WorkflowOutcomeCard({
  title,
  count,
  suffix,
  detail
}: {
  title: string;
  count: number;
  suffix: string;
  detail: string;
}) {
  return (
    <article className="rounded-md border border-line bg-white p-4 text-sm text-slate-700">
      <h3 className="font-semibold text-ink">{title}</h3>
      <p className="mt-2 leading-6">
        WILQ ma {count || "brak"} {suffix}. {detail}
      </p>
    </article>
  );
}

function RelatedWorkflowActionsSection({
  actionCount,
  actions,
  isLoading,
  error,
  expanded,
  onToggle
}: {
  actionCount: number;
  actions: ActionObject[];
  isLoading: boolean;
  error: unknown;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <section>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SectionHeading title="Powiązane akcje" />
        <ToggleButton onClick={onToggle}>
          {expanded ? "Ukryj powiązane akcje" : `Pokaż powiązane akcje (${actionCount})`}
        </ToggleButton>
      </div>
      {isLoading ? (
        <LoadingBand />
      ) : error ? (
        <InlineErrorState message="Nie udało się pobrać powiązanych akcji." />
      ) : expanded ? (
        <ActionList actions={actions} />
      ) : (
        <MutedExpandableText>
          Pełne karty akcji są dostępne po rozwinięciu. Wejście w procesy ma
          najpierw pokazać, co jest gotowe, co jest zablokowane i gdzie przejść dalej.
        </MutedExpandableText>
      )}
    </section>
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
