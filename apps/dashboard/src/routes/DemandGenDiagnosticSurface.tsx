import { useQuery } from "@tanstack/react-query";
import { ShieldAlert } from "lucide-react";

import { getDemandGenDiagnostics } from "../lib/api";
import { BlockerNotice, LoadingBand, MetricTile } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import { LinkedTraceLine, TraceLine } from "../components/TraceLine";

export function DemandGenDiagnosticSurface() {
  const diagnostics = useQuery({
    queryKey: ["demand-gen-diagnostics"],
    queryFn: getDemandGenDiagnostics
  });

  if (diagnostics.isLoading) return <LoadingBand />;
  if (diagnostics.error || !diagnostics.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać /api/demand-gen/diagnostics. Demand Gen route nie może udawać gotowości migracji ani jakości kreacji bez WILQ API." />
      </main>
    );
  }

  const data = diagnostics.data;
  const channelEntries = Object.entries(data.campaign_channel_counts);
  const demandGenRowCount = data.demand_gen_campaign_rows.length;
  const landingQualityRows = data.demand_gen_landing_quality_rows;
  const migrationConstraintRows = data.demand_gen_migration_constraint_rows;
  const metricTileEntries = Object.entries(data.metric_tiles);
  const demandGenPreview = data.payload_preview[0] as Record<string, unknown> | undefined;
  const previewMissingContracts = Array.isArray(demandGenPreview?.missing_read_contracts)
    ? demandGenPreview.missing_read_contracts.filter(
        (value): value is string => typeof value === "string"
      )
    : [];
  const previewValidation = Array.isArray(demandGenPreview?.required_validation)
    ? demandGenPreview.required_validation.filter(
        (value): value is string => typeof value === "string"
      )
    : [];

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Demand Gen</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Dedykowany widok Demand Gen z WILQ API. Oddziela kontekst kampanii
            Ads i GA4 od prawdziwych kontraktów Demand Gen: assetów, kreacji,
            jakości landingów per kampania, ograniczeń migracji i ActionObject.
          </p>
        </div>
        {metricTileEntries.length > 0 ? (
          <div className="grid grid-cols-2 gap-2 text-center text-xs sm:grid-cols-6">
            {metricTileEntries.slice(0, 6).map(([label, value]) => (
              <MetricTile key={label} label={label} value={value} />
            ))}
          </div>
        ) : null}
      </div>

      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              {data.title}
            </h2>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
              {data.summary}
            </p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <StatusBadge value={data.status === "blocked" ? "zablokowane" : "gotowe"} />
            <StatusBadge value={data.risk} />
          </div>
        </div>
      </section>

      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
              Operator Demand Gen
            </div>
            <h2 className="mt-1 text-base font-semibold tracking-normal">
              Co marketer ma wiedzieć przed planem Demand Gen
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              WILQ może zwalidować review-only ActionObject i użyć Ads/GA4
              jako kontekstu, ale nie może polecić launchu, migracji ani
              jakości kreacji bez osobnych rekordów Demand Gen.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-2 text-center text-xs">
            {channelEntries.slice(0, 4).map(([channel, count]) => (
              <MetricTile key={channel} label={demandGenChannelLabel(channel)} value={count} />
            ))}
          </div>
        </div>

        {demandGenRowCount > 0 ? (
          <div className="grid gap-3">
            {data.demand_gen_campaign_rows.slice(0, 4).map((row) => (
              <article key={row.campaign_id} className="rounded-md border border-line bg-slate-50 p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <h3 className="text-sm font-semibold text-ink">{row.campaign_name}</h3>
                    <p className="mt-1 text-xs text-slate-500">
                      {row.advertising_channel_type} / {row.campaign_status}
                    </p>
                  </div>
                  <StatusBadge value="do review" />
                </div>
                <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
                  <MetricTile label="Kliknięcia" value={row.clicks ?? "brak"} />
                  <MetricTile label="Wyświetlenia" value={row.impressions ?? "brak"} />
                  <MetricTile label="Koszt" value={adsCost(row.cost_micros)} />
                  <MetricTile label="Konwersje" value={row.conversions ?? "brak"} />
                </div>
                <div className="mt-3 text-xs text-slate-600">
                  <TraceLine
                    label="Dowody"
                    values={[formatDemandGenIdCount(row.evidence_ids.length, "ID", "ID")]}
                  />
                </div>
              </article>
            ))}
          </div>
        ) : (
          <BlockerNotice message="W bieżącym evidence Ads nie ma kampanii Demand Gen ani Discovery. WILQ może pokazać kanały konta, ale nie stworzy rekomendacji Demand Gen z kampanii, których nie widzi w danych." />
        )}

        {demandGenPreview ? (
          <article className="mt-4 rounded-md border border-blue-200 bg-blue-50 p-3">
            <div className="text-xs font-semibold uppercase tracking-normal text-blue-700">
              Review-only ActionObject
            </div>
            <h3 className="mt-1 text-sm font-semibold text-ink">
              Podgląd walidacji gotowości Demand Gen
            </h3>
            <p className="mt-2 text-sm leading-6 text-slate-700">
              Ten payload sprawdza kanały i braki kontraktów. Nie tworzy kampanii,
              nie migruje budżetu i nie odblokowuje apply.
            </p>
            <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
              <MetricTile
                label="Kampanie"
                value={String(demandGenPreview.campaign_rows_evaluated ?? "brak")}
              />
              <MetricTile
                label="DG rows"
                value={String(demandGenPreview.demand_gen_campaign_row_count ?? "0")}
              />
              <MetricTile
                label="Reklamy"
                value={String(demandGenPreview.demand_gen_ad_group_ad_row_count ?? "0")}
              />
              <MetricTile
                label="Assety"
                value={String(demandGenPreview.demand_gen_creative_asset_row_count ?? "0")}
              />
              <MetricTile
                label="Landingi"
                value={String(demandGenPreview.demand_gen_landing_quality_row_count ?? "0")}
              />
              <MetricTile
                label="Migracje"
                value={String(
                  demandGenPreview.demand_gen_migration_constraint_row_count ?? "0"
                )}
              />
              <MetricTile label="Braki" value={previewMissingContracts.length} />
              <MetricTile
                label="Apply"
                value={demandGenPreview.apply_allowed === true ? "możliwy" : "zablokowany"}
              />
            </div>
            <div className="mt-3 grid gap-2 text-xs text-slate-600">
              <TraceLine
                label="Braki kontraktów"
                values={previewMissingContracts.map(demandGenContractLabel)}
              />
              <TraceLine
                label="Walidacja"
                values={previewValidation.map(demandGenContractLabel)}
              />
              <TraceLine
                label="Akcje"
                values={[
                  formatDemandGenIdCount(
                    data.action_ids.length,
                    "akcja",
                    "akcji"
                  )
                ]}
              />
            </div>
          </article>
        ) : null}

        {landingQualityRows.length > 0 ? (
          <div className="mt-4 grid gap-3 lg:grid-cols-2">
            {landingQualityRows.slice(0, 4).map((row) => (
              <article
                key={`${row.campaign_name}-${row.landing_page}-${row.source_medium ?? "source"}`}
                className="rounded-md border border-line bg-white p-3"
              >
                <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
                  Odczyt jakości landingów
                </div>
                <h3 className="mt-1 text-sm font-semibold text-ink">{row.campaign_name}</h3>
                <p className="mt-1 text-xs text-slate-500">
                  {row.landing_page} / {row.source_medium ?? "brak źródła"}
                </p>
                <div className="mt-3 grid grid-cols-3 gap-2">
                  <MetricTile label="Aktywni" value={row.active_users ?? "brak"} />
                  <MetricTile label="Sesje" value={row.sessions ?? "brak"} />
                  <MetricTile label="Engagement" value={adsPercent(row.engagement_rate)} />
                </div>
                <div className="mt-3 text-xs text-slate-600">
                  <TraceLine
                    label="Dowody"
                    values={[formatDemandGenIdCount(row.evidence_ids.length, "ID", "ID")]}
                  />
                </div>
              </article>
            ))}
          </div>
        ) : null}

        {migrationConstraintRows.length > 0 ? (
          <div className="mt-4 grid gap-3 lg:grid-cols-2">
            {migrationConstraintRows.slice(0, 4).map((row) => (
              <article
                key={`${row.campaign_id ?? row.campaign_name}-${row.reason}`}
                className="rounded-md border border-line bg-white p-3"
              >
                <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
                  Odczyt ograniczeń migracji
                </div>
                <h3 className="mt-1 text-sm font-semibold text-ink">{row.campaign_name}</h3>
                <p className="mt-1 text-xs text-slate-500">
                  {row.advertising_channel_type ?? "brak kanału"} /{" "}
                  {row.campaign_status ?? "brak statusu"}
                </p>
                <div className="mt-3 grid grid-cols-2 gap-2">
                  <MetricTile
                    label="Migracja"
                    value={row.migration_candidate ? "kandydat" : "nie dotyczy"}
                  />
                  <MetricTile label="Powód" value={demandGenContractLabel(row.reason)} />
                </div>
                <div className="mt-3 text-xs text-slate-600">
                  <TraceLine
                    label="Dowody"
                    values={[formatDemandGenIdCount(row.evidence_ids.length, "ID", "ID")]}
                  />
                </div>
              </article>
            ))}
          </div>
        ) : null}
      </section>

      <section className="rounded-md border border-line bg-white p-4">
        <div className="mb-3 flex items-start gap-3">
          <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
            <ShieldAlert aria-hidden="true" size={18} />
          </div>
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Dowody i ograniczenia Demand Gen
            </h2>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
              To jest kontrakt gotowości, nie kreator kampanii. Brakujące
              kontrakty są jawne i muszą powstać w API przed rekomendacjami.
            </p>
          </div>
        </div>
        <div className="grid gap-2 text-xs text-slate-600">
          <TraceLine
            label="Dostępne kontrakty"
            values={data.available_read_contracts.map(demandGenContractLabel)}
          />
          <TraceLine
            label="Brakujące kontrakty"
            values={data.missing_read_contracts.map(demandGenContractLabel)}
          />
          <TraceLine label="Źródła" values={data.source_connectors} />
          <LinkedTraceLine label="Dowody" values={data.evidence_ids.slice(0, 8)} kind="evidence" />
          <LinkedTraceLine label="Akcje" values={data.action_ids} kind="actions" empty="brak" />
          <TraceLine
            label="Bramki operatora"
            values={data.operator_review_gates.map(demandGenContractLabel)}
          />
          <TraceLine
            label="Nie wolno twierdzić"
            values={demandGenBlockedClaimLabels(data.blocked_claims)}
          />
        </div>
        <p className="mt-4 text-sm font-medium text-ink">{data.next_step}</p>
      </section>
    </main>
  );
}

function demandGenChannelLabel(channel: string) {
  const labels: Record<string, string> = {
    DEMAND_GEN: "Demand Gen",
    DISCOVERY: "Discovery",
    PERFORMANCE_MAX: "PMax",
    SEARCH: "Search",
    UNKNOWN: "unknown"
  };
  return labels[channel] ?? channel;
}

function demandGenContractLabel(contract: string) {
  const labels: Record<string, string> = {
    demand_gen_action_object: "Demand Gen ActionObject",
    demand_gen_ad_group_ad_rows: "wiersze reklam Demand Gen",
    demand_gen_campaign_rows: "wiersze kampanii Demand Gen/Discovery",
    demand_gen_creative_asset_rows: "wiersze assetów kreacji",
    demand_gen_landing_quality_by_campaign: "jakość landingów per kampania",
    demand_gen_migration_constraints: "ograniczenia migracji",
    demand_gen_readiness_review_action_object: "review-only ActionObject",
    demand_gen_specific_evidence_required: "wymagane konkretne evidence Demand Gen",
    already_demand_gen_review_only: "już Demand Gen, tylko review",
    discovery_to_demand_gen_requires_human_review: "Discovery wymaga ręcznego review",
    ga4_landing_source_campaign_quality: "GA4 landing/source/campaign quality",
    google_ads_budget_context: "kontekst budżetowy Google Ads",
    google_ads_campaign_activity: "aktywność kampanii Google Ads",
    google_ads_impression_share_context: "udział w wyświetleniach Google Ads",
    human_confirm_before_apply: "potwierdzenie człowieka przed apply",
    human_strategy_review: "review strategii przez człowieka",
    review_ads_campaign_channel_context: "review kanałów kampanii Ads",
    review_demand_gen_missing_contracts: "review brakujących kontraktów Demand Gen",
    review_ga4_landing_source_campaign_context: "review GA4 landing/source/campaign"
  };
  return labels[contract] ?? contract;
}

function demandGenBlockedClaimLabels(claims: string[]) {
  const labels: Record<string, string> = {
    "asset performance verdict": "werdykt performance assetów",
    "campaign apply": "wdrożenie kampanii",
    "creative quality verdict": "werdykt jakości kreacji",
    "Demand Gen launch recommendation": "rekomendacja launchu Demand Gen",
    "Demand Gen migration ready": "gotowość migracji Demand Gen",
    "performance uplift": "wzrost performance"
  };
  return uniqueValues(claims.map((claim) => labels[claim] ?? claim));
}

function formatDemandGenIdCount(count: number, singular: string, plural: string) {
  if (count === 1) return `1 ${singular}`;
  return `${count} ${plural}`;
}

function adsCost(value: number | null | undefined, currencyCode?: string) {
  if (value === null || value === undefined) return "brak";
  const accountUnits = value / 1_000_000;
  if (currencyCode) {
    return new Intl.NumberFormat("pl-PL", {
      currency: currencyCode,
      maximumFractionDigits: 2,
      style: "currency"
    }).format(accountUnits);
  }
  return `${new Intl.NumberFormat("pl-PL", { maximumFractionDigits: 2 }).format(
    accountUnits
  )} jedn. konta`;
}

function adsPercent(value: number | null | undefined) {
  if (value === null || value === undefined) return "brak";
  return `${new Intl.NumberFormat("pl-PL", { maximumFractionDigits: 2 }).format(
    value * 100
  )}%`;
}

function uniqueValues(values: string[]) {
  return Array.from(new Set(values));
}
