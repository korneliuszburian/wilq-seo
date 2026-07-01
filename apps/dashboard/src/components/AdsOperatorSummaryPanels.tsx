import { AdsDiagnosticsResponse } from "../lib/api";
import { AdsCampaignTriageRowsPanel } from "./AdsCampaignPanels";
import { AdsCustomSegmentCandidatesPanel } from "./AdsCustomSegmentPanels";
import { AdsNegativeKeywordCandidatesPanel } from "./AdsNegativeKeywordCandidatesPanel";
import { AdsSearchTermNgramRowsTable } from "./AdsSearchTermPanels";
import { BlockerNotice, LabelChipRow, MetricTile } from "./OperatorPrimitives";
import { TraceLine } from "./TraceLine";

type AdsDecisionItem = AdsDiagnosticsResponse["decision_queue"][number];
type AdsOptimizerReadinessItem =
  AdsDiagnosticsResponse["optimizer_readiness_contract"]["readiness_items"][number];

export function AdsOperatorSummary({
  data
}: {
  data: AdsDiagnosticsResponse;
}) {
  const currencyCode = data.account_currency_read_contract.currency_code ?? undefined;
  const optimizer = data.optimizer_readiness_contract;
  const summary = data.operator_summary;
  const decisionsById = new Map(data.decision_queue.map((decision) => [decision.id, decision]));
  const decisions = summary.top_decision_ids
    .map((decisionId) => decisionsById.get(decisionId))
    .filter((decision): decision is AdsDecisionItem => Boolean(decision));
  const allowedMetrics = summary.allowed_metric_labels;
  const missingReadContractSummary = summary.missing_read_contract_summary_label;
  const operatorReviewGateSummary = summary.operator_review_gate_summary_label;
  const blockedClaimSummary = summary.blocked_claim_summary_label;

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Przegląd Google Ads
          </div>
          <h2 className="mt-1 text-base font-semibold tracking-normal">{summary.title}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            WILQ porządkuje bieżący odczyt Ads w kolejkę decyzji: kampanie,
            wyszukiwane hasła, wskaźniki, budżety i rekomendacje. To jest przegląd
            oparty o dowody, bez zapisu zmian i bez oceny opłacalności.
          </p>
          <p className="mt-2 max-w-3xl text-sm font-semibold leading-6 text-ink">
            Przejrzyj top decyzje w tej kolejności. Nie zapisuj wykluczeń,
            budżetów ani rekomendacji bez podglądu zmian, sprawdzenia w WILQ
            i oceny kontekstu biznesowego.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Kampanie" value={summary.campaign_count} />
          <MetricTile label="Budżety" value={data.budget_pacing_read_contract.budget_rows.length} />
          <MetricTile
            label="Rekomendacje"
            value={data.recommendations_read_contract.recommendation_rows.length}
          />
          <MetricTile
            label="Udział"
            value={data.impression_share_read_contract.impression_share_rows.length}
          />
          <MetricTile
            label="Zmiany"
            value={data.change_history_read_contract.change_history_rows.length}
          />
          <MetricTile label="Zapytania" value={summary.search_term_count} />
          <MetricTile label="Gotowe" value={summary.ready_area_count} />
          <MetricTile label="Blokady" value={summary.blocked_area_count} />
        </div>
      </div>

      <AdsOptimizerReadinessPanel contract={optimizer} />
      <AdsStartHerePanel decisions={decisions.slice(0, 3)} />

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="grid gap-3">
          {decisions.length > 0 ? (
            decisions.map((decision) => (
              <AdsDecisionCard
                key={decision.id}
                decision={decision}
                currencyCode={currencyCode}
              />
            ))
          ) : (
            <BlockerNotice message="Brak decyzji Ads. Najpierw uruchom odczyt Google Ads." />
          )}
        </div>

        <div className="rounded-md border border-line bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-ink">Bezpieczny tryb Ads</h3>
          <div className="mt-3 grid gap-2 text-xs text-slate-600">
            <TraceLine
              label="Metryki dostępne"
              values={allowedMetrics}
              empty="WILQ nie podał metryk; nie oceniaj skuteczności z tego panelu."
            />
            <TraceLine
              label="Waluta konta"
              values={[data.account_currency_read_contract.currency_code ?? "waluta do potwierdzenia"]}
              empty="waluta do potwierdzenia"
            />
            <TraceLine
              label="Brakujące dane"
              values={[missingReadContractSummary]}
              empty="dane kompletne"
            />
            <TraceLine
              label="Wymagana ocena"
              values={[operatorReviewGateSummary]}
              empty="WILQ nie podał wymaganej oceny; zostaje ręczny review."
            />
            <TraceLine
              label="Dowody"
              values={[summary.evidence_summary_label]}
              empty="WILQ nie podał dowodów źródłowych; nie traktuj tego jako rekomendacji Ads."
            />
            <TraceLine
              label="Akcje do sprawdzenia"
              values={[summary.action_summary_label]}
              empty="WILQ nie podał akcji do sprawdzenia; zostaje ręczny przegląd Ads."
            />
            <TraceLine
              label="Nie wolno twierdzić"
              values={[blockedClaimSummary]}
              empty="WILQ nie zgłosił dodatkowych zablokowanych obietnic."
            />
          </div>
        </div>
      </div>
    </section>
  );
}

function AdsStartHerePanel({ decisions }: { decisions: AdsDecisionItem[] }) {
  if (decisions.length === 0) {
    return null;
  }

  return (
    <div className="mb-4 rounded-md border border-line bg-white p-3">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-ink">Najpierw sprawdź w Ads</h3>
          <p className="mt-1 max-w-3xl text-xs leading-5 text-slate-600">
            Skrócona kolejność dla marketera. Pełne karty i akcje do sprawdzenia są niżej,
            ale ten pasek pokazuje, od czego zacząć bez przechodzenia przez całą listę.
          </p>
        </div>
        <span className="rounded-md border border-line bg-slate-50 px-2 py-1 text-xs text-slate-600">
          tryb: sprawdzenie przed zapisem zmian
        </span>
      </div>
      <div className="grid gap-2 lg:grid-cols-3">
        {decisions.map((decision, index) => (
          <article key={decision.id} className="rounded-md border border-line bg-slate-50 p-3">
            <div className="flex items-start gap-2">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-ink text-xs font-semibold text-white">
                {index + 1}
              </span>
              <div>
                <div className="text-sm font-semibold leading-5 text-ink">
                  Krok {index + 1}: {decision.title}
                </div>
                <LabelChipRow
                  className="mt-1"
                  chips={[
                    { label: "Typ", value: decision.decision_type_label },
                    { label: "Status", value: decision.status_label }
                  ]}
                />
              </div>
            </div>
            <p className="mt-2 text-xs leading-5 text-slate-700">
              {decision.start_here_summary}
            </p>
            <p className="mt-2 text-xs font-medium leading-5 text-ink">
              {decision.next_step}
            </p>
            <div className="mt-2 grid gap-1 text-xs text-slate-600">
              <TraceLine
                label="Akcje"
                values={[decision.action_summary_label]}
                empty="WILQ nie podał akcji do sprawdzenia; zostaje ręczny przegląd Ads."
              />
              <TraceLine
                label="Nie wolno"
                values={[decision.blocked_claim_summary_label]}
                empty="WILQ nie zgłosił dodatkowych zablokowanych obietnic."
              />
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function AdsOptimizerReadinessPanel({
  contract
}: {
  contract: AdsDiagnosticsResponse["optimizer_readiness_contract"];
}) {
  const readyItems = contract.readiness_items.filter((item) => item.status === "ready");
  const blockedItems = contract.readiness_items.filter((item) => item.status === "blocked");

  return (
    <div className="mb-4 rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-ink">
            Co można zrobić teraz w Ads
          </h3>
          <p className="mt-1 max-w-3xl text-xs leading-5 text-slate-600">
            WILQ ma obszary gotowe do ręcznej oceny i obszary nadal zablokowane.
            Ten panel pokazuje, co można przejrzeć teraz, a czego nie wolno
            jeszcze zamienić w decyzję albo zapis zmian.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Gotowe" value={contract.ready_area_count} />
          <MetricTile label="Zablokowane" value={contract.blocked_area_count} />
          <MetricTile label="Tryb" value={contract.mode_label} />
        </div>
      </div>

      <div className="mt-3 grid gap-3 xl:grid-cols-2">
        <AdsOptimizerReadinessGroup
          title="Gotowe do oceny"
          items={readyItems}
          empty="WILQ nie wskazał obszarów gotowych do oceny; nie traktuj tego panelu jako listy działań Ads."
        />
        <AdsOptimizerReadinessGroup
          title="Zablokowane wnioski i zapis zmian"
          items={blockedItems}
          empty="WILQ nie zgłosił aktywnych blokad; nadal sprawdź dowody przed zmianą w Ads."
        />
      </div>

      <div className="mt-3 grid gap-2 text-xs text-slate-600 md:grid-cols-2">
        <TraceLine
          label="Brakujące dane"
          values={[contract.missing_read_contract_summary_label]}
          empty="dane kompletne"
        />
        <TraceLine
          label="Nie wolno twierdzić"
          values={[contract.blocked_claim_summary_label]}
          empty="WILQ nie zgłosił dodatkowych zablokowanych obietnic."
        />
        <TraceLine
          label="Dowody"
          values={[contract.evidence_summary_label]}
          empty="WILQ nie podał dowodów źródłowych; nie traktuj tego jako rekomendacji Ads."
        />
        <TraceLine
          label="Akcje do sprawdzenia"
          values={[contract.action_summary_label]}
          empty="WILQ nie podał akcji do sprawdzenia; zostaje ręczny przegląd Ads."
        />
      </div>
    </div>
  );
}

function AdsOptimizerReadinessGroup({
  title,
  items,
  empty
}: {
  title: string;
  items: AdsOptimizerReadinessItem[];
  empty: string;
}) {
  if (items.length === 0) {
    return <BlockerNotice message={empty} />;
  }

  return (
    <div>
      <div className="mb-2 text-xs font-semibold uppercase tracking-normal text-slate-500">
        {title}
      </div>
      <div className="grid gap-2">
        {items.slice(0, 5).map((item) => (
          <article key={item.id} className="rounded-md border border-line bg-white p-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h4 className="text-sm font-semibold text-ink">
                  {item.label}
                </h4>
                <p className="mt-1 text-xs text-slate-500">
                  {item.title}
                </p>
              </div>
              <LabelChipRow
                chips={[
                  { label: "Status", value: item.status_label },
                  { label: "Ryzyko", value: item.risk_label }
                ]}
              />
            </div>
            <p className="mt-2 text-xs leading-5 text-slate-700">
              {item.summary}
            </p>
            <p className="mt-2 text-xs font-medium text-ink">
              {item.next_step}
            </p>
            <div className="mt-2 grid gap-1 text-xs text-slate-600">
              <TraceLine
                label="Warunki źródłowe"
                values={[item.source_contract_summary_label]}
                empty="WILQ nie podał warunków źródłowych; nie wykonuj zmiany bez sprawdzenia."
              />
              <TraceLine
                label="Braki"
                values={[item.missing_read_contract_summary_label]}
                empty="dane kompletne"
              />
              <TraceLine
                label="Blokady"
                values={[item.blocked_claim_summary_label]}
                empty="WILQ nie zgłosił dodatkowych zablokowanych obietnic."
              />
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function AdsDecisionCard({
  decision,
  currencyCode
}: {
  decision: AdsDecisionItem;
  currencyCode?: string;
}) {
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">{decision.title}</h3>
          <LabelChipRow
            className="mt-1"
            chips={[
              { label: "Typ", value: decision.decision_type_label },
              { label: "Status", value: decision.status_label }
            ]}
          />
        </div>
        <span className="rounded-md border border-line bg-white px-2 py-1 text-xs text-slate-600">
          ryzyko: {decision.risk_label}
        </span>
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-700">
        {decision.summary}
      </p>
      <p className="mt-2 text-sm leading-6 text-slate-600">
        {decision.rationale}
      </p>
      <p className="mt-2 text-sm font-medium text-ink">
        {decision.next_step}
      </p>
      {Object.keys(decision.metric_tiles).length > 0 ? (
        <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-700 sm:grid-cols-3">
          {Object.entries(decision.metric_tiles).map(([label, value]) => (
            <MetricTile key={`${decision.id}-${label}`} label={label} value={value} />
          ))}
        </div>
      ) : null}
      {decision.negative_keyword_candidates.length > 0 ? (
        <AdsNegativeKeywordCandidatesPanel
          candidates={decision.negative_keyword_candidates}
          currencyCode={currencyCode}
          compact
        />
      ) : null}
      {decision.custom_segment_candidates.length > 0 ? (
        <AdsCustomSegmentCandidatesPanel candidates={decision.custom_segment_candidates} compact />
      ) : null}
      {decision.search_term_ngram_rows.length > 0 ? (
        <div className="mt-3">
          <AdsSearchTermNgramRowsTable
            rows={decision.search_term_ngram_rows}
            currencyCode={currencyCode}
            compact
          />
        </div>
      ) : null}
      {decision.campaign_triage_rows.length > 0 ? (
        <div className="mt-3">
          <AdsCampaignTriageRowsPanel
            rows={decision.campaign_triage_rows}
            currencyCode={currencyCode}
            compact
          />
        </div>
      ) : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <TraceLine
          label="Dowody"
          values={[decision.evidence_summary_label]}
          empty="WILQ nie podał dowodów źródłowych; nie traktuj tego jako rekomendacji Ads."
        />
        <TraceLine label="Źródła" values={decision.source_connector_labels} />
        <TraceLine
          label="Akcje do sprawdzenia"
          values={[decision.action_summary_label]}
          empty="WILQ nie podał akcji do sprawdzenia; zostaje ręczny przegląd Ads."
        />
        {decision.operator_review_gates.length > 0 ? (
          <TraceLine
            label="Wymagana ocena"
            values={[decision.operator_review_gate_summary_label]}
          />
        ) : null}
        <TraceLine label="Nie wolno twierdzić" values={[decision.blocked_claim_summary_label]} />
      </div>
    </article>
  );
}
