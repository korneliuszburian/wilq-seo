import { AdsDiagnosticsResponse } from "../lib/api";
import { adsCost, adsNumber, adsStrategyContextValue } from "../lib/adsFormatting";
import {
  adsMissingCampaignLabel,
  adsMissingCampaignMetricsLabel,
  adsMissingChangeIdLabel,
  adsMissingDateLabel
} from "../lib/adsLabels";
import { BlockerNotice, LabelChipRow, MetricTile } from "./OperatorPrimitives";
import { LinkedTraceLine, TraceLine } from "./TraceLine";

type AdsChangeImpactReadinessRow =
  AdsDiagnosticsResponse["change_impact_readiness_contract"]["readiness_rows"][number];

export function AdsBusinessTargetInterpretationPanel({
  contract
}: {
  contract: AdsDiagnosticsResponse["business_context_read_contract"];
}) {
  const interpretation = contract.target_interpretation;
  const strategyReadiness = contract.strategy_review_readiness_contract;
  return (
    <div className="rounded-md border border-line bg-slate-50 p-3 text-sm">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="font-semibold text-ink">Interpretacja celu biznesowego Ads</h3>
          <p className="mt-1 text-slate-700">{interpretation.summary}</p>
        </div>
        <span className="rounded-md border border-line bg-white px-2 py-1 text-xs text-slate-600">
          {interpretation.status_label}
        </span>
      </div>
      <div className="mt-3 grid gap-2 text-xs text-slate-600 md:grid-cols-2">
        <TraceLine
          label="Wolno użyć jako"
          values={interpretation.allowed_use_labels}
          empty="WILQ nie podał dozwolonego użycia; nie rozszerzaj wniosku poza review."
        />
        <TraceLine
          label="Zablokowane użycia"
          values={interpretation.blocked_use_labels}
          empty="WILQ nie podał zablokowanych użyć; nadal obowiązują blokady obietnic z kontraktu."
        />
        <TraceLine
          label="Braki"
          values={interpretation.missing_requirement_labels}
          empty="WILQ nie zgłosił brakujących wymagań; nadal sprawdź dowody przed akcją."
        />
        <TraceLine
          label="Polityki"
          values={[interpretation.policy_summary_label]}
          empty="WILQ nie podał polityki oceny; nie automatyzuj decyzji."
        />
        <TraceLine
          label="Akcje do sprawdzenia"
          values={[interpretation.action_summary_label]}
          empty="WILQ nie podał akcji do sprawdzenia; zostaje ręczny przegląd Ads."
        />
      </div>
      <div className="mt-3 rounded-md border border-line bg-white p-3">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <h4 className="text-sm font-semibold text-ink">
              Gotowość oceny strategii Ads
            </h4>
            <p className="mt-1 text-xs leading-5 text-slate-600">
              {strategyReadiness.summary}
            </p>
          </div>
          <LabelChipRow
            chips={[
              { label: "Status", value: strategyReadiness.status_label },
              { label: "Ostatnie sprawdzenie", value: strategyReadiness.latest_review_status_label }
            ]}
          />
        </div>
        <div className="mt-3 grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-5">
          <MetricTile
            label="Marża"
            value={adsStrategyContextValue(strategyReadiness.current_context.profit_margin)}
          />
          <MetricTile
            label="Docelowy zwrot z reklam"
            value={adsStrategyContextValue(strategyReadiness.current_context.target_roas)}
          />
          <MetricTile
            label="Docelowy koszt pozyskania celu"
            value={adsStrategyContextValue(strategyReadiness.current_context.target_cpa_micros)}
          />
          <MetricTile label="Braki" value={strategyReadiness.missing_read_contract_summary_label} />
          <MetricTile label="Ocena" value={strategyReadiness.latest_review_status_label} />
        </div>
        <p className="mt-3 text-xs font-medium text-ink">{strategyReadiness.next_step}</p>
        <div className="mt-3 grid gap-2 text-xs text-slate-600 md:grid-cols-2">
          <TraceLine
            label="Wymagane sprawdzenie"
            values={[strategyReadiness.required_validation_summary_label]}
            empty="WILQ nie podał wymaganego sprawdzenia; nie wykonuj zmiany bez review."
          />
          <TraceLine
            label="Braki"
            values={[strategyReadiness.missing_read_contract_summary_label]}
            empty="dane kompletne"
          />
          <TraceLine
            label="Nie wolno twierdzić"
            values={[strategyReadiness.blocked_claim_summary_label]}
            empty="WILQ nie zgłosił dodatkowych zablokowanych obietnic."
          />
          <TraceLine
            label="Akcje do sprawdzenia"
            values={[strategyReadiness.action_summary_label]}
            empty="WILQ nie podał akcji do sprawdzenia; zostaje ręczny przegląd Ads."
          />
        </div>
      </div>
    </div>
  );
}

export function AdsChangeImpactReadinessPanel({
  contract,
  currencyCode
}: {
  contract: AdsDiagnosticsResponse["change_impact_readiness_contract"];
  currencyCode?: string;
}) {
  const rows = contract.readiness_rows;
  const currentReadoutCount = rows.filter((row) => row.current_campaign_metrics_available).length;

  return (
    <div className="rounded-md border border-line bg-slate-50 p-3">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-ink">Gotowość oceny wpływu zmian</h3>
          <p className="mt-1 max-w-3xl text-xs leading-5 text-slate-600">
            {contract.summary}
          </p>
          <p className="mt-2 text-xs font-medium text-ink">{contract.next_step}</p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Zmiany" value={rows.length} />
          <MetricTile label="Odczyty" value={currentReadoutCount} />
          <MetricTile label="Status" value={contract.status_label} />
        </div>
      </div>

      {rows.length === 0 ? (
        <BlockerNotice message="Brak zdarzeń historii zmian do oceny wpływu. WILQ może pokazać tylko blokadę, nie ocenę wpływu zmian." />
      ) : (
        <div className="grid gap-2">
          {rows.slice(0, 6).map((row) => (
            <AdsChangeImpactReadinessCard
              key={`${row.change_event_id ?? "change"}-${row.campaign_id ?? "campaign"}`}
              row={row}
              currencyCode={currencyCode}
            />
          ))}
        </div>
      )}

      <div className="mt-3 grid gap-2 text-xs text-slate-600 md:grid-cols-2">
        <TraceLine
          label="Metryki dostępne"
          values={contract.allowed_metric_labels}
          empty="WILQ nie podał metryk; nie oceniaj skuteczności z tego panelu."
        />
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
        <LinkedTraceLine
          label="Dowody"
          values={contract.evidence_ids.slice(0, 6)}
          kind="evidence"
          empty="WILQ nie podał dowodów źródłowych; nie traktuj tego jako rekomendacji Ads."
        />
      </div>
    </div>
  );
}

function AdsChangeImpactReadinessCard({
  row,
  currencyCode
}: {
  row: AdsChangeImpactReadinessRow;
  currencyCode?: string;
}) {
  return (
    <article className="rounded-md border border-line bg-white p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h4 className="text-sm font-semibold text-ink">
            {row.campaign_label || adsMissingCampaignLabel}
          </h4>
          <p className="mt-1 text-xs text-slate-500">
            {row.change_event_label || adsMissingChangeIdLabel} /{" "}
            {row.change_date_time ?? adsMissingDateLabel}
          </p>
        </div>
        <span className="rounded-md border border-line bg-slate-50 px-2 py-1 text-xs text-slate-600">
          {row.current_campaign_metrics_available
            ? "odczyt kampanii"
            : adsMissingCampaignMetricsLabel}
        </span>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-5">
        <MetricTile label="Kliknięcia" value={adsNumber(row.current_clicks)} />
        <MetricTile label="Wyświetlenia" value={adsNumber(row.current_impressions)} />
        <MetricTile label="Koszt" value={adsCost(row.current_cost_micros, currencyCode)} />
        <MetricTile label="Konwersje" value={adsNumber(row.current_conversions)} />
        <MetricTile label="Wartość konwersji" value={adsNumber(row.current_conversion_value)} />
      </div>
      <div className="mt-3 grid gap-2 text-xs text-slate-600 md:grid-cols-2">
        <TraceLine
          label="Zmienione pola"
          values={row.changed_field_labels}
          empty="WILQ nie podał zmienionych pól; nie oceniaj wpływu zmiany bez historii."
        />
        <TraceLine
          label="Braki"
          values={[row.missing_read_contract_summary_label]}
          empty="dane kompletne"
        />
        <TraceLine
          label="Blokady"
          values={[row.blocked_claim_summary_label]}
          empty="WILQ nie zgłosił dodatkowych zablokowanych obietnic."
        />
        <LinkedTraceLine
          label="Dowody"
          values={row.evidence_ids}
          kind="evidence"
          empty="WILQ nie podał dowodów źródłowych; nie traktuj tego jako rekomendacji Ads."
        />
      </div>
    </article>
  );
}
