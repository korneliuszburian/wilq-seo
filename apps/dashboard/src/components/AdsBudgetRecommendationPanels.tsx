import { AdsDiagnosticsResponse } from "../lib/api";
import {
  adsCost,
  adsPercent,
  adsSignedCost,
  adsSignedNumber
} from "../lib/adsFormatting";
import {
  adsMissingCampaignLabel,
  adsMissingDateLabel,
  adsMissingPreviewLabel,
  adsMissingRecommendedBudgetLabel
} from "../lib/adsLabels";
import { ActionPreviewCard } from "./ActionPreviewCard";
import { BlockerNotice, LabelChipRow, MetricTile } from "./OperatorPrimitives";
import { LinkedTraceLine, TraceLine } from "./TraceLine";

type AdsBudgetPacingRow =
  AdsDiagnosticsResponse["budget_pacing_read_contract"]["budget_rows"][number];
type AdsSharedBudgetDistributionRow =
  AdsDiagnosticsResponse["budget_pacing_read_contract"]["shared_budget_distribution_rows"][number];
type AdsRecommendationRow =
  AdsDiagnosticsResponse["recommendations_read_contract"]["recommendation_rows"][number];
type AdsImpressionShareRow =
  AdsDiagnosticsResponse["impression_share_read_contract"]["impression_share_rows"][number];
type AdsChangeHistoryRow =
  AdsDiagnosticsResponse["change_history_read_contract"]["change_history_rows"][number];

export function AdsBudgetPacingRowsTable({
  rows,
  currencyCode,
  emptyStateMessage
}: {
  rows: AdsBudgetPacingRow[];
  currencyCode?: string;
  emptyStateMessage?: string;
}) {
  if (rows.length === 0) {
    return (
      <BlockerNotice
        message={
          emptyStateMessage ||
          "Brak kontekstu budżetu kampanii. Odśwież dane Google Ads z polami budżetu, żeby pokazać koszt względem budżetu dziennego."
        }
      />
    );
  }
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-line bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
          <tr>
            <th className="py-2 pl-3 pr-4 font-semibold">Kampania</th>
            <th className="py-2 pr-4 font-semibold">Budżet</th>
            <th className="py-2 pr-4 font-semibold">Koszt 7 dni</th>
            <th className="py-2 pr-4 font-semibold">7-dniowy budżet</th>
            <th className="py-2 pr-4 font-semibold">Wydanie</th>
            <th className="py-2 pr-4 font-semibold">Rekomendacja Google</th>
            <th className="py-2 pr-4 font-semibold">Podgląd zmian</th>
            <th className="py-2 pr-3 font-semibold">Blokady</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.slice(0, 12).map((row) => (
            <tr key={`${row.campaign_id ?? "unknown"}-${row.budget_id ?? row.budget_name}`}>
              <td className="py-2 pl-3 pr-4 font-medium text-ink">
                <div>{row.campaign_name}</div>
                <LabelChipRow
                  className="mt-1"
                  chips={[
                    { label: "Kanał", value: row.advertising_channel_type_label },
                    { label: "Budżet", value: row.budget_period_label }
                  ]}
                />
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {adsCost(row.budget_amount_micros, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {adsCost(row.cost_micros_7d, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {adsCost(row.seven_day_budget_micros, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {adsPercent(row.spend_to_budget_ratio_7d)}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.has_recommended_budget
                  ? adsCost(row.recommended_budget_amount_micros, currencyCode)
                  : adsMissingRecommendedBudgetLabel}
              </td>
              <td className="min-w-48 py-2 pr-4 text-xs text-slate-600">
                {row.preview_card ? (
                  <div className="min-w-72">
                    <ActionPreviewCard card={row.preview_card} />
                  </div>
                ) : (
                  adsMissingPreviewLabel
                )}
              </td>
              <td className="py-2 pr-3 text-xs text-slate-600">
                {row.blocked_claim_summary_label}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function AdsSharedBudgetDistributionPanel({
  rows,
  currencyCode
}: {
  rows: AdsSharedBudgetDistributionRow[];
  currencyCode?: string;
}) {
  if (rows.length === 0) {
    return (
      <div className="rounded-md border border-line bg-slate-50 p-3 text-sm text-slate-600">
        Brak wspólnych budżetów w bieżącym odczycie albo każda kampania ma osobny
        budżet. To oznacza, że WILQ nie musi rozdzielać kosztu wspólnego budżetu
        między kilka kampanii przed oceną.
      </div>
    );
  }
  return (
    <div className="rounded-md border border-line bg-slate-50 p-3">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-ink">Podział wspólnych budżetów</h3>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            Wspólne budżety Google Ads rozbite po kampaniach. To jest kontekst oceny,
            nie rekomendacja skalowania ani zmiany budżetu.
          </p>
        </div>
        <MetricTile label="Wspólne budżety" value={rows.length} />
      </div>
      <div className="grid gap-3 lg:grid-cols-2">
        {rows.slice(0, 6).map((row) => (
          <article key={row.budget_id} className="rounded-md border border-line bg-white p-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h4 className="text-sm font-semibold text-ink">
                  {row.budget_name ?? "Budżet bez nazwy w odczycie"}
                </h4>
                <p className="mt-1 text-xs text-slate-500">
                  Kampanie korzystające z tego budżetu: {row.campaign_count}
                </p>
              </div>
              <span className="rounded-md border border-line bg-slate-50 px-2 py-1 text-xs text-slate-600">
                wydanie: {adsPercent(row.spend_to_budget_ratio_7d)}
              </span>
            </div>
            <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
              <MetricTile
                label="Budżet dzień"
                value={adsCost(row.budget_amount_micros, currencyCode)}
              />
              <MetricTile
                label="Budżet 7 dni"
                value={adsCost(row.seven_day_budget_micros, currencyCode)}
              />
              <MetricTile
                label="Koszt 7 dni"
                value={adsCost(row.total_cost_micros_7d, currencyCode)}
              />
            </div>
            <div className="mt-3 grid gap-2">
              {row.campaign_shares.slice(0, 8).map((share) => (
                <div
                  key={`${row.budget_id}-${share.campaign_id ?? share.campaign_name}`}
                  className="rounded-md border border-line bg-slate-50 p-2 text-xs"
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <div className="font-semibold text-ink">{share.campaign_name}</div>
                      <LabelChipRow
                        className="mt-1"
                        chips={[
                          { label: "Kanał", value: share.advertising_channel_type_label },
                          { label: "Status", value: share.campaign_status_label }
                        ]}
                      />
                    </div>
                    <div className="text-right text-slate-700">
                      <div>{adsCost(share.cost_micros_7d, currencyCode)}</div>
                      <div className="text-slate-500">
                        udział: {adsPercent(share.spend_share_7d)}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-3 grid gap-1 text-xs text-slate-600">
              <LinkedTraceLine
                label="Dowody"
                values={row.evidence_ids.slice(0, 3)}
                kind="evidence"
              />
              <TraceLine
                label="Nie wolno twierdzić"
                values={[row.blocked_claim_summary_label]}
              />
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

export function AdsRecommendationRowsPanel({
  rows,
  currencyCode
}: {
  rows: AdsRecommendationRow[];
  currencyCode?: string;
}) {
  if (rows.length === 0) {
    return (
      <BlockerNotice message="Brak aktywnych rekomendacji Google Ads w ostatnim odczycie tylko do analizy albo brak kontraktu rekomendacji. WILQ nie przyjmuje rekomendacji bez ręcznej oceny." />
    );
  }
  return (
    <div className="rounded-md border border-line bg-slate-50 p-3">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-ink">Rekomendacje Google Ads</h3>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            Lista typów rekomendacji do sprawdzenia. Zapis zmian pozostaje
            zablokowany do czasu sprawdzenia w WILQ i audytu.
          </p>
        </div>
        <MetricTile label="Do oceny" value={rows.length} />
      </div>
      <div className="grid gap-2 md:grid-cols-2">
        {rows.slice(0, 6).map((row) => (
          <article
            key={`${row.recommendation_id ?? row.recommendation_type}-${row.campaign_id ?? "account"}`}
            className="rounded-md border border-line bg-white p-3"
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <div className="text-sm font-semibold text-ink">
                  {row.recommendation_type_label}
                </div>
                <div className="mt-1 text-xs leading-5 text-slate-600">
                  Zakres: {row.campaign_count ?? 0} kampanii. Pełne powiązania
                  są dostępne w danych akcji.
                </div>
              </div>
              <LabelChipRow
                chips={[
                  { label: "Priorytet", value: row.review_priority },
                  { label: "Ocena WILQ", value: row.review_score }
                ]}
              />
            </div>
            <div className="mt-1 text-xs leading-5 text-slate-600">
              {row.review_reason}
            </div>
            {row.impact_available ? (
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs sm:grid-cols-3">
                <MetricTile label="Klik. delta" value={adsSignedNumber(row.delta_clicks)} />
                <MetricTile
                  label="Wyśw. delta"
                  value={adsSignedNumber(row.delta_impressions)}
                />
                <MetricTile
                  label="Koszt delta"
                  value={adsSignedCost(row.delta_cost_micros, currencyCode)}
                />
                <MetricTile
                  label="Koszt bazowy"
                  value={adsCost(row.base_cost_micros, currencyCode)}
                />
                <MetricTile
                  label="Koszt po"
                  value={adsCost(row.potential_cost_micros, currencyCode)}
                />
                <MetricTile
                  label="Konw. delta"
                  value={adsSignedNumber(row.delta_conversions)}
                />
              </div>
            ) : (
              <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-800">
                Google Ads nie zwrócił metryk wpływu dla tego typu rekomendacji.
              </div>
            )}
            <TraceLine
              label="Ocena człowieka"
              values={[row.human_review_gate_summary_label]}
              empty="WILQ nie ma oceny człowieka; nie wykonuj zmiany bez review."
            />
            <TraceLine
              label="Nie wolno twierdzić"
              values={[row.blocked_claim_summary_label]}
            />
            <LinkedTraceLine
              label="Dowody"
              values={row.evidence_ids.slice(0, 2)}
              kind="evidence"
            />
            {row.preview_card ? (
              <div className="mt-3">
                <ActionPreviewCard card={row.preview_card} />
              </div>
            ) : null}
          </article>
        ))}
      </div>
    </div>
  );
}

export function AdsImpressionShareRowsTable({
  rows,
  emptyStateMessage
}: {
  rows: AdsImpressionShareRow[];
  emptyStateMessage?: string;
}) {
  if (rows.length === 0) {
    return (
      <BlockerNotice
        message={
          emptyStateMessage ||
          "Brak wierszy udziału w wyświetleniach. Odśwież dane Google Ads z metrykami udziału w wyświetleniach, żeby ocenić utraconą ekspozycję."
        }
      />
    );
  }
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-line bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
          <tr>
            <th className="py-2 pl-3 pr-4 font-semibold">Kampania</th>
            <th className="py-2 pr-4 font-semibold">Udział w wyświetleniach</th>
            <th className="py-2 pr-4 font-semibold">Utrata przez budżet</th>
            <th className="py-2 pr-4 font-semibold">Utrata przez ranking</th>
            <th className="py-2 pr-3 font-semibold">Blokady</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.slice(0, 12).map((row) => (
            <tr key={`${row.campaign_id ?? "unknown"}-${row.campaign_name}-impression-share`}>
              <td className="py-2 pl-3 pr-4 font-medium text-ink">{row.campaign_name}</td>
              <td className="py-2 pr-4 text-slate-700">
                {adsPercent(row.search_impression_share)}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {adsPercent(row.search_budget_lost_impression_share)}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {adsPercent(row.search_rank_lost_impression_share)}
              </td>
              <td className="py-2 pr-3 text-xs text-slate-600">
                {row.blocked_claim_summary_label}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function AdsChangeHistoryRowsTable({ rows }: { rows: AdsChangeHistoryRow[] }) {
  if (rows.length === 0) {
    return (
      <BlockerNotice message="Brak wierszy historii zmian. WILQ nie może łączyć skuteczności ze zmianami kampanii bez odczytu historii zmian." />
    );
  }
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-line bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
          <tr>
            <th className="py-2 pl-3 pr-4 font-semibold">Data zmiany</th>
            <th className="py-2 pr-4 font-semibold">Zasób</th>
            <th className="py-2 pr-4 font-semibold">Operacja</th>
            <th className="py-2 pr-4 font-semibold">Klient</th>
            <th className="py-2 pr-4 font-semibold">Kampania</th>
            <th className="py-2 pr-3 font-semibold">Pola</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.slice(0, 12).map((row) => (
            <tr key={`${row.change_event_id ?? "unknown"}-${row.change_date_time ?? "no-date"}`}>
              <td className="py-2 pl-3 pr-4 font-medium text-ink">
                {row.change_date_time ?? adsMissingDateLabel}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.change_resource_label || "zasób zmiany do sprawdzenia"}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.resource_change_operation_label || "operacja do potwierdzenia"}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.client_type_label || "źródło zmiany do potwierdzenia"}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.campaign_label || adsMissingCampaignLabel}
              </td>
              <td className="py-2 pr-3 text-xs text-slate-600">
                {row.changed_field_summary_label}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
