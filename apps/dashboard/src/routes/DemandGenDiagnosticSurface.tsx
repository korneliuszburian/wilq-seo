import { useQuery } from "@tanstack/react-query";
import { ShieldAlert } from "lucide-react";

import { getDemandGenDiagnostics } from "../lib/api";
import { BlockerNotice, LoadingBand, MetricTile } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import { TraceLine } from "../components/TraceLine";

export function DemandGenDiagnosticSurface() {
  const diagnostics = useQuery({
    queryKey: ["demand-gen-diagnostics"],
    queryFn: getDemandGenDiagnostics
  });

  if (diagnostics.isLoading) return <LoadingBand />;
  if (diagnostics.error || !diagnostics.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać danych Demand Gen. Ten widok nie może udawać gotowości przejścia kampanii ani jakości kreacji bez WILQ." />
      </main>
    );
  }

  const data = diagnostics.data;
  const channelEntries = Object.entries(data.campaign_channel_counts);
  const demandGenRowCount = data.demand_gen_campaign_rows.length;
  const landingQualityRows = data.demand_gen_landing_quality_rows;
  const transitionConstraintRows = data.demand_gen_transition_constraint_rows;
  const metricTileEntries = Object.entries(data.metric_tiles);
  const demandGenPreview = data.payload_preview[0] as Record<string, unknown> | undefined;
  const previewMissingContractLabels = stringArray(
    demandGenPreview?.missing_read_contract_labels
  );
  const previewRequiredValidationLabels = stringArray(
    demandGenPreview?.required_validation_labels
  );
  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Demand Gen</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Dedykowany widok Demand Gen z WILQ. Oddziela kontekst kampanii
            Ads i GA4 od prawdziwych danych Demand Gen: kreacji, jakości
            stron wejścia według kampanii, ograniczeń przejścia i akcji do sprawdzenia.
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
              WILQ może sprawdzić akcję do sprawdzenia i użyć Ads/GA4
              jako kontekstu, ale nie może polecić uruchomienia, przejścia kampanii ani
              jakości kreacji bez osobnych rekordów Demand Gen.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-2 text-center text-xs">
            {channelEntries.slice(0, 4).map(([channel, count]) => (
              <MetricTile
                key={channel}
                label={data.campaign_channel_labels[channel] ?? channel}
                value={count}
              />
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
                  <StatusBadge value="do sprawdzenia" />
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
                    values={[formatDemandGenEvidenceCount(row.evidence_ids.length)]}
                  />
                </div>
              </article>
            ))}
          </div>
        ) : (
          <BlockerNotice message="W bieżących dowodach Ads nie ma kampanii Demand Gen ani Discovery. WILQ może pokazać kanały konta, ale nie stworzy rekomendacji Demand Gen z kampanii, których nie widzi w danych." />
        )}

        {demandGenPreview ? (
          <article className="mt-4 rounded-md border border-blue-200 bg-blue-50 p-3">
            <div className="text-xs font-semibold uppercase tracking-normal text-blue-700">
              Akcja do sprawdzenia
            </div>
            <h3 className="mt-1 text-sm font-semibold text-ink">
              Podgląd sprawdzenia gotowości Demand Gen
            </h3>
            <p className="mt-2 text-sm leading-6 text-slate-700">
              Ten podgląd sprawdza kanały i brakujące dane. Nie tworzy kampanii,
              nie migruje budżetu i nie odblokowuje zapisu zmian.
            </p>
            <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
              <MetricTile
                label="Kampanie"
                value={String(demandGenPreview.campaign_rows_evaluated ?? "brak")}
              />
              <MetricTile
                label="Kampanie Demand Gen"
                value={String(demandGenPreview.demand_gen_campaign_row_count ?? "0")}
              />
              <MetricTile
                label="Reklamy"
                value={String(demandGenPreview.demand_gen_ad_group_ad_row_count ?? "0")}
              />
              <MetricTile
                label="Kreacje"
                value={String(demandGenPreview.demand_gen_creative_asset_row_count ?? "0")}
              />
              <MetricTile
                label="Strony wejścia"
                value={String(demandGenPreview.demand_gen_landing_quality_row_count ?? "0")}
              />
              <MetricTile
                label="Przejścia"
                value={String(
                  demandGenPreview.demand_gen_transition_constraint_row_count ?? "0"
                )}
              />
              <MetricTile label="Braki" value={previewMissingContractLabels.length} />
              <MetricTile
                label="Zapis zmian"
                value={demandGenPreview.apply_allowed === true ? "możliwy" : "zablokowany"}
              />
            </div>
            <div className="mt-3 grid gap-2 text-xs text-slate-600">
              <TraceLine
                label="Brakujące dane"
                values={previewMissingContractLabels}
              />
              <TraceLine
                label="Sprawdzenie w WILQ"
                values={previewRequiredValidationLabels}
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
                  Odczyt jakości stron wejścia
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
                    values={[formatDemandGenEvidenceCount(row.evidence_ids.length)]}
                  />
                </div>
              </article>
            ))}
          </div>
        ) : null}

        {transitionConstraintRows.length > 0 ? (
          <div className="mt-4 grid gap-3 lg:grid-cols-2">
            {transitionConstraintRows.slice(0, 4).map((row) => (
              <article
                key={`${row.campaign_id ?? row.campaign_name}-${row.reason}`}
                className="rounded-md border border-line bg-white p-3"
              >
                <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
                  Odczyt ograniczeń przejścia
                </div>
                <h3 className="mt-1 text-sm font-semibold text-ink">{row.campaign_name}</h3>
                <p className="mt-1 text-xs text-slate-500">
                  {row.advertising_channel_type ?? "brak kanału"} /{" "}
                  {row.campaign_status ?? "brak statusu"}
                </p>
                <div className="mt-3 grid grid-cols-2 gap-2">
                  <MetricTile
                    label="Przejście"
                    value={row.transition_candidate ? "do sprawdzenia" : "nie dotyczy"}
                  />
                  <MetricTile label="Powód" value={row.reason_label ?? row.reason} />
                </div>
                <div className="mt-3 text-xs text-slate-600">
                  <TraceLine
                    label="Dowody"
                    values={[formatDemandGenEvidenceCount(row.evidence_ids.length)]}
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
              To jest sprawdzenie gotowości, nie kreator kampanii. Brakujące
              dane są jawne i muszą powstać w API przed rekomendacjami.
            </p>
          </div>
        </div>
        <div className="grid gap-2 text-xs text-slate-600">
          <TraceLine
            label="Dostępne dane"
            values={data.available_read_contract_labels}
          />
          <TraceLine
            label="Brakujące dane"
            values={data.missing_read_contract_labels}
          />
          <TraceLine label="Źródła danych" values={data.source_connector_labels} />
          <TraceLine
            label="Dowody"
            values={[data.evidence_summary_label]}
          />
          <TraceLine
            label="Akcje"
            values={[formatDemandGenIdCount(data.action_ids.length, "akcja", "akcji")]}
          />
          <TraceLine
            label="Bramki operatora"
            values={data.operator_review_gate_labels}
          />
          <TraceLine
            label="Nie wolno twierdzić"
            values={data.blocked_claims}
          />
        </div>
        <p className="mt-4 text-sm font-medium text-ink">{data.next_step}</p>
      </section>
    </main>
  );
}

function formatDemandGenIdCount(count: number, singular: string, plural: string) {
  if (count === 1) return `1 ${singular}`;
  return `${count} ${plural}`;
}

function formatDemandGenEvidenceCount(count: number) {
  if (count === 0) return "brak dowodów źródłowych";
  if (count === 1) return "1 dowód źródłowy";
  if (count >= 2 && count <= 4) return `${count} dowody źródłowe`;
  return `${count} dowodów źródłowych`;
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

function stringArray(value: unknown) {
  return Array.isArray(value)
    ? uniqueValues(value.filter((item): item is string => typeof item === "string"))
    : [];
}
