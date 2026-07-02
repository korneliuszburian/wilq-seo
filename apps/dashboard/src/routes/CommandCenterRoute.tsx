import { useQuery } from "@tanstack/react-query";
import { ClipboardCheck, Copy } from "lucide-react";

import { BlockerNotice, LabelChipRow, LoadingBand, MetricTile } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import { TraceLine } from "../components/TraceLine";
import { CommandCenterResponse, getCommandCenter } from "../lib/api";

function copyPromptToClipboard(prompt: string) {
  if (!navigator.clipboard) return;
  void navigator.clipboard.writeText(prompt);
}

function DailyDecisionBoard({ data }: { data: CommandCenterResponse }) {
  const blockedDecisions = data.daily_decisions.filter(
    (item) => item.decision_state === "blocked" || item.status === "blocked"
  );

  return (
    <section>
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
          <ClipboardCheck aria-hidden="true" size={18} />
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Dzisiejsze decyzje marketera
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            {data.primary_next_step}
          </p>
        </div>
      </div>
      <div className="mb-4 grid gap-3 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-md border border-line bg-white p-4">
          <h3 className="text-sm font-semibold text-ink">Plan dnia w kolejności</h3>
          <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-6 text-slate-700">
            {data.daily_decisions.map((item) => (
              <li key={`order-${item.id}`}>
                <span className="font-medium text-ink">{item.title}</span>
                <span className="text-slate-500"> · {item.route_label} · {item.decision_state_label}</span>
              </li>
            ))}
          </ol>
        </div>

        <div className="rounded-md border border-risk/25 bg-risk/10 p-4">
          <h3 className="text-sm font-semibold text-ink">Blokady dnia</h3>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            {data.blocker_count > 0
              ? `${data.blocker_count} decyzje wymagają wyjaśnienia przed końcowym wnioskiem.`
              : "Brak blokad w decyzjach dnia; nadal sprawdzaj dowody i akcje przed zapisem."}
          </p>
          <TraceLine
            label="Najpierw nie przeskakuj"
            values={blockedDecisions.map((item) => item.title)}
            empty="Brak zablokowanych decyzji w planie dnia."
          />
        </div>
      </div>
      <div className="grid gap-3 xl:grid-cols-2">
        {data.daily_decisions.map((item) => {
          return (
          <article key={item.id} className="rounded-md border border-line bg-white p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <LabelChipRow
                  chips={[
                    { label: "Typ", value: "decyzja" },
                    { label: "Priorytet", value: item.priority_label }
                  ]}
                />
                <h3 className="mt-1 text-base font-semibold tracking-normal">
                  {item.title}
                </h3>
              </div>
              <StatusBadge value={item.decision_state} label={item.decision_state_label} />
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-700">
              {item.co_widzimy}
            </p>
            {Object.keys(item.metric_tiles ?? {}).length > 0 ? (
              <div className="mt-3 grid grid-cols-2 gap-2 text-center text-xs sm:grid-cols-3">
                {Object.entries(item.metric_tiles).map(([label, value]) => (
                  <MetricTile key={label} label={label} value={value} />
                ))}
              </div>
            ) : null}
            <p className="mt-2 text-sm leading-6 text-slate-700">
              {item.dlaczego_to_ma_znaczenie}
            </p>
            <p className="mt-2 text-sm font-medium text-ink">
              {item.bezpieczny_next_step}
            </p>
            {item.skill_id && item.codex_prompt ? (
              <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-md border border-action/25 bg-action/5 p-3 text-sm">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-normal text-action">
                  <Copy aria-hidden="true" size={15} />
                  Polecenie: {item.skill_label ?? "workflow WILQ"}
                </div>
                <button
                  type="button"
                  onClick={() => copyPromptToClipboard(item.codex_prompt ?? "")}
                  className="inline-flex h-8 items-center rounded-md border border-action/30 px-3 text-xs font-semibold uppercase tracking-normal text-action hover:bg-action/10"
                >
                  Kopiuj polecenie
                </button>
              </div>
            ) : null}
            <div className="mt-3 grid gap-2 text-xs text-slate-600">
              <TraceLine label="Źródła danych" values={item.source_connector_labels} />
              <TraceLine label="Świeżość źródeł" values={[item.freshness_label]} />
              <TraceLine label="Dowody w WILQ" values={[item.evidence_summary]} />
              <TraceLine label="Akcje do sprawdzenia" values={[item.action_summary]} />
              <TraceLine label="Czego nie twierdzimy" values={item.blocked_claim_labels} />
            </div>
            <a
              href={item.route}
              className="mt-4 inline-flex h-9 items-center rounded-md border border-line px-3 text-sm font-medium text-ink hover:bg-slate-50"
            >
              {item.cta_label || "Otwórz widok"}
            </a>
          </article>
          );
        })}
      </div>
    </section>
  );
}

function SourceHealthSummary({ data }: { data: CommandCenterResponse }) {
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Źródła i ograniczenia
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            To jest tylko skrót zdrowia źródeł. Pełne statusy źródeł danych, braki
            uprawnień i etykiety źródeł dostępu są w ustawieniach, nie w planie dnia.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Źródła" value={data.connector_summary.total} />
          <MetricTile label="Aktywne" value={data.connector_summary.configured} />
          <MetricTile label="Do naprawy" value={data.connector_summary.missing_credentials} />
        </div>
      </div>
      <a
        href="/settings"
        className="mt-4 inline-flex h-9 items-center rounded-md border border-line px-3 text-sm font-medium text-ink hover:bg-slate-50"
      >
        Otwórz ustawienia
      </a>
    </section>
  );
}

function ErrorState() {
  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <BlockerNotice message="Nie udało się połączyć z WILQ." />
    </main>
  );
}

export function CommandCenter() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["command-center"],
    queryFn: getCommandCenter
  });

  if (isLoading) return <LoadingBand />;
  if (error || !data) return <ErrorState />;
  const sourceCount = Array.from(
    new Set(data.daily_decisions.flatMap((item) => item.source_connectors))
  ).length;

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Centrum pracy</h1>
          <p className="mt-1 text-sm text-slate-600">{data.strict_instruction}</p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Decyzje" value={data.daily_decisions.length} />
          <MetricTile label="Blokady" value={data.blocker_count} />
          <MetricTile label="Źródła" value={sourceCount} />
        </div>
      </div>

      <div className="grid gap-8">
        <DailyDecisionBoard data={data} />

        <SourceHealthSummary data={data} />
      </div>
    </main>
  );
}
