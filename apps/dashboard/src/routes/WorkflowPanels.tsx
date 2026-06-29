import { useState } from "react";
import { Link } from "@tanstack/react-router";

import { BlockerNotice, MetricTile } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import type { Workflow, WorkflowRun } from "../lib/api";

export function WorkflowRunList({
  runs,
  workflowLabelsById = new Map()
}: {
  runs: WorkflowRun[];
  workflowLabelsById?: Map<string, string>;
}) {
  if (runs.length === 0) {
    return (
      <p className="text-sm text-slate-600">
        Nie ma zapisanych uruchomień procesu; nie traktuj procesu jako wykonanej automatyzacji.
      </p>
    );
  }

  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {runs.map((run) => (
        <article key={run.id} className="rounded-md border border-line bg-white p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold">
                {workflowLabelsById.get(run.workflow_id) ?? "Proces WILQ"}
              </h3>
            </div>
            <StatusBadge value={run.status} label={run.status_label} />
          </div>
          <div className="mt-3 grid gap-2 text-xs text-slate-600">
            <div>Dowody: {run.output.evidence_summary_label}</div>
            <div>Akcje: {run.output.action_summary_label}</div>
            <div>Błędy: {run.output.error_summary_label}</div>
          </div>
        </article>
      ))}
    </div>
  );
}

export function WorkflowRegistryList({ workflows }: { workflows: Workflow[] }) {
  const [showAll, setShowAll] = useState(false);

  if (workflows.length === 0) {
    return (
      <BlockerNotice message="Brak procesów w WILQ. Nie pokazujemy automatyzacji bez danych i reguł w systemie." />
    );
  }

  const visibleWorkflows = showAll ? workflows : workflows.slice(0, 5);
  const hiddenCount = Math.max(workflows.length - visibleWorkflows.length, 0);

  return (
    <div className="grid gap-3">
      <div className="grid gap-3 xl:grid-cols-2">
        {visibleWorkflows.map((workflow) => (
          <WorkflowSummaryCard key={workflow.id} workflow={workflow} />
        ))}
      </div>
      {hiddenCount > 0 || showAll ? (
        <button
          type="button"
          className="min-h-9 w-fit rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:border-action hover:text-action"
          onClick={() => setShowAll((value) => !value)}
        >
          {showAll ? "Pokaż mniej procesów" : `Pokaż wszystkie procesy (${workflows.length})`}
        </button>
      ) : null}
    </div>
  );
}

function WorkflowSummaryCard({ workflow }: { workflow: Workflow }) {
  const [showDetails, setShowDetails] = useState(false);

  return (
    <article className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">{workflow.label}</h3>
          <p className="mt-1 text-xs text-slate-500">
            {workflow.route_label ?? "Widok procesu niepodłączony do osobnej strony"}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <StatusBadge value={workflow.status} label={workflow.status_label} />
          <StatusBadge value={workflow.risk} label={workflow.risk_label} />
        </div>
      </div>
      {workflow.safe_next_step ? (
        <div className="mt-3 rounded-md border border-action/20 bg-action/5 p-3 text-sm leading-6 text-ink">
          <div className="font-semibold">Co zrobić dalej</div>
          <p>{workflow.safe_next_step}</p>
        </div>
      ) : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <div>Źródła danych: {workflow.source_connector_summary_label}</div>
        <div>Akcje do sprawdzenia: {workflow.action_summary_label}</div>
        <div>Dowody: {workflow.evidence_summary_label}</div>
        <div>Brakujące dane: {workflow.missing_contract_summary_label}</div>
        <div>Granice wniosków: {workflow.blocked_claim_summary_label}</div>
        <div>
          Widok:{" "}
          {workflow.route ? (
            <Link className="font-medium text-brand" to={workflow.route}>
              Otwórz
            </Link>
          ) : (
            "nie ma osobnego widoku; korzystaj z opisu procesu"
          )}
        </div>
      </div>
      <button
        type="button"
        className="mt-3 min-h-8 rounded-md border border-line bg-white px-3 py-1 text-xs font-medium text-slate-700 hover:border-action hover:text-action"
        onClick={() => setShowDetails((value) => !value)}
      >
        {showDetails ? "Ukryj opis procesu" : "Pokaż opis procesu"}
      </button>
      {showDetails ? (
        <div className="mt-3 rounded-md border border-line bg-slate-50 p-3 text-sm leading-6 text-slate-700">
          <p>{workflow.description}</p>
          {Object.keys(workflow.metric_tiles).length > 0 ? (
            <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-700 sm:grid-cols-3">
              {Object.entries(workflow.metric_tiles).map(([label, value]) => (
                <MetricTile key={`${workflow.id}-${label}`} label={label} value={value} />
              ))}
            </div>
          ) : null}
          <div className="mt-3 grid gap-2 text-xs text-slate-600">
            <div>Brakujące dane: {workflow.missing_contract_detail_label}</div>
            <div>Granice wniosków: {workflow.blocked_claim_summary_label}</div>
          </div>
        </div>
      ) : null}
    </article>
  );
}
