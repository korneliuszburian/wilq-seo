import { BlockerNotice, LabelChipRow, MetricTile } from "../../components/OperatorPrimitives";
import { StatusBadge } from "../../components/StatusBadge";
import { TraceLine } from "../../components/TraceLine";
import { tacticalContextPairs } from "../TacticalQueuePanel";
import { MerchantDecisionCard } from "./ProductSections";
import type { MerchantDecisionItem, MerchantDiagnosticsResponse } from "./shared";

export function MerchantOperatorSummary({ data }: { data: MerchantDiagnosticsResponse }) {
  const summary = data.operator_summary;
  const decisionsById = new Map(data.decision_queue.map((decision) => [decision.id, decision]));
  const clustersById = new Map(data.issue_clusters.map((cluster) => [cluster.id, cluster]));
  const itemsById = new Map(
    data.sections.flatMap((section) => section.tactical_items).map((item) => [item.id, item])
  );
  const topDecisions = summary.top_decision_ids
    .map((decisionId) => decisionsById.get(decisionId))
    .filter((decision): decision is MerchantDecisionItem => Boolean(decision));
  const topIssueClusters = summary.top_issue_cluster_ids
    .map((clusterId) => clustersById.get(clusterId))
    .filter((cluster): cluster is MerchantDiagnosticsResponse["issue_clusters"][number] =>
      Boolean(cluster)
    );
  const topIssueItems = summary.top_tactical_item_ids
    .map((itemId) => itemsById.get(itemId))
    .filter((item): item is MerchantDiagnosticsResponse["sections"][number]["tactical_items"][number] =>
      Boolean(item)
    );
  const actionIds = summary.action_ids;

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Przegląd Merchant
          </div>
          <h2 className="mt-1 text-base font-semibold tracking-normal">
            {summary.title}
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            {summary.summary}
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Produkty" value={data.product_count ?? 0} />
          <MetricTile label="Decyzje" value={data.decision_queue.length} />
          <MetricTile label="Zgłoszenia" value={summary.reported_issue_occurrences} />
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="grid gap-3">
          {topDecisions.length > 0 ? (
            topDecisions.map((decision) => (
              <MerchantDecisionCard key={decision.id} decision={decision} />
            ))
          ) : topIssueClusters.length > 0 ? (
            topIssueClusters.map((cluster) => (
              <article key={cluster.id} className="rounded-md border border-line bg-slate-50 p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <h3 className="text-sm font-semibold text-ink">
                      {cluster.issue_type_label ?? "problem pliku produktowego"}
                      {cluster.affected_attribute_label
                        ? `; atrybut: ${cluster.affected_attribute_label}`
                        : ""}
                      {`; kontekst: ${cluster.reporting_context_label}`}
                    </h3>
                    <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
                      {cluster.severity_label ?? "status nieznany"}.{" "}
                      {cluster.resolution_label ?? "ścieżka rozwiązania niepotwierdzona w Merchant"}.
                    </p>
                  </div>
                  <StatusBadge value={cluster.risk} label={cluster.risk_label} />
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-700">
                  Raport pokazuje {cluster.reported_issue_summary_label}
                  {cluster.country ? ` w kraju ${cluster.country}` : ""}
                  {`; kontekst: ${cluster.reporting_context_label}`}.
                </p>
                {cluster.sample_unavailable_reason ? (
                  <p className="mt-2 text-xs leading-5 text-slate-600">
                    {cluster.sample_unavailable_reason}
                  </p>
                ) : null}
                <p className="mt-2 text-sm font-medium text-ink">{cluster.next_step}</p>
                <div className="mt-2 flex flex-wrap gap-1.5 text-xs text-slate-700">
                  <span className="rounded border border-line bg-white px-2 py-1">
                    zgłoszenia: {cluster.product_count}
                  </span>
                  {cluster.country ? (
                    <span className="rounded border border-line bg-white px-2 py-1">
                      kraj: {cluster.country}
                    </span>
                  ) : null}
                  <span className="rounded border border-line bg-white px-2 py-1">
                    kontekst: {cluster.reporting_context_label}
                  </span>
                  {cluster.resolution ? (
                    <span className="rounded border border-line bg-white px-2 py-1">
                      rozwiązanie:{" "}
                      {cluster.resolution_label ?? "ścieżka rozwiązania niepotwierdzona w Merchant"}
                    </span>
                  ) : null}
                  {cluster.action_id ? (
                    <span className="rounded border border-line bg-white px-2 py-1">
                      akcja do sprawdzenia
                    </span>
                  ) : null}
                </div>
              </article>
            ))
          ) : topIssueItems.length > 0 ? (
            topIssueItems.map((item) => (
              <article key={item.id} className="rounded-md border border-line bg-slate-50 p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <h3 className="text-sm font-semibold text-ink">{item.title}</h3>
                    <LabelChipRow
                      className="mt-2"
                      chips={[
                        { label: "Zadanie", value: item.intent_label },
                        { label: "Priorytet", value: item.priority_label }
                      ]}
                    />
                  </div>
                  <StatusBadge value={item.risk} label={item.risk_label} />
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-700">{item.diagnosis}</p>
                <p className="mt-2 text-sm font-medium text-ink">{item.next_step}</p>
                <div className="mt-2 flex flex-wrap gap-1.5 text-xs text-slate-700">
                  {tacticalContextPairs(item).map(({ key, label, valueLabel }) => (
                    <span key={key} className="rounded border border-line bg-white px-2 py-1">
                      {label}: {valueLabel}
                    </span>
                  ))}
                </div>
              </article>
            ))
          ) : (
            <BlockerNotice message="Brak kolejki Merchant. Najpierw uruchom odczyt danych Merchant." />
          )}
        </div>

        <div className="rounded-md border border-line bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-ink">Bezpieczny tryb pracy</h3>
          <div className="mt-3 grid gap-2 text-xs text-slate-600">
            <TraceLine
              label="Typy problemów"
              values={summary.issue_types}
              empty="WILQ nie podał typów problemów; zacznij od odczytu Merchant."
            />
            <TraceLine
              label="Dowody"
              values={summary.evidence_summary_label ? [summary.evidence_summary_label] : []}
              empty="WILQ nie podał dowodów źródłowych; nie traktuj trybu pracy jako rekomendacji."
            />
            <TraceLine
              label="Akcje"
              values={[summary.action_summary_label]}
              empty="WILQ nie podał akcji do sprawdzenia; zostaje ręczna ocena."
            />
            <TraceLine
              label="Nie wolno twierdzić"
              values={summary.blocked_claim_labels}
            />
          </div>
          {actionIds.length > 0 ? (
            <a
              href={`/actions/${actionIds[0]}`}
              className="mt-4 inline-flex h-9 items-center rounded-md border border-line bg-white px-3 text-sm font-medium text-ink hover:bg-slate-100"
            >
              Sprawdź w WILQ
            </a>
          ) : null}
        </div>
      </div>
    </section>
  );
}

export function MerchantUnknowns({ data }: { data: MerchantDiagnosticsResponse }) {
  if (data.unknowns.length === 0) return null;
  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Czego nie wiemy o pliku produktowym Merchant Center
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Te ograniczenia blokują zbyt mocne wnioski i automatyczne zmiany pliku produktowego.
            Kolejka decyzji jest źródłem decyzji, a grupy problemów są szczegółowym
            przeglądem.
          </p>
        </div>
        <MetricTile label="Ograniczenia" value={data.unknowns.length} />
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {data.unknowns.map((unknown) => (
          <article key={unknown.id} className="rounded-md border border-line bg-slate-50 p-3">
            <h3 className="text-sm font-semibold text-ink">{unknown.title}</h3>
            <p className="mt-2 text-sm leading-6 text-slate-700">{unknown.reason}</p>
            <p className="mt-2 text-sm leading-6 text-slate-700">{unknown.impact}</p>
            <p className="mt-2 text-sm font-medium text-ink">{unknown.next_step}</p>
            <div className="mt-2 text-xs text-slate-600">
              <TraceLine
                label="Nie wolno twierdzić"
                values={unknown.blocked_claim_labels}
              />
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}


export function MerchantDiagnosticProof({ data }: { data: MerchantDiagnosticsResponse }) {
  const metricFacts = data.sections.flatMap((section) => section.metric_facts);
  const visibleMetricFacts = metricFacts.slice(0, 4);
  const blockedClaims = data.sections.flatMap((section) => section.blocked_claim_labels);
  const sectionTitles = data.sections.map((section) => section.label);
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Dowody i warunki przeglądu Merchant
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            To jest skrót źródeł danych i blokad w WILQ. Pełna kolejka pracy
            jest powyżej; tutaj widać, z jakich sekcji i dowodów wynika przegląd.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Obszary danych" value={data.sections.length} />
          <MetricTile label="Metryki" value={metricFacts.length} />
          <MetricTile label="Dowody" value={data.evidence_summary_label} />
        </div>
      </div>
      {visibleMetricFacts.length > 0 ? (
        <div className="mt-3 grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-4">
          {visibleMetricFacts.map((fact, index) => (
            <MetricTile
              key={`${fact.source_connector}-${fact.name}-${fact.evidence_id}-${index}`}
              label={fact.metric_label || "Metryka bez etykiety"}
              value={fact.value}
            />
          ))}
        </div>
      ) : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <TraceLine label="Sekcje źródłowe" values={sectionTitles} />
        <TraceLine label="Źródła danych" values={data.source_connector_labels} />
        <TraceLine
          label="Akcje"
          values={[data.action_summary_label]}
          empty="WILQ nie podał akcji; panel zostaje tylko podsumowaniem dowodów."
        />
        <TraceLine label="Nie wolno twierdzić" values={blockedClaims} />
      </div>
    </section>
  );
}

