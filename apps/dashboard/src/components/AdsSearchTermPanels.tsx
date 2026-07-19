import { AdsDiagnosticsResponse } from "../lib/api";
import { adsCost, adsNumber } from "../lib/adsFormatting";
import { adsMissingAdGroupLabel, adsMissingCampaignLabel } from "../lib/adsLabels";
import { BlockerNotice, LabelChipRow, MetricTile } from "./OperatorPrimitives";
import { TraceLine } from "./TraceLine";

type AdsSearchTermMetricRow =
  AdsDiagnosticsResponse["search_terms_read_contract"]["search_term_rows"][number];
type AdsSearchTermNgramRow =
  AdsDiagnosticsResponse["search_term_ngram_read_contract"]["ngram_rows"][number];
type AdsSearchTermSafetyRow =
  AdsDiagnosticsResponse["search_term_safety_read_contract"]["safety_rows"][number];
type AdsKeywordMatchContextRow =
  AdsDiagnosticsResponse["keyword_match_context_read_contract"]["context_rows"][number];

type AdsSearchTermCoverage =
  AdsDiagnosticsResponse["search_terms_read_contract"]["coverage"][number];

function adsServiceBindingLabel(
  binding: AdsSearchTermMetricRow["landing_service_binding"]
) {
  if (!binding) return "usługa: brak exact powiązania";
  if (binding.status === "approved_current") return "usługa: potwierdzona";
  if (binding.status === "review_required") return "usługa: wymaga review";
  if (binding.status === "ambiguous") return "usługa: niejednoznaczna";
  return "usługa: niepowiązana";
}

export function AdsSearchTermCoveragePanel({
  coverage
}: {
  coverage: AdsSearchTermCoverage[];
}) {
  if (coverage.length === 0) return null;
  const visibleCoverage = Array.from(
    new Map(coverage.map((item) => [item.window, item])).values()
  );
  return (
    <div
      className="rounded-md border border-wait/30 bg-wait/10 p-3 text-xs leading-5 text-slate-700"
      data-testid="ads-search-term-coverage"
    >
      <div className="font-semibold text-ink">Zakres odczytu zapytań</div>
      <div className="mt-1 grid gap-1 md:grid-cols-2">
        {visibleCoverage.map((item) => (
          <div key={`${item.window}-${item.window_label}`}>
            {item.window_label}: {item.returned_row_count} z maks. {item.connector_cap ?? "brak limitu"} wierszy
            {item.cap_applied ? " · osiągnięto limit" : " · próbka poniżej limitu"}. {item.privacy_omission_caveat}
          </div>
        ))}
      </div>
    </div>
  );
}

export function AdsSearchTermReviewSummaryPanel({
  contract,
  currencyCode
}: {
  contract: AdsDiagnosticsResponse["search_term_review_summary_contract"];
  currencyCode?: string;
}) {
  if (contract.status === "blocked") {
    return <BlockerNotice message={contract.summary} />;
  }

  return (
    <div className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-ink">Kolejność oceny zapytań</h3>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            {contract.summary}
          </p>
          <p className="mt-1 text-sm font-medium text-ink">{contract.next_step}</p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs sm:grid-cols-4">
          <MetricTile label="Zapytania" value={contract.total_search_term_count} />
          <MetricTile label="Zero conv." value={contract.zero_conversion_search_term_count} />
          <MetricTile label="Kliknięcia" value={contract.total_clicks} />
          <MetricTile label="Koszt" value={adsCost(contract.total_cost_micros, currencyCode)} />
        </div>
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-2">
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Kampanie do przejrzenia
          </h4>
          <div className="mt-2 overflow-x-auto rounded-md border border-line bg-white">
            <table className="min-w-full text-left text-xs">
              <thead className="border-b border-line bg-slate-50 uppercase tracking-normal text-slate-500">
                <tr>
                  <th className="py-2 pl-3 pr-3 font-semibold">Kampania</th>
                  <th className="py-2 pr-3 font-semibold">Zapytania</th>
                  <th className="py-2 pr-3 font-semibold">Zero conv.</th>
                  <th className="py-2 pr-3 font-semibold">Koszt</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {contract.campaign_review_rows.slice(0, 6).map((row) => (
                  <tr key={`${row.campaign_id ?? "unknown"}-${row.campaign_name ?? "campaign"}`}>
                    <td className="py-2 pl-3 pr-3 font-medium text-ink">
                      {row.campaign_label || adsMissingCampaignLabel}
                    </td>
                    <td className="py-2 pr-3 text-slate-700">{row.search_term_count}</td>
                    <td className="py-2 pr-3 text-slate-700">
                      {row.zero_conversion_search_term_count}
                    </td>
                    <td className="py-2 pr-3 text-slate-700">
                      {adsCost(row.cost_micros, currencyCode)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div>
          <h4 className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Top kosztowe zapytania
          </h4>
          <div className="mt-2 grid gap-2">
            {contract.top_cost_search_terms.slice(0, 5).map((row) => (
              <div
                key={`${row.search_term}-${row.campaign_id ?? "unknown"}-${
                  row.ad_group_id ?? "unknown"
                }`}
                className="rounded-md border border-line bg-white p-2"
              >
                <div className="text-sm font-medium text-ink">{row.search_term}</div>
                <LabelChipRow
                  className="mt-1"
                  chips={[
                    { label: "Kampania", value: row.campaign_label || adsMissingCampaignLabel },
                    { label: "Koszt", value: adsCost(row.cost_micros, currencyCode) },
                    { label: "Konwersje", value: adsNumber(row.conversions) }
                  ]}
                />
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-3 grid gap-2 text-xs text-slate-600 md:grid-cols-2">
        <TraceLine
          label="Wymaga oceny"
          values={[contract.operator_review_gate_summary_label]}
        />
        <TraceLine
          label="Nie wolno twierdzić"
          values={[contract.blocked_claim_summary_label]}
        />
      </div>
    </div>
  );
}

export function AdsSearchTermRowsTable({
  rows,
  currencyCode
}: {
  rows: AdsSearchTermMetricRow[];
  currencyCode?: string;
}) {
  if (rows.length === 0) {
    return (
      <BlockerNotice message="Brak szczegółowych wierszy zapytań. WILQ nie może analizować zapytań ani strat budżetu bez danych o wyszukiwanych hasłach." />
    );
  }
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-line bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
          <tr>
            <th className="py-2 pl-3 pr-4 font-semibold">Zapytanie</th>
            <th className="py-2 pr-4 font-semibold">Kampania</th>
            <th className="py-2 pr-4 font-semibold">Grupa reklam</th>
            <th className="py-2 pr-4 font-semibold">Kliknięcia</th>
            <th className="py-2 pr-4 font-semibold">Wyświetlenia</th>
            <th className="py-2 pr-4 font-semibold">Koszt</th>
            <th className="py-2 pr-4 font-semibold">Konwersje</th>
            <th className="py-2 pr-4 font-semibold">Landing</th>
            <th className="py-2 pr-3 font-semibold">Dowody</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.slice(0, 12).map((row) => (
            <tr
              key={`${row.search_term}-${row.campaign_id ?? "unknown"}-${
                row.ad_group_id ?? "unknown"
              }`}
            >
              <td className="py-2 pl-3 pr-4 font-medium text-ink">{row.search_term}</td>
              <td className="py-2 pr-4 text-slate-700">
                {row.campaign_label || adsMissingCampaignLabel}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.ad_group_label || adsMissingAdGroupLabel}
              </td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.clicks)}</td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.impressions)}</td>
              <td className="py-2 pr-4 text-slate-700">
                {adsCost(row.cost_micros, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.conversions)}</td>
              <td className="py-2 pr-4 text-xs text-slate-700">
                <div>{adsLandingMappingLabel(row.landing_mapping_status)}</div>
                <div className="mt-1 text-[11px] text-slate-500" data-testid="ads-service-binding-status">
                  {adsServiceBindingLabel(row.landing_service_binding)}
                </div>
              </td>
              <td className="py-2 pr-3 text-xs text-slate-600">
                {row.evidence_summary_label}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function AdsSearchTermNgramRowsTable({
  rows,
  currencyCode,
  compact = false
}: {
  rows: AdsSearchTermNgramRow[];
  currencyCode?: string;
  compact?: boolean;
}) {
  if (rows.length === 0) {
    return (
      <BlockerNotice message="Brak n-gramów zapytań. WILQ musi najpierw mieć wiersze wyszukiwanych haseł z Google Ads." />
    );
  }
  const visibleRows = rows.slice(0, compact ? 5 : 12);
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-line bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
          <tr>
            <th className="py-2 pl-3 pr-4 font-semibold">Temat z zapytań</th>
            <th className="py-2 pr-4 font-semibold">Źródłowe zapytania</th>
            <th className="py-2 pr-4 font-semibold">Przykłady</th>
            <th className="py-2 pr-4 font-semibold">Kliknięcia</th>
            <th className="py-2 pr-4 font-semibold">Wyświetlenia</th>
            <th className="py-2 pr-4 font-semibold">Koszt</th>
            <th className="py-2 pr-4 font-semibold">Konwersje</th>
            <th className="py-2 pr-3 font-semibold">Dowody</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {visibleRows.map((row) => (
            <tr key={`${row.ngram_size}-${row.ngram}`}>
              <td className="py-2 pl-3 pr-4 font-medium text-ink">
                {row.ngram}
                <span className="ml-2 text-xs font-normal text-slate-500">
                  {row.ngram_size}-gram
                </span>
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {adsNumber(row.source_search_term_count)}
              </td>
              <td className="max-w-sm py-2 pr-4 text-xs leading-5 text-slate-600">
                {row.sample_search_terms.join(", ")}
              </td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.clicks)}</td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.impressions)}</td>
              <td className="py-2 pr-4 text-slate-700">
                {adsCost(row.cost_micros, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.conversions)}</td>
              <td className="py-2 pr-3 text-xs text-slate-600">
                {row.evidence_summary_label}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function AdsSearchTermSafetyRowsTable({
  rows,
  currencyCode
}: {
  rows: AdsSearchTermSafetyRow[];
  currencyCode?: string;
}) {
  if (rows.length === 0) {
    return (
      <BlockerNotice message="Brak 90-dniowego odczytu bezpieczeństwa dla zapytań. WILQ nie powinien zdejmować blokady z oceny wykluczeń bez tego odczytu." />
    );
  }
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-line bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
          <tr>
            <th className="py-2 pl-3 pr-4 font-semibold">Bezpieczeństwo 90 dni</th>
            <th className="py-2 pr-4 font-semibold">Kampania</th>
            <th className="py-2 pr-4 font-semibold">Grupa reklam</th>
            <th className="py-2 pr-4 font-semibold">Kliknięcia</th>
            <th className="py-2 pr-4 font-semibold">Wyświetlenia</th>
            <th className="py-2 pr-4 font-semibold">Koszt</th>
            <th className="py-2 pr-4 font-semibold">Konwersje</th>
            <th className="py-2 pr-3 font-semibold">Dowody</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.slice(0, 12).map((row) => (
            <tr
              key={`90d-${row.search_term}-${row.campaign_id ?? "unknown"}-${
                row.ad_group_id ?? "unknown"
              }`}
            >
              <td className="py-2 pl-3 pr-4 font-medium text-ink">{row.search_term}</td>
              <td className="py-2 pr-4 text-slate-700">
                {row.campaign_label || adsMissingCampaignLabel}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.ad_group_label || adsMissingAdGroupLabel}
              </td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.clicks_90d)}</td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.impressions_90d)}</td>
              <td className="py-2 pr-4 text-slate-700">
                {adsCost(row.cost_micros_90d, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.conversions_90d)}</td>
              <td className="py-2 pr-3 text-xs text-slate-600">
                {row.evidence_summary_label}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function AdsKeywordMatchContextRowsTable({ rows }: { rows: AdsKeywordMatchContextRow[] }) {
  if (rows.length === 0) {
    return (
      <BlockerNotice message="Brak kontekstu istniejących słów kluczowych i typów dopasowania. WILQ nie powinien zdejmować blokady z oceny wykluczeń bez odczytu istniejących słów kluczowych i wykluczeń w grupach reklam." />
    );
  }
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-line bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
          <tr>
            <th className="py-2 pl-3 pr-4 font-semibold">Słowo kluczowe</th>
            <th className="py-2 pr-4 font-semibold">Typ dopasowania</th>
            <th className="py-2 pr-4 font-semibold">Status</th>
            <th className="py-2 pr-4 font-semibold">Kampania</th>
            <th className="py-2 pr-4 font-semibold">Grupa reklam</th>
            <th className="py-2 pr-3 font-semibold">Dowody</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.slice(0, 12).map((row) => (
            <tr
              key={`kw-${row.criterion_id ?? row.keyword_text}-${
                row.ad_group_id ?? "unknown"
              }`}
            >
              <td className="py-2 pl-3 pr-4 font-medium text-ink">{row.keyword_text}</td>
              <td className="py-2 pr-4 text-slate-700">
                {row.match_type_label || "typ dopasowania do potwierdzenia"}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.negative_label || row.criterion_status_label || "status do potwierdzenia"}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.campaign_label || adsMissingCampaignLabel}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.ad_group_label || adsMissingAdGroupLabel}
              </td>
              <td className="py-2 pr-3 text-xs text-slate-600">
                {row.evidence_summary_label}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function adsLandingMappingLabel(status: string | null | undefined): string {
  switch (status) {
    case "resolved":
      return "landing dopasowany";
    case "page_only":
      return "tylko strona · do potwierdzenia";
    case "ambiguous":
      return "landing niejednoznaczny";
    case "missing":
      return "brak mapowania";
    case "blocked":
      return "mapowanie zablokowane";
    default:
      return "mapowanie do sprawdzenia";
  }
}
