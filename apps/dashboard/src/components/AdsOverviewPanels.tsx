import { AdsDiagnosticsResponse } from "../lib/api";
import { adsCost, adsNumber } from "../lib/adsFormatting";
import { MetricTile } from "./OperatorPrimitives";
import { TraceLine } from "./TraceLine";

type AdsDecisionItem = AdsDiagnosticsResponse["decision_queue"][number];

const adsMissingLatestReadLabel = "bez ostatniego odczytu; nie oceniaj trendu";

export function AdsCondensedDecisionPanel({
  data,
  currencyCode
}: {
  data: AdsDiagnosticsResponse;
  currencyCode: string | undefined;
}) {
  const summary = data.operator_summary;
  const decisionsById = new Map(data.decision_queue.map((decision) => [decision.id, decision]));
  const primaryDecision =
    summary.top_decision_ids
      .map((decisionId) => decisionsById.get(decisionId))
      .find((decision): decision is AdsDecisionItem => Boolean(decision)) ??
    data.decision_queue[0];
  const topBlockedClaimLabels =
    summary.top_blocked_claim_labels.length > 0
      ? summary.top_blocked_claim_labels
      : primaryDecision?.blocked_claim_labels ?? [];
  const blockedClaimSummary =
    summary.top_blocked_claim_summary_label ||
    primaryDecision?.blocked_claim_summary_label ||
    summary.blocked_claim_summary_label;
  const missingInputSummary = primaryDecision
    ? primaryDecision.missing_read_contract_summary_label
    : summary.missing_read_contract_summary_label;
  const evidenceSummary = primaryDecision
    ? primaryDecision.evidence_summary_label
    : summary.evidence_summary_label;
  const actionSummary = primaryDecision?.action_summary_label ?? summary.action_summary_label;
  const workSteps = [
    `Zacznij od kolejki ${summary.campaign_count} kampanii: sprawdź kampanie z największym ruchem, kosztem i sygnałem review.`,
    `Potem przejrzyj ${summary.search_term_count} wyszukiwanych haseł oraz ${data.negative_keywords_read_contract.candidates.length} propozycji wykluczeń, ale tylko jako review.`,
    "Nie zapisuj zmian w Ads: budżety, rekomendacje i wykluczenia wymagają podglądu, sprawdzenia w WILQ i audytu."
  ];

  return (
    <section className="mb-6 rounded-md border border-action/30 bg-action/5 p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-action">
            Google Ads: co dziś zrobić
          </div>
          <h2 className="mt-1 text-lg font-semibold tracking-normal text-ink">
            {primaryDecision
              ? `Najpierw: ${primaryDecision.decision_type_label}`
              : "Najpierw sprawdź Ads"}
          </h2>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-700">
            {primaryDecision
              ? primaryDecision.summary
              : "WILQ ma odczyt Google Ads i pokazuje, co można sprawdzić bez udawania optymalizatora."}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-4">
          <MetricTile label="Kliknięcia" value={adsNumber(summary.total_clicks)} />
          <MetricTile label="Koszt" value={adsCost(summary.total_cost_micros, currencyCode)} />
          <MetricTile label="Konwersje" value={adsNumber(summary.total_conversions)} />
          <MetricTile label="Akcje" value={actionSummary} />
        </div>
      </div>

      <div className="mt-4 rounded-md border border-line bg-white p-3">
        <h3 className="text-sm font-semibold text-ink">Kolejność pracy</h3>
        <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm leading-6 text-slate-700">
          {workSteps.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Dlaczego to ma znaczenie</h3>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            {primaryDecision
              ? primaryDecision.rationale
              : "Ads ma aktualne dowody, ale decyzje budżetowe i zapis zmian nadal wymagają celów, sprawdzenia w WILQ i audytu."}
          </p>
        </div>
        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Bezpieczny następny krok</h3>
          <p className="mt-2 text-sm font-medium leading-6 text-ink">
            {primaryDecision
              ? primaryDecision.next_step
              : "Przejrzyj kolejkę Ads i wybierz jedną akcję do sprawdzenia bez zapisu zmian."}
          </p>
        </div>
        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Dowody i źródła</h3>
          <div className="mt-2 grid gap-1 text-xs leading-5 text-slate-600">
            <TraceLine label="Dowody" values={[evidenceSummary]} />
            <TraceLine label="Źródła" values={data.source_connector_labels} />
            <TraceLine
              label="Stan danych"
              values={[
                data.live_data_status_label,
                data.latest_refresh
                  ? `ostatni odczyt: ${data.latest_refresh_status_label}`
                  : adsMissingLatestReadLabel
              ]}
            />
          </div>
        </div>
        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Czego WILQ nie powie</h3>
          <div className="mt-2 grid gap-1 text-xs leading-5 text-slate-600">
            <TraceLine
              label="Nie wolno twierdzić"
              values={topBlockedClaimLabels}
              empty={blockedClaimSummary}
            />
            <TraceLine label="Brakujące wejścia" values={[missingInputSummary]} />
          </div>
        </div>
      </div>

      <div className="mt-3 rounded-md border border-line bg-white p-3">
        <h3 className="text-sm font-semibold text-ink">Jak później sprawdzimy efekt</h3>
        <p className="mt-2 text-sm leading-6 text-slate-700">
          {primaryDecision?.measurement_plan ?? data.operator_summary.next_step}
        </p>
      </div>
    </section>
  );
}

export function AdsMarketSnapshot({
  data,
  currencyCode
}: {
  data: AdsDiagnosticsResponse;
  currencyCode: string | undefined;
}) {
  const summary = data.operator_summary;
  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Aktualny odczyt Ads
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Szybki obraz tego, co WILQ może dziś uczciwie przejrzeć w Ads.
            Zapis zmian, ocena zmarnowanego budżetu, koszt pozyskania celu,
            zwrot z reklam i skalowanie budżetu pozostają zablokowane do czasu
            sprawdzenia w WILQ oraz uzupełnienia brakujących danych.
          </p>
        </div>
        <MetricTile label="Waluta" value={currencyCode ?? "waluta do potwierdzenia"} />
      </div>
      <div className="mb-3 text-xs font-semibold uppercase tracking-normal text-slate-600">
        Wartości Ads
      </div>
      <div className="grid gap-2 text-center text-xs sm:grid-cols-2 xl:grid-cols-5">
        <MetricTile label="Kliknięcia" value={adsNumber(summary.total_clicks)} />
        <MetricTile label="Wyświetlenia" value={adsNumber(summary.total_impressions)} />
        <MetricTile label="Koszt" value={adsCost(summary.total_cost_micros, currencyCode)} />
        <MetricTile label="Konwersje" value={adsNumber(summary.total_conversions)} />
        <MetricTile label="Wartość konwersji" value={adsNumber(summary.total_conversion_value)} />
      </div>
      <div className="mt-3 grid gap-2 text-center text-xs sm:grid-cols-3 xl:grid-cols-6">
        <MetricTile label="Kampanie" value={summary.campaign_count} />
        <MetricTile label="Zapytania" value={summary.search_term_count} />
        <MetricTile
          label="Rekomendacje"
          value={data.recommendations_read_contract.recommendation_rows.length}
        />
        <MetricTile label="Budżety" value={data.budget_pacing_read_contract.budget_rows.length} />
        <MetricTile label="Gotowe" value={summary.ready_area_count} />
        <MetricTile label="Blokady" value={summary.blocked_area_count} />
      </div>
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <TraceLine
          label="Brakujące dane"
          values={[summary.missing_read_contract_summary_label]}
          empty="dane kompletne"
        />
        <TraceLine
          label="Nie wolno twierdzić"
          values={summary.top_blocked_claim_labels}
          empty={
            summary.blocked_claim_summary_label ||
            "WILQ nie zgłosił dodatkowych zablokowanych obietnic."
          }
        />
      </div>
      <div className="mt-3 rounded-md border border-line bg-slate-50/70 p-3 text-xs leading-5 text-slate-600">
        <div className="font-semibold text-ink">Zakres odczytu</div>
        <div className="mt-1 grid gap-1 sm:grid-cols-2">
          <span>
            Kampanie: {data.aggregation_contract.campaign_rows_returned}/
            {data.aggregation_contract.campaign_rows_available ?? "?"} · {data.aggregation_contract.campaign_window}
          </span>
          <span>
            Zapytania: {data.aggregation_contract.search_term_rows_returned}/
            {data.aggregation_contract.search_term_rows_available ?? "?"} · okna 30/90 dni
          </span>
          <span>
            {data.aggregation_contract.is_exhaustive
              ? "Pełny odczyt"
              : data.aggregation_contract.view === "summary"
                ? "Skrót — nie pełna kolejka"
                : "Pełny odczyt w granicach limitów źródła"}
          </span>
          <span>
            Waluta: {data.aggregation_contract.currency_code ?? "do potwierdzenia"} · {data.aggregation_contract.money_aggregation_allowed ? "potwierdzona" : "zablokowana"}
          </span>
        </div>
      </div>
    </section>
  );
}
