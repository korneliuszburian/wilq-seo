import { BlockerNotice, MetricTile } from "../../components/OperatorPrimitives";
import { StatusBadge } from "../../components/StatusBadge";
import { TraceLine } from "../../components/TraceLine";
import type {
  Ga4DecisionCardComponent,
  Ga4DecisionItem,
  Ga4DiagnosticsResponse
} from "./Shared";

export function Ga4OperatorSummary({
  data,
  DecisionCard,
  MeasurementIssueCard
}: {
  data: Ga4DiagnosticsResponse;
  DecisionCard: Ga4DecisionCardComponent;
  MeasurementIssueCard: Ga4DecisionCardComponent;
}) {
  const summary = data.operator_summary;
  const decisionsById = new Map(data.decision_queue.map((decision) => [decision.id, decision]));
  const topDecisions = summary.top_decision_ids
    .map((decisionId) => decisionsById.get(decisionId))
    .filter(
      (decision): decision is Ga4DecisionItem =>
        decision !== undefined && decision.decision_type !== "fix_measurement"
    );
  const measurementDecisions = data.decision_queue.filter(
    (decision) => decision.decision_type === "fix_measurement"
  );
  const conversionReadiness = data.conversion_readiness_contract;
  const trackingSection = data.sections.find((section) => section.id === "ga4_tracking_readiness");
  const actionIds = summary.action_ids;
  const conversionMissingDataLabels =
    conversionReadiness.missing_read_contract_labels.length > 0
      ? conversionReadiness.missing_read_contract_labels
      : [conversionReadiness.missing_read_contract_summary_label || "dane kompletne"];
  const workSteps = [
    `Najpierw wyjaśnij ${summary.measurement_issue_count} problemy pomiaru: brak strony wejścia, źródła albo medium nie jest oceną kampanii.`,
    `Potem sprawdź ${topDecisions.length} gotowe kontrole jakości ruchu: porównaj stronę wejścia, źródło, kampanię i intencję strony.`,
    "Nie wyciągaj wniosków o zwrocie z reklam, przychodzie, opłacalności ani spadku konwersji bez osobnych dowodów kosztu, atrybucji i kontekstu konwersji."
  ];

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            GA4: co dziś zrobić
          </div>
          <h2 className="mt-1 text-base font-semibold tracking-normal">{summary.title}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{summary.summary}</p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Grupy ruchu" value={data.landing_group_count} />
          <MetricTile label="Pomiar" value={summary.measurement_issue_count} />
          <MetricTile label="Brak WP" value={summary.wordpress_missing_count} />
        </div>
      </div>

      <div className="mb-4 rounded-md border border-line bg-slate-50 p-3">
        <h3 className="text-sm font-semibold text-ink">Kolejność pracy</h3>
        <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm leading-6 text-slate-700">
          {workSteps.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
      </div>

      {measurementDecisions.length > 0 ? (
        <div className="mb-4 rounded-md border border-risk/25 bg-risk/10 p-3">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h3 className="text-sm font-semibold text-ink">Najpierw pomiar</h3>
              <p className="mt-1 text-sm leading-6 text-slate-700">
                Te wiersze mówią o luce w danych, nie o jakości kampanii ani strony. Wyjaśnij je
                przed oceną ruchu.
              </p>
            </div>
            <StatusBadge
              value="blocked"
              label={`${measurementDecisions.length} do wyjaśnienia`}
            />
          </div>
          <div className="mt-3 grid gap-2">
            {measurementDecisions.slice(0, 2).map((decision) => (
              <MeasurementIssueCard key={decision.id} decision={decision} />
            ))}
          </div>
        </div>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="grid gap-3">
          {topDecisions.length > 0 ? (
            topDecisions.map((decision) => (
              <DecisionCard key={decision.id} decision={decision} />
            ))
          ) : (
            <BlockerNotice message="Problemy pomiaru są w sekcji powyżej. Brak osobnych decyzji jakości ruchu do pokazania w operatorze GA4." />
          )}
        </div>

        <div className="rounded-md border border-line bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-ink">Bezpieczny tryb analityki</h3>
          <div className="mt-3 grid gap-2 text-xs text-slate-600">
            <TraceLine
              label="Świeżość danych"
              values={[
                data.freshness_assessment.state_label,
                data.freshness_assessment.summary
              ]}
            />
            <TraceLine
              label="Gotowość pomiaru"
              values={
                trackingSection ? [trackingSection.status_label, trackingSection.summary] : []
              }
              empty="WILQ nie podał oceny gotowości pomiaru; nie oceniaj kampanii po tych danych."
            />
            <TraceLine
              label="Konwersje i zdarzenia kluczowe"
              values={[conversionReadiness.status_label, conversionReadiness.summary]}
            />
            <TraceLine
              label="Brakujące dane"
              values={conversionMissingDataLabels}
              empty="dane kompletne"
            />
            <TraceLine label="Dowody w WILQ" values={[data.evidence_summary_label]} />
            <TraceLine label="Akcje" values={[summary.action_summary_label]} />
            <TraceLine label="Nie wolno twierdzić" values={summary.blocked_claim_labels} />
          </div>
          {actionIds.length > 0 ? (
            <a
              href={`/actions/${actionIds[0]}`}
              className="mt-4 inline-flex h-9 items-center rounded-md border border-line bg-white px-3 text-sm font-medium text-ink hover:bg-slate-100"
            >
              Sprawdź GA4 w WILQ
            </a>
          ) : null}
        </div>
      </div>
    </section>
  );
}
