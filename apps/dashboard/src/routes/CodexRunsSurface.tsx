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
import { getCodexRun, getCodexRunHistory, type CodexRun } from "../lib/api";

const HISTORY_PAGE_LIMIT = 50;

export function CodexRunsSurface() {
  const [cursor, setCursor] = useState<string | null>(null);
  const [cursorStack, setCursorStack] = useState<Array<string | null>>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const historyQuery = useQuery({
    queryKey: ["codex-run-history", cursor],
    queryFn: () => getCodexRunHistory(HISTORY_PAGE_LIMIT, cursor)
  });
  const detailQuery = useQuery({
    queryKey: ["codex-run-detail", selectedRunId],
    queryFn: () => getCodexRun(selectedRunId as string),
    enabled: selectedRunId !== null
  });
  const page = historyQuery.data;
  const runs = page?.items ?? [];
  const selectedSummary = runs.find((run) => run.id === selectedRunId) ?? null;

  if (historyQuery.isLoading) return <LoadingBand />;
  if (historyQuery.error) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <h1 className="text-3xl font-semibold text-ink">Uruchomienia AI</h1>
        <p className="mt-3 text-sm text-risk">Nie udało się odczytać historii uruchomień.</p>
      </main>
    );
  }

  const costValues = runs.flatMap((run) =>
    run.cost_estimate_pln === null || run.cost_estimate_pln === undefined
      ? []
      : [run.cost_estimate_pln]
  );
  const totalCost = costValues.reduce((sum, value) => sum + value, 0);
  const materialCount = runs.reduce((sum, run) => sum + run.source_material_count, 0);
  const failedRuns = runs.filter((run) => run.status === "failed" || run.status === "blocked");

  function goNext() {
    if (!page?.next_cursor) return;
    setCursorStack((stack) => [...stack, cursor]);
    setCursor(page.next_cursor);
    setSelectedRunId(null);
  }

  function goPrevious() {
    const previous = cursorStack.at(-1);
    if (previous === undefined) return;
    setCursorStack((stack) => stack.slice(0, -1));
    setCursor(previous);
    setSelectedRunId(null);
  }

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <DashboardToolbar
        title="Uruchomienia AI"
        description="Stronicowana historia modeli, kosztów i materiałów źródłowych. Metadane promptu i pełny ślad uruchomienia są dostępne po wybraniu rekordu."
        dateLabel="Strona serwerowa"
        onRefresh={() => void historyQuery.refetch()}
      />

      <p className="mb-3 text-xs text-slate-500">
        Statystyki dotyczą bieżącej strony: {runs.length} z {page?.total_count ?? 0} uruchomień.
      </p>
      <section className="mb-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <CompactStatTile
          value={runs.length}
          label="uruchomień na stronie"
          tone="blue"
          icon={<Bot aria-hidden="true" size={22} />}
        />
        <CompactStatTile
          value={costValues.length > 0 ? formatCost(totalCost) : "—"}
          label="koszt strony"
          tone="green"
          icon={<CircleDollarSign aria-hidden="true" size={22} />}
        />
        <CompactStatTile
          value={materialCount}
          label="materiałów na stronie"
          tone="purple"
          icon={<FileStack aria-hidden="true" size={22} />}
        />
        <CompactStatTile
          value={failedRuns.length}
          label="błędnych na stronie"
          tone={failedRuns.length > 0 ? "red" : "neutral"}
          icon={<ListChecks aria-hidden="true" size={22} />}
        />
      </section>

      <DenseQueueTable
        title="Lista uruchomień"
        rows={runs}
        getRowKey={(run) => run.id}
        selectedRowKey={selectedSummary?.id}
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
          { key: "materials", header: "Materiały", render: (run) => run.source_material_count }
        ]}
      />

      <nav className="mt-5 flex items-center justify-between" aria-label="Historia uruchomień">
        <button
          type="button"
          className="rounded-md border border-line px-3 py-2 text-sm font-semibold text-ink disabled:cursor-not-allowed disabled:opacity-40"
          disabled={cursorStack.length === 0}
          onClick={goPrevious}
        >
          Poprzednia strona
        </button>
        <span className="text-xs text-slate-500">Limit {HISTORY_PAGE_LIMIT}</span>
        <button
          type="button"
          className="rounded-md border border-line px-3 py-2 text-sm font-semibold text-action disabled:cursor-not-allowed disabled:opacity-40"
          disabled={!page?.next_cursor}
          onClick={goNext}
        >
          Następna strona
        </button>
      </nav>

      {selectedRunId && detailQuery.isLoading ? <LoadingBand /> : null}
      {selectedRunId && detailQuery.error ? (
        <p className="mt-4 text-sm text-risk">Nie udało się odczytać szczegółów uruchomienia.</p>
      ) : null}
      {detailQuery.data ? <CodexRunDetails run={detailQuery.data} /> : null}
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
