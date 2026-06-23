import { Link } from "@tanstack/react-router";

import { BlockerNotice, MetricTile } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import type { Workflow, WorkflowRun } from "../lib/api";

export function WorkflowRunList({ runs }: { runs: WorkflowRun[] }) {
  if (runs.length === 0) {
    return <p className="text-sm text-slate-600">Brak zapisanych uruchomień workflow.</p>;
  }

  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {runs.map((run) => (
        <article key={run.id} className="rounded-md border border-line bg-white p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold">{run.workflow_id.replaceAll("_", " ")}</h3>
              <p className="mt-1 break-words text-xs text-slate-500">{run.id}</p>
            </div>
            <StatusBadge value={run.status} />
          </div>
          <div className="mt-3 grid gap-2 text-xs text-slate-600">
            <div>Dowody: {run.output.evidence_ids.length}</div>
            <div>Akcje: {run.output.action_ids.length}</div>
            <div>Błędy: {run.output.errors.length}</div>
          </div>
        </article>
      ))}
    </div>
  );
}

export function WorkflowRegistryList({ workflows }: { workflows: Workflow[] }) {
  if (workflows.length === 0) {
    return (
      <BlockerNotice message="Brak workflowów w WILQ API. Nie pokazujemy automatyzacji, której API nie zna." />
    );
  }

  return (
    <div className="grid gap-3 xl:grid-cols-2">
      {workflows.map((workflow) => (
        <article key={workflow.id} className="rounded-md border border-line bg-white p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold">{workflow.label}</h3>
              <p className="mt-1 break-words text-xs text-slate-500">{workflow.id}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <StatusBadge value={workflow.status} />
              <StatusBadge value={workflow.risk} />
            </div>
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-700">{workflow.description}</p>
          {Object.keys(workflow.metric_tiles).length > 0 ? (
            <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-700 sm:grid-cols-3">
              {Object.entries(workflow.metric_tiles).map(([label, value]) => (
                <MetricTile key={`${workflow.id}-${label}`} label={label} value={value} />
              ))}
            </div>
          ) : null}
          {workflow.safe_next_step ? (
            <p className="mt-3 text-sm font-medium text-ink">{workflow.safe_next_step}</p>
          ) : null}
          <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
            <div>Skill: {workflow.skill_id ? "dostępny" : "brak"}</div>
            <div>
              Widok:{" "}
              {workflow.route ? (
                <Link className="font-medium text-brand" to={workflow.route}>
                  {workflow.route}
                </Link>
              ) : (
                "brak"
              )}
            </div>
            <div>Źródła: {workflow.source_connectors.join(", ") || "brak"}</div>
            <div>Akcje: {workflow.action_ids.length || "brak"}</div>
            <div>Dowody: {workflow.evidence_ids.length || "brak"}</div>
            <div>Brakujące kontrakty: {workflow.missing_contracts.length}</div>
          </div>
          {workflow.blocked_claims.length > 0 ? (
            <p className="mt-3 text-xs text-slate-600">
              Zablokowane claimy: {workflow.blocked_claims.join(", ")}
            </p>
          ) : null}
        </article>
      ))}
    </div>
  );
}
