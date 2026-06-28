import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ClipboardCheck, ShieldAlert } from "lucide-react";

import { getLocaloDiagnostics, LocaloDiagnosticsResponse } from "../lib/api";
import { MetricFactChips } from "../components/MetricFactChips";
import { BlockerNotice, LoadingBand, MetricTile } from "../components/OperatorPrimitives";
import { TraceLine } from "../components/TraceLine";

type LocaloDecisionItem = LocaloDiagnosticsResponse["decision_queue"][number];

export function LocaloDiagnosticSurface() {
  const diagnostics = useQuery({
    queryKey: ["localo-diagnostics"],
    queryFn: getLocaloDiagnostics
  });

  if (diagnostics.isLoading) return <LoadingBand />;
  if (diagnostics.error || !diagnostics.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać danych Localo. Ten widok nie może udawać rankingów, danych profilu firmy w Google ani lokalnej widoczności bez WILQ." />
      </main>
    );
  }

  const data = diagnostics.data;
  const latestRefresh = data.latest_refresh;

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Localo</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Dedykowany widok Localo z WILQ. Oddziela sam dostęp do danych od
            lokalnych rankingów, profilu firmy w Google, konkurencji i opinii,
            żeby marketer nie dostał fałszywej rekomendacji lokalnego SEO.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Dane lokalne" value={data.visibility_fact_count} />
          <MetricTile label="Braki danych" value={data.operator_summary.missing_read_contract_summary_label} />
          <MetricTile label="Blokady" value={data.blocker_count} />
        </div>
      </div>

      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Status Localo / widoczność lokalna
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">{data.strict_instruction}</p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="rounded-md border border-line px-2 py-1 text-slate-600">
              Źródło Localo: {data.connector_status_label}
              <span className="sr-only">; </span>
            </span>
            <span className="rounded-md border border-line px-2 py-1 text-slate-600">
              {data.access_probe.status_label}
              <span className="sr-only">; </span>
            </span>
            {latestRefresh ? (
              <span className="rounded-md border border-line px-2 py-1 text-slate-600">
                ostatni odczyt: {data.latest_refresh_status_label}
                <span className="sr-only">; </span>
              </span>
            ) : null}
          </div>
        </div>
        <p className="mt-3 text-sm leading-6 text-slate-700">{data.access_probe.summary}</p>
        {latestRefresh?.errors.length ? (
          <div className="mt-3 rounded-md border border-risk/30 bg-risk/10 p-3 text-sm text-risk">
            {latestRefresh.errors[0]}
          </div>
        ) : null}
      </section>

      <LocaloVisibilitySnapshot data={data} />
      <LocaloOperatorSummary data={data} />
      <LocaloDiagnosticProof data={data} />

      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <div className="mb-3 flex items-start gap-3">
          <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
            <ShieldAlert aria-hidden="true" size={18} />
          </div>
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Brama bezpieczeństwa Localo i profilu firmy w Google
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              Sam dostęp do Localo potwierdza tylko możliwość odczytu danych. WILQ nie publikuje
              postów w profilu firmy w Google, nie zmienia profilu i nie obiecuje poprawy
              widoczności bez danych rankingów i profilu firmy w Google, sprawdzonej akcji
              oraz audytu.
            </p>
          </div>
        </div>
        <div className="grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
          <TraceLine
            label="Dowody"
            values={[data.operator_summary.evidence_summary_label]}
            empty="brak"
          />
          <TraceLine label="Źródła" values={data.operator_summary.source_connector_labels} />
          <TraceLine
            label="Czego nie wolno obiecać"
            values={uniqueValues(
              data.decision_queue.flatMap((decision) =>
                decision.blocked_claim_labels
              )
            )}
          />
          <TraceLine
            label="Brakujące dane"
            values={uniqueValues(
              data.decision_queue.flatMap((decision) =>
                decision.missing_read_contract_labels
              )
            )}
          />
        </div>
      </section>
    </main>
  );
}

function LocaloVisibilitySnapshot({ data }: { data: LocaloDiagnosticsResponse }) {
  const visibilityDecision =
    data.decision_queue.find((decision) => decision.decision_type === "review_local_visibility") ??
    data.decision_queue.find((decision) => decision.status === "ready") ??
    data.decision_queue[0];
  const metricEntries = Object.entries(visibilityDecision?.metric_tiles ?? {}).filter(
    ([label]) => label !== "dostęp Localo"
  );

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-3">
        <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
          Aktualny odczyt lokalnej widoczności
        </h2>
        <p className="mt-1 text-sm leading-6 text-slate-600">
          To jest marketerowy skrót z danych Localo dostępnych w WILQ. Szczegóły
          techniczne są niżej, a lokalne obietnice pozostają
          zablokowane, jeśli brakuje danych o rankingach, profilu firmy w Google albo opiniach.
        </p>
      </div>
      {visibilityDecision ? (
        <div className="rounded-md border border-line p-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-base font-semibold">Dane Localo w WILQ</h3>
              <p className="mt-2 text-sm leading-6 text-slate-700">
                {visibilityDecision.summary}
              </p>
            </div>
            <span className="rounded-md border border-line px-2 py-1 text-xs font-semibold text-ink">
              {visibilityDecision.status_label}
            </span>
          </div>
          {metricEntries.length > 0 ? (
            <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
              {metricEntries.map(([label, value]) => (
                <MetricTile
                  key={`${visibilityDecision.id}-readout-${label}`}
                  label={label}
                  value={value}
                />
              ))}
            </div>
          ) : (
            <BlockerNotice message="Brak danych Localo do odczytu. WILQ pokazuje tylko stan dostępu i blokuje lokalne rekomendacje." />
          )}
          <p className="mt-3 text-sm font-semibold leading-6 text-ink">
            {visibilityDecision.next_step}
          </p>
        </div>
      ) : (
        <BlockerNotice message="Brak decyzji Localo w WILQ. Odczyt lokalny nie może zostać zbudowany." />
      )}
    </section>
  );
}

function LocaloOperatorSummary({ data }: { data: LocaloDiagnosticsResponse }) {
  const summary = data.operator_summary;
  const decisionsById = new Map(data.decision_queue.map((decision) => [decision.id, decision]));
  const decisions = summary.top_decision_ids
    .map((decisionId) => decisionsById.get(decisionId))
    .filter((decision): decision is LocaloDecisionItem => Boolean(decision));
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="mb-4 flex items-start gap-3">
        <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
          <ClipboardCheck aria-hidden="true" size={18} />
        </div>
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            {summary.title}
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            {summary.summary}
          </p>
        </div>
      </div>
      {decisions.length === 0 ? (
        <BlockerNotice message="Brak decyzji Localo w WILQ. Widok nie wygeneruje lokalnej rekomendacji z pustego stanu." />
      ) : (
        <div className="grid gap-3 xl:grid-cols-2">
          {decisions.map((decision) => (
            <LocaloDecisionCard key={decision.id} decision={decision} />
          ))}
        </div>
      )}
    </section>
  );
}

function LocaloDecisionCard({ decision }: { decision: LocaloDecisionItem }) {
  const marketerMetricTiles = Object.entries(decision.metric_tiles ?? {}).filter(
    ([label]) => label !== "dostęp Localo"
  );

  return (
    <article className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Localo / {decision.decision_type_label} / {decision.priority_label}
          </p>
          <h3 className="mt-1 text-base font-semibold">{decision.title}</h3>
        </div>
        <span className="rounded-md border border-line px-2 py-1 text-xs font-semibold text-ink">
          {decision.status_label}
        </span>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">{decision.summary}</p>
      <p className="mt-2 text-sm leading-6 text-slate-600">{decision.rationale}</p>
      <p className="mt-3 text-sm font-semibold leading-6 text-ink">{decision.next_step}</p>
      {marketerMetricTiles.length > 0 ? (
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
          {marketerMetricTiles.map(([label, value]) => (
            <MetricTile key={`${decision.id}-${label}`} label={label} value={value} />
          ))}
        </div>
      ) : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <TraceLine label="Dostęp" values={[decision.access_status_label]} />
        <TraceLine
          label="Dozwolone dowody"
          values={decision.allowed_evidence_labels}
        />
        <TraceLine
          label="Brakujące dane"
          values={decision.missing_read_contract_labels}
        />
        <TraceLine
          label="Czego nie wolno obiecać"
          values={decision.blocked_claim_labels}
        />
        <TraceLine
          label="Dowody"
          values={[decision.evidence_summary_label]}
          empty="brak"
        />
      </div>
      {decision.metric_facts.length > 0 ? (
        <MetricFactChips facts={decision.metric_facts.slice(0, 6)} />
      ) : null}
    </article>
  );
}

function LocaloDiagnosticProof({ data }: { data: LocaloDiagnosticsResponse }) {
  const [showTechnicalProof, setShowTechnicalProof] = useState(false);
  const probe = data.access_probe;
  return (
    <section className="mt-6 rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Dowody i warunki diagnozy Localo
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            WILQ pokazuje techniczne potwierdzenie dostępu osobno od danych lokalnych.
            Brak danych oznacza brak diagnozy rankingów, nie zaproszenie do zgadywania.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowTechnicalProof((current) => !current)}
          className="inline-flex min-h-9 items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-ink hover:bg-slate-100"
        >
          {showTechnicalProof ? "Ukryj szczegóły techniczne Localo" : "Pokaż szczegóły techniczne Localo"}
        </button>
      </div>
      {showTechnicalProof ? (
        <>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <MetricTile label="Połączenie" value={probe.access_check_label} />
            <MetricTile
              label="Autoryzacja"
              value={probe.authorization_readiness_label}
            />
            <MetricTile label="Bezpieczeństwo połączenia" value={probe.secure_readiness_label} />
            <MetricTile label="Dostęp lokalny" value={probe.credential_readiness_label} />
          </div>
          <div className="mt-4 grid gap-3 xl:grid-cols-3">
            {data.sections.map((section) => (
              <article key={section.id} className="rounded-md border border-line p-3">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-sm font-semibold">{section.title}</h3>
                  <span className="rounded-md border border-line px-2 py-1 text-xs text-slate-600">
                    {section.status_label}
                  </span>
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-700">{section.summary}</p>
                <p className="mt-2 text-xs leading-5 text-slate-600">{section.next_step}</p>
              </article>
            ))}
          </div>
        </>
      ) : null}
      {data.visibility_fact_count === 0 ? (
        <BlockerNotice message="Brak danych Localo o rankingach, profilu firmy w Google i konkurencji. Ten ekran celowo blokuje lokalne rekomendacje marketingowe." />
      ) : null}
    </section>
  );
}

function uniqueValues(values: string[]) {
  return Array.from(new Set(values));
}
