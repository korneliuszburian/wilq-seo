import { useQuery } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

import {
  type ActionObject,
  type WorkflowRun,
  getActions,
  getWorkflowRuns,
  getWorkflows
} from "../../lib/api";
import { BlockerNotice, LoadingBand } from "../../components/OperatorPrimitives";
import { ActionList } from "../RegistryPanels";
import { WorkflowRegistryList, WorkflowRunList } from "../WorkflowPanels";
import { SurfaceIntro, ToggleButton } from "./Shared";

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

  if (workflows.isLoading) {
    return <LoadingBand />;
  }
  if (workflows.error) {
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
          isLoading={workflowRuns.isLoading}
          error={workflowRuns.error}
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
  isLoading,
  error,
  expanded,
  onToggle
}: {
  runs: WorkflowRun[];
  workflowLabelsById: Map<string, string>;
  isLoading: boolean;
  error: unknown;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <section>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SectionHeading title="Ostatnie uruchomienia" />
        {!isLoading && !error ? (
          <ToggleButton onClick={onToggle}>
            {expanded ? "Ukryj uruchomienia" : `Pokaż uruchomienia (${runs.length})`}
          </ToggleButton>
        ) : null}
      </div>
      {isLoading ? (
        <LoadingBand />
      ) : error ? (
        <InlineErrorState message="Nie udało się pobrać historii uruchomień." />
      ) : expanded ? (
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
  const outcomeCopy =
    count > 0
      ? `WILQ ma ${count} ${suffix}. ${detail}`
      : `WILQ nie ma jeszcze ${suffix}. Nie traktuj tego procesu jak gotowej decyzji bez dowodów i akcji do sprawdzenia. ${detail}`;

  return (
    <article className="rounded-md border border-line bg-white p-4 text-sm text-slate-700">
      <h3 className="font-semibold text-ink">{title}</h3>
      <p className="mt-2 leading-6">{outcomeCopy}</p>
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

export function ErrorState() {
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
