import { AdsDiagnosticsResponse } from "../lib/api";
import {
  adsCost,
  adsNumber,
  adsPercent,
  adsSignedCost,
  adsSignedNumber,
  adsTargetStatusClass
} from "../lib/adsFormatting";
import {
  adsMissingCampaignStatusLabel,
  adsMissingChannelLabel
} from "../lib/adsLabels";
import { BlockerNotice, LabelChipRow, MetricTile } from "./OperatorPrimitives";
import { TraceLine } from "./TraceLine";

type AdsCampaignMetricRow = AdsDiagnosticsResponse["campaign_read_contract"]["campaign_rows"][number];
type AdsDerivedKpiRow = AdsDiagnosticsResponse["derived_kpi_read_contract"]["kpi_rows"][number];
type AdsCampaignTriageRow =
  AdsDiagnosticsResponse["campaign_triage_read_contract"]["triage_rows"][number];

export function AdsCampaignRowsTable({
  rows,
  currencyCode
}: {
  rows: AdsCampaignMetricRow[];
  currencyCode?: string;
}) {
  if (rows.length === 0) {
    return (
      <BlockerNotice message="Brak szczegółowych wierszy kampanii. WILQ nie może analizować kampanii bez odczytu Google Ads." />
    );
  }
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-line bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
          <tr>
            <th className="py-2 pl-3 pr-4 font-semibold">Kampania</th>
            <th className="py-2 pr-4 font-semibold">Ocena</th>
            <th className="py-2 pr-4 font-semibold">Kliknięcia</th>
            <th className="py-2 pr-4 font-semibold">Wyświetlenia</th>
            <th className="py-2 pr-4 font-semibold">Koszt</th>
            <th className="py-2 pr-4 font-semibold">Konwersje</th>
            <th className="py-2 pr-4 font-semibold">Wartość konwersji</th>
            <th className="py-2 pr-4 font-semibold">Powód</th>
            <th className="py-2 pr-3 font-semibold">Dowody</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.slice(0, 12).map((row) => (
            <tr key={`${row.campaign_id ?? "unknown"}-${row.campaign_name}`}>
              <td className="py-2 pl-3 pr-4 font-medium text-ink">{row.campaign_name}</td>
              <td className="py-2 pr-4 text-xs">
                <LabelChipRow
                  chips={[
                    { label: "Priorytet", value: row.review_priority },
                    { label: "Ocena WILQ", value: row.review_score }
                  ]}
                />
                <div className="mt-1 text-slate-500">{row.human_review_gate_summary_label}</div>
                {row.target_status !== "no_target" ? (
                  <div className="mt-1 text-slate-500">{row.target_status_label}</div>
                ) : null}
              </td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.clicks)}</td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.impressions)}</td>
              <td className="py-2 pr-4 text-slate-700">
                {adsCost(row.cost_micros, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.conversions)}</td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.conversion_value)}</td>
              <td className="max-w-md py-2 pr-4 text-xs leading-5 text-slate-600">
                {row.review_reason}
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

export function AdsCampaignTriageRowsPanel({
  rows,
  contract,
  currencyCode,
  compact = false
}: {
  rows: AdsCampaignTriageRow[];
  contract?: AdsDiagnosticsResponse["campaign_triage_read_contract"];
  currencyCode?: string;
  compact?: boolean;
}) {
  if (rows.length === 0) {
    return (
      <BlockerNotice message="Brak kolejki oceny kampanii. WILQ potrzebuje aktywności kampanii, wskaźników, budżetu i zasad oceny, żeby ustalić kolejność sprawdzania." />
    );
  }

  const visibleRows = compact ? rows.slice(0, 3) : rows.slice(0, 8);

  return (
    <div className="rounded-md border border-line bg-slate-50 p-3">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-ink">Kolejność oceny kampanii</h3>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            {contract?.summary ??
              "Ranking kampanii do ręcznej oceny. To nie jest ocena zmarnowanego budżetu, kosztu pozyskania celu, zwrotu z reklam ani opłacalności."}
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Kampanie" value={rows.length} />
          <MetricTile
            label="Pilne"
            value={rows.filter((row) => row.review_priority === "pilne").length}
          />
          <MetricTile
            label="Wysokie"
            value={rows.filter((row) => row.review_priority === "wysokie").length}
          />
        </div>
      </div>

      <div className="grid gap-2">
        {visibleRows.map((row) => (
          <article
            key={`${row.campaign_id ?? row.campaign_name}-triage`}
            className="rounded-md border border-line bg-white p-3"
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h4 className="text-sm font-semibold text-ink">{row.campaign_name}</h4>
                <LabelChipRow
                  className="mt-1"
                  chips={[
                    { label: "Kanał", value: row.advertising_channel_type_label ?? adsMissingChannelLabel },
                    { label: "Status", value: row.campaign_status_label ?? adsMissingCampaignStatusLabel },
                    { label: "Cel", value: row.target_status_label }
                  ]}
                />
              </div>
              <LabelChipRow
                chips={[
                  { label: "Priorytet", value: row.review_priority },
                  { label: "Ocena WILQ", value: row.review_score }
                ]}
              />
            </div>

            <div className="mt-3 grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-5">
              <MetricTile label="Kliknięcia" value={adsNumber(row.clicks)} />
              <MetricTile label="Koszt" value={adsCost(row.cost_micros, currencyCode)} />
              <MetricTile label="Konwersje" value={adsNumber(row.conversions)} />
              <MetricTile label="Zwrot z reklam" value={adsNumber(row.roas)} />
              <MetricTile
                label="Wydanie 7d"
                value={adsPercent(row.spend_to_budget_ratio_7d)}
              />
            </div>

            <p className="mt-3 text-xs leading-5 text-slate-700">
              {row.review_reason}
            </p>
            <p className="mt-2 text-xs font-medium text-ink">
              {row.next_step}
            </p>
            <div className="mt-3 grid gap-1 text-xs text-slate-600 md:grid-cols-2">
              <TraceLine
                label="Wymagana ocena"
                values={[row.human_review_gate_summary_label]}
                empty="WILQ nie podał wymaganej oceny; zostaje ręczny review."
              />
              <TraceLine
                label="Braki"
                values={[row.missing_read_contract_summary_label]}
                empty="dane kompletne"
              />
              <TraceLine
                label="Dowody"
                values={[row.evidence_summary_label]}
                empty="WILQ nie podał dowodów źródłowych; nie traktuj tego jako rekomendacji Ads."
              />
              <TraceLine
                label="Akcje do sprawdzenia"
                values={[row.action_summary_label]}
                empty="WILQ nie podał akcji do sprawdzenia; zostaje ręczny przegląd Ads."
              />
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

export function AdsDerivedKpiRowsTable({
  rows,
  currencyCode
}: {
  rows: AdsDerivedKpiRow[];
  currencyCode?: string;
}) {
  if (rows.length === 0) {
    return (
      <BlockerNotice message="Brak wyliczalnych wskaźników kampanii. WILQ potrzebuje kosztu, kliknięć, konwersji i wartości konwersji w danych kampanii." />
    );
  }
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-line bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
          <tr>
            <th className="py-2 pl-3 pr-4 font-semibold">Kampania</th>
            <th className="py-2 pr-4 font-semibold">CTR</th>
            <th className="py-2 pr-4 font-semibold">Śr. CPC</th>
            <th className="py-2 pr-4 font-semibold">Conv. rate</th>
            <th className="py-2 pr-4 font-semibold">Koszt pozyskania celu</th>
            <th className="py-2 pr-4 font-semibold">Docelowy koszt pozyskania celu</th>
            <th className="py-2 pr-4 font-semibold">Różnica kosztu pozyskania celu</th>
            <th className="py-2 pr-4 font-semibold">zwrot z reklam</th>
            <th className="py-2 pr-4 font-semibold">Docelowy zwrot z reklam</th>
            <th className="py-2 pr-4 font-semibold">Różnica zwrot z reklam</th>
            <th className="py-2 pr-4 font-semibold">Ocena</th>
            <th className="py-2 pr-3 font-semibold">Blokady</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.slice(0, 12).map((row) => (
            <tr key={`${row.campaign_id ?? "unknown"}-${row.campaign_name}-kpi`}>
              <td className="py-2 pl-3 pr-4 font-medium text-ink">{row.campaign_name}</td>
              <td className="py-2 pr-4 text-slate-700">{adsPercent(row.ctr)}</td>
              <td className="py-2 pr-4 text-slate-700">
                {adsCost(row.average_cpc_micros, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">{adsPercent(row.conversion_rate)}</td>
              <td className="py-2 pr-4 text-slate-700">
                {adsCost(row.cost_per_conversion_micros, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {adsCost(row.target_cpa_micros, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {adsSignedCost(row.cpa_vs_target_micros, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.roas)}</td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.target_roas)}</td>
              <td className="py-2 pr-4 text-slate-700">{adsSignedNumber(row.roas_vs_target)}</td>
              <td className="py-2 pr-4 text-xs">
                <span className={adsTargetStatusClass(row.target_status)}>
                  {row.target_status_label}
                </span>
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
