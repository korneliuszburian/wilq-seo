import { useQuery } from "@tanstack/react-query";

import {
  getActions,
  getEvidence,
  getOpportunities,
  getWorkflowRuns,
  getWorkflows
} from "../lib/api";
import { LoadingBand, MetricTile } from "../components/OperatorPrimitives";
import { LinkedTraceLine } from "../components/TraceLine";
import { ActionList, EvidenceList, OpportunityList } from "./RegistryPanels";
import { WorkflowRegistryList, WorkflowRunList } from "./WorkflowPanels";

export function OpportunitiesSurface() {
  const opportunities = useQuery({ queryKey: ["opportunities"], queryFn: getOpportunities });
  const actions = useQuery({ queryKey: ["actions"], queryFn: getActions });
  const evidence = useQuery({ queryKey: ["evidence"], queryFn: getEvidence });

  if (opportunities.isLoading || actions.isLoading || evidence.isLoading) return <LoadingBand />;
  if (opportunities.error || actions.error || evidence.error) return <ErrorState />;

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
          <MetricTile label="Decyzje" value={items.length} />
          <MetricTile label="Aktywne" value={liveItems.length} />
          <MetricTile label="Dowody" value={evidenceIds.size} />
        </div>
      </div>

      <div className="grid gap-8">
        <section>
          <SectionHeading title="Kolejka decyzji z WILQ API" />
          <OpportunityList opportunities={items} />
        </section>
        <section>
          <SectionHeading title="Powiązane ActionObjecty" />
          <ActionList
            actions={(actions.data ?? []).filter(
              (action) =>
                actionEvidenceIds.size === 0 ||
                action.evidence_ids.some((id) => evidenceIds.has(id))
            )}
          />
        </section>
        <section>
          <SectionHeading title="Dowody użyte przez karty" />
          <EvidenceList
            evidenceItems={(evidence.data ?? []).filter((item) => evidenceIds.has(item.id)).slice(0, 12)}
          />
        </section>
      </div>
    </main>
  );
}

export function ActionsSurface() {
  const actions = useQuery({ queryKey: ["actions"], queryFn: getActions });
  const evidence = useQuery({ queryKey: ["evidence"], queryFn: getEvidence });

  if (actions.isLoading || evidence.isLoading) return <LoadingBand />;
  if (actions.error || evidence.error) return <ErrorState />;

  const items = actions.data ?? [];
  const evidenceIds = new Set(items.flatMap((action) => action.evidence_ids));
  const relatedEvidence = (evidence.data ?? [])
    .filter((item) => evidenceIds.has(item.id))
    .slice(0, 12);
  const needsValidation = items.filter(
    (action) => action.validation_status !== "valid"
  );

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">ActionObjecty</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            ActionObjecty z WILQ API. To jest kolejka bezpiecznych kandydatów działań:
            każda karta ma dowody, tryb, ryzyko, status walidacji i payload preview.
            Apply pozostaje zablokowany bez walidacji, jawnej zgody i audytu.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="ActionObjecty" value={items.length} />
          <MetricTile label="Do walidacji" value={needsValidation.length} />
          <MetricTile label="Dowody" value={evidenceIds.size} />
        </div>
      </div>

      <div className="grid gap-8">
        <section>
          <SectionHeading title="ActionObjecty do przeglądu" />
          <ActionList actions={items} />
        </section>
        <section>
          <SectionHeading title="Dowody powiązane z akcjami" />
          <EvidenceList evidenceItems={relatedEvidence} />
        </section>
      </div>
    </main>
  );
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
            decyzji, dowodów i ActionObjectów; planowane pokazują brakujące kontrakty
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
              <h3 className="font-semibold text-ink">ActionObjecty z workflowów</h3>
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
          <SectionHeading title="Powiązane ActionObjecty" />
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
