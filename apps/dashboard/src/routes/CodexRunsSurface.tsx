import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Bot, CircleDollarSign, FileStack, ListChecks } from "lucide-react";

import { LoadingBand } from "../components/OperatorPrimitives";
import {
  CompactStatTile,
  DashboardToolbar,
  DenseQueueTable,
  StatusPill
} from "../components/DashboardMockupPrimitives";
import { getCodexRuns, type CodexRun } from "../lib/api";

export function CodexRunsSurface() {
  const runsQuery = useQuery({ queryKey: ["codex-runs"], queryFn: getCodexRuns });
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const runs = runsQuery.data ?? [];

  if (runsQuery.isLoading) return <LoadingBand />;
  if (runsQuery.error) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <h1 className="text-3xl font-semibold text-ink">Uruchomienia AI</h1>
        <p className="mt-3 text-sm text-risk">Nie udało się odczytać historii uruchomień.</p>
      </main>
    );
  }

  const selectedRun = runs.find((run) => run.id === selectedRunId) ?? runs[0] ?? null;
  const costValues = runs.flatMap((run) =>
    run.cost_estimate_pln === null || run.cost_estimate_pln === undefined
      ? []
      : [run.cost_estimate_pln]
  );
  const totalCost = costValues.reduce((sum, value) => sum + value, 0);
  const materialIds = new Set(runs.flatMap((run) => run.source_material_ids));
  const failedRuns = runs.filter((run) => run.status === "failed" || run.status === "blocked");

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <DashboardToolbar
        title="Uruchomienia AI"
        description="Historia modeli, kosztów i materiałów źródłowych użytych przez WILQ. Surowe prompty nie są zapisywane ani wyświetlane."
        dateLabel="Wszystkie zapisane"
        onRefresh={() => void runsQuery.refetch()}
      />

      <section className="mb-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <CompactStatTile
          value={runs.length}
          label="uruchomień"
          tone="blue"
          icon={<Bot aria-hidden="true" size={22} />}
        />
        <CompactStatTile
          value={costValues.length > 0 ? formatCost(totalCost) : "—"}
          label="oszacowanego kosztu"
          tone="green"
          icon={<CircleDollarSign aria-hidden="true" size={22} />}
        />
        <CompactStatTile
          value={materialIds.size}
          label="materiałów źródłowych"
          tone="purple"
          icon={<FileStack aria-hidden="true" size={22} />}
        />
        <CompactStatTile
          value={failedRuns.length}
          label="zablokowanych lub błędnych"
          tone={failedRuns.length > 0 ? "red" : "neutral"}
          icon={<ListChecks aria-hidden="true" size={22} />}
        />
      </section>

      <DenseQueueTable
        title="Lista uruchomień"
        rows={runs}
        getRowKey={(run) => run.id}
        selectedRowKey={selectedRun?.id}
        emptyLabel="Brak zapisanych uruchomień AI"
        columns={[
          {
            key: "id",
            header: "Run",
            render: (run) => (
              <button
                type="button"
                className="font-mono text-xs font-semibold text-action hover:underline"
                aria-label={`Pokaż szczegóły uruchomienia ${shortRunId(run.id)}`}
                onClick={() => setSelectedRunId(run.id)}
              >
                {shortRunId(run.id)}
              </button>
            ),
            className: "min-w-40"
          },
          { key: "skill", header: "Skill", render: (run) => run.skill ?? "—" },
          {
            key: "status",
            header: "Status",
            render: (run) => (
              <StatusPill label={statusLabel(run.status)} tone={statusTone(run.status)} />
            )
          },
          { key: "model", header: "Model", render: (run) => run.model ?? "—" },
          { key: "cost", header: "Koszt", render: (run) => formatOptionalCost(run.cost_estimate_pln) },
          {
            key: "template",
            header: "Szablon promptu",
            render: (run) => run.prompt_template_id ?? "—",
            className: "min-w-48"
          },
          {
            key: "materials",
            header: "Materiały",
            render: (run) => run.source_material_ids.length
          }
        ]}
      />

      {selectedRun ? <CodexRunDetails run={selectedRun} /> : null}
    </main>
  );
}

function CodexRunDetails({ run }: { run: CodexRun }) {
  return (
    <section className="mt-5 rounded-md border border-line bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-ink">Szczegóły uruchomienia</h2>
        <StatusPill label={statusLabel(run.status)} tone={statusTone(run.status)} />
      </div>
      <dl className="mt-4 grid gap-x-6 gap-y-4 text-sm md:grid-cols-2 xl:grid-cols-3">
        <Detail label="Pełne ID" value={run.id} mono />
        <Detail label="Skill" value={run.skill} />
        <Detail label="Hook" value={run.hook} />
        <Detail label="Model" value={run.model} />
        <Detail label="Reasoning effort" value={run.model_reasoning_effort} />
        <Detail label="Szablon promptu" value={run.prompt_template_id} mono />
        <Detail label="Digest promptu" value={run.prompt_digest} mono />
        <Detail label="Tokeny wejściowe" value={formatOptionalNumber(run.token_usage_input)} />
        <Detail label="Tokeny wyjściowe" value={formatOptionalNumber(run.token_usage_output)} />
        <Detail label="Koszt" value={formatOptionalCost(run.cost_estimate_pln)} />
        <Detail label="Digest planu" value={run.planning_digest} mono />
        <Detail label="Digest wejścia planu" value={run.planning_input_digest} mono />
        <Detail label="Digest kontekstu szkicu" value={run.initial_draft_context_digest} mono />
        <Detail label="Błąd" value={run.error} />
      </dl>
      <TraceIds label="Dowody" values={run.evidence_ids} />
      <TraceIds label="Materiały źródłowe" values={run.source_material_ids} />
      <TraceIds label="Akcje" values={run.action_ids} />
      <TraceIds label="Użyte endpointy" values={run.used_endpoints} />
    </section>
  );
}

function Detail({ label, value, mono = false }: { label: string; value: string | null | undefined; mono?: boolean }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase tracking-normal text-slate-500">{label}</dt>
      <dd className={`mt-1 break-all text-slate-800 ${mono ? "font-mono text-xs" : ""}`}>
        {value || "—"}
      </dd>
    </div>
  );
}

function TraceIds({ label, values }: { label: string; values: string[] }) {
  return (
    <details className="mt-4 border-t border-line pt-3">
      <summary className="cursor-pointer text-sm font-semibold text-slate-700">
        {label} ({values.length})
      </summary>
      <div className="mt-2 flex flex-wrap gap-2">
        {values.length > 0 ? values.map((value) => (
          <code key={value} className="break-all rounded bg-slate-100 px-2 py-1 text-xs text-slate-700">
            {value}
          </code>
        )) : <span className="text-sm text-slate-500">—</span>}
      </div>
    </details>
  );
}

function shortRunId(runId: string) {
  if (runId.length <= 18) return runId;
  return `${runId.slice(0, 10)}…${runId.slice(-6)}`;
}

function formatCost(value: number) {
  return new Intl.NumberFormat("pl-PL", {
    style: "currency",
    currency: "PLN",
    minimumFractionDigits: 2,
    maximumFractionDigits: 4
  }).format(value);
}

function formatOptionalCost(value: number | null | undefined) {
  return value === null || value === undefined ? "—" : formatCost(value);
}

function formatOptionalNumber(value: number | null | undefined) {
  return value === null || value === undefined ? "—" : new Intl.NumberFormat("pl-PL").format(value);
}

function statusLabel(status: CodexRun["status"]) {
  return {
    started: "w toku",
    completed: "zakończone",
    failed: "błąd",
    blocked: "zablokowane"
  }[status];
}

function statusTone(status: CodexRun["status"]): "blue" | "green" | "red" | "amber" {
  const tones: Record<CodexRun["status"], "blue" | "green" | "red" | "amber"> = {
    started: "blue",
    completed: "green",
    failed: "red",
    blocked: "amber"
  };
  return tones[status];
}
