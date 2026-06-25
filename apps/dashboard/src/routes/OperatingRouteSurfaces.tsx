import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";

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
import { LinkedTraceLine } from "../components/TraceLine";
import { ActionList, EvidenceList, OpportunityList } from "./RegistryPanels";
import { WorkflowRegistryList, WorkflowRunList } from "./WorkflowPanels";
import { marketerOperatorCopy } from "./marketingLabels";

const DEMO_ACTION_PRIORITY = [
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

  if (opportunities.error) return <ErrorState />;

  const items = opportunities.data ?? [];
  const evidenceIds = new Set(items.flatMap((item) => item.evidence_ids));
  const actionEvidenceIds = new Set((actions.data ?? []).flatMap((action) => action.evidence_ids));
  const liveItems = items.filter((item) => !item.is_fixture);

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Szanse i decyzje</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Kolejka szans z WILQ API oparta o te same decyzje, które widzi Command Center.
            Każda karta musi mieć dowody, źródła, liczby i bezpieczny następny krok.
            Sama gotowość connectora albo dane testowe nie są rekomendacją marketingową.
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
          <SectionHeading title="Kolejka decyzji z WILQ API" />
          {opportunities.isLoading ? <LoadingBand /> : <OpportunityList opportunities={items} />}
        </section>
        <section>
          <SectionHeading title="Powiązane akcje" />
          {actions.isLoading ? (
            <LoadingBand />
          ) : actions.error ? (
            <InlineErrorState message="Nie udało się pobrać powiązanych akcji." />
          ) : (
            <ActionList
              actions={(actions.data ?? []).filter(
                (action) =>
                  actionEvidenceIds.size === 0 ||
                  action.evidence_ids.some((id) => evidenceIds.has(id))
              )}
            />
          )}
        </section>
        <section>
          <SectionHeading title="Dowody użyte przez karty" />
          {evidence.isLoading ? (
            <LoadingBand />
          ) : evidence.error ? (
            <InlineErrorState message="Nie udało się pobrać dowodów dla kart." />
          ) : (
            <EvidenceList
              evidenceItems={(evidence.data ?? [])
                .filter((item) => evidenceIds.has(item.id))
                .slice(0, 12)}
            />
          )}
        </section>
      </div>
    </main>
  );
}

export function ActionsSurface() {
  const actions = useQuery({ queryKey: ["actions"], queryFn: getActions });

  if (actions.isLoading) return <LoadingBand />;
  if (actions.error) return <ErrorState />;

  const items = actions.data ?? [];
  const evidenceIds = new Set(items.flatMap((action) => action.evidence_ids));
  const needsValidation = items.filter(
    (action) => action.validation_status !== "valid"
  );
  const demoFocusActions = getDemoFocusActions(items);
  const remainingActions = items.filter(
    (action) => !demoFocusActions.some((focusAction) => focusAction.id === action.id)
  );

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Akcje do walidacji</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Kolejka bezpiecznych kandydatów działań z WILQ API. Każda karta ma
            dowody, tryb, ryzyko, status walidacji i podgląd zmian.
            Wykonanie pozostaje zablokowane bez walidacji, jawnej zgody i audytu.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Akcje" value={items.length} />
          <MetricTile label="Do walidacji" value={needsValidation.length} />
          <MetricTile label="Dowody" value={evidenceIds.size} />
        </div>
      </div>

      <div className="grid gap-8">
        <section>
          <SectionHeading title="Najważniejsze akcje demo" />
          <p className="mb-3 max-w-3xl text-sm leading-6 text-slate-600">
            To są pierwsze akcje do pokazania marketerowi: Merchant, Content,
            GA4 i przegląd Ads. Pełna lista zostaje niżej jako szczegóły.
          </p>
          <ActionDemoFocus actions={demoFocusActions} />
        </section>
        <section>
          <SectionHeading title="Pełna lista akcji - szczegóły" />
          <ActionList actions={remainingActions} />
        </section>
      </div>
    </main>
  );
}

function getDemoFocusActions(actions: ActionObject[]) {
  const byId = new Map(actions.map((action) => [action.id, action]));
  return DEMO_ACTION_PRIORITY.map((id) => byId.get(id)).filter(
    (action): action is ActionObject => Boolean(action)
  );
}

function ActionDemoFocus({ actions }: { actions: ActionObject[] }) {
  if (actions.length === 0) {
    return (
      <BlockerNotice message="Brak priorytetowych akcji demo w /api/actions. Pełna lista niżej nadal pokazuje dostępne kandydaty do przeglądu." />
    );
  }

  return (
    <div className="grid gap-3 xl:grid-cols-2">
      {actions.map((action) => (
        <article key={action.id} className="rounded-md border border-action/30 bg-action/5 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold">{marketerOperatorCopy(action.title)}</h3>
              <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
                {action.domain} / {action.connector} / {action.mode}
              </p>
            </div>
            <StatusBadge value={action.validation_status} />
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-700">
            {marketerOperatorCopy(action.recommended_reason)}
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
  return `${count} ID`;
}

export function WorkflowsSurface() {
  const workflows = useQuery({ queryKey: ["workflows"], queryFn: getWorkflows });
  const workflowRuns = useQuery({ queryKey: ["workflow-runs"], queryFn: getWorkflowRuns });
  const actions = useQuery({ queryKey: ["actions"], queryFn: getActions });
  const evidence = useQuery({ queryKey: ["evidence"], queryFn: getEvidence });

  if (workflows.isLoading || workflowRuns.isLoading || actions.isLoading || evidence.isLoading) {
    return <LoadingBand />;
  }
  if (workflows.error || workflowRuns.error || actions.error || evidence.error) {
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

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Workflowy WILQ</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Mapa workflowów operatora oparta o WILQ API. Gotowe workflowy prowadzą do
            decyzji, dowodów i akcji; planowane pokazują brakujące kontrakty
            zamiast udawać automatyzację.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Workflowy" value={workflowItems.length} />
          <MetricTile label="Gotowe workflowy" value={readyWorkflows.length} />
          <MetricTile label="Runy" value={runs.length} />
        </div>
      </div>

      <div className="grid gap-8">
        <section>
          <SectionHeading title="Workflowy decyzyjne" />
          <WorkflowRegistryList workflows={workflowItems} />
        </section>
        <section>
          <SectionHeading title="Ostatnie uruchomienia" />
          <WorkflowRunList runs={runs} />
        </section>
        <section>
          <SectionHeading title="Wyniki workflowów" />
          <div className="grid gap-3 xl:grid-cols-2">
            <article className="rounded-md border border-line bg-white p-4 text-sm text-slate-700">
              <h3 className="font-semibold text-ink">Dowody z workflowów</h3>
              <LinkedTraceLine
                label="Dowody"
                values={[...workflowEvidenceIds].slice(0, 12)}
                kind="evidence"
                empty="brak"
              />
            </article>
            <article className="rounded-md border border-line bg-white p-4 text-sm text-slate-700">
              <h3 className="font-semibold text-ink">Akcje z workflowów</h3>
              <LinkedTraceLine
                label="Akcje"
                values={[...workflowActionIds].slice(0, 12)}
                kind="actions"
                empty="brak"
              />
            </article>
          </div>
        </section>
        <section>
          <SectionHeading title="Powiązane akcje" />
          <ActionList
            actions={(actions.data ?? []).filter((action) => workflowActionIds.has(action.id))}
          />
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
        WILQ API is not reachable.
      </div>
    </main>
  );
}

function InlineErrorState({ message }: { message: string }) {
  return <BlockerNotice message={message} />;
}
