import { useQuery } from "@tanstack/react-query";

import {
  type ActionPreviewCardViewModel,
  getDemandGenDiagnostics,
  type DemandGenReadinessContract
} from "../lib/api";
import {
  DiagnosticPage
} from "../components/DiagnosticSurfaceShell";
import { BlockerNotice, MetricTile } from "../components/OperatorPrimitives";
import { SafetyGatePanel } from "../components/SafetyGatePanel";
import { StatusBadge } from "../components/StatusBadge";
import { TraceLine } from "../components/TraceLine";

export function DemandGenDiagnosticSurface() {
  const diagnostics = useQuery({
    queryKey: ["demand-gen-diagnostics"],
    queryFn: getDemandGenDiagnostics
  });

  return (
    <DiagnosticPage
      query={diagnostics}
      title="Demand Gen"
      description="Dedykowany widok Demand Gen z WILQ. Oddziela kontekst kampanii Ads i GA4 od prawdziwych danych Demand Gen: kreacji, jakości stron wejścia według kampanii, kontroli trybu kampanii i akcji do sprawdzenia."
      unavailableMessage="Nie udało się odczytać danych Demand Gen. Ten widok nie może udawać gotowości zmiany trybu kampanii ani jakości kreacji bez WILQ."
      metrics={demandGenMetrics}
    >
      {(data) => <DemandGenDiagnosticBody data={data} />}
    </DiagnosticPage>
  );
}

function demandGenMetrics(data: DemandGenReadinessContract) {
  const metricTileEntries = Object.entries(data.metric_tiles);
  return metricTileEntries.length > 0 ? (
    <div className="grid grid-cols-2 gap-2 text-center text-xs sm:grid-cols-6">
      {metricTileEntries.slice(0, 6).map(([label, value]) => (
        <MetricTile key={label} label={label} value={value} />
      ))}
    </div>
  ) : null;
}

function DemandGenDiagnosticBody({ data }: { data: DemandGenReadinessContract }) {
  const channelEntries = Object.entries(data.campaign_channel_counts);
  const demandGenRowCount = data.demand_gen_campaign_rows.length;
  const landingQualityRows = data.demand_gen_landing_quality_rows;
  const campaignModeReviewRows = data.demand_gen_campaign_mode_review_rows;

  return (
    <>
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
            <StatusBadge value={data.status} label={data.status_label} />
            <StatusBadge value={data.risk} label={data.risk_label} />
          </div>
        </div>
      </section>

      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
              Sprawdzenie Demand Gen
            </div>
            <h2 className="mt-1 text-base font-semibold tracking-normal">
              Co marketer ma wiedzieć przed planem Demand Gen
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              WILQ może sprawdzić akcję do sprawdzenia i użyć Ads/GA4
              jako kontekstu, ale nie może polecić uruchomienia, zmiany trybu kampanii ani
              jakości kreacji bez osobnych rekordów Demand Gen.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-2 text-center text-xs">
            {channelEntries.slice(0, 4).map(([channel, count]) => (
              <MetricTile
                key={channel}
                label={data.campaign_channel_labels[channel] || "kanał kampanii do sprawdzenia"}
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
                      {row.advertising_channel_type_label || "kanał do sprawdzenia"} /{" "}
                      {row.campaign_status_label || "status do sprawdzenia"}
                    </p>
                  </div>
                  <StatusBadge value="needs_validation" label="do sprawdzenia" />
                </div>
                <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
                  <MetricTile label="Kliknięcia" value={row.clicks_label} />
                  <MetricTile label="Wyświetlenia" value={row.impressions_label} />
                  <MetricTile label="Koszt" value={row.cost_label} />
                  <MetricTile label="Konwersje" value={row.conversions_label} />
                </div>
                <div className="mt-3 text-xs text-slate-600">
                  <TraceLine
                    label="Dowody"
                    values={[row.evidence_summary_label]}
                  />
                </div>
              </article>
            ))}
          </div>
        ) : (
          <BlockerNotice message="W bieżących dowodach Ads nie ma kampanii Demand Gen ani Discovery. WILQ może pokazać kanały konta, ale nie stworzy rekomendacji Demand Gen z kampanii, których nie widzi w danych." />
        )}

        {data.preview_cards.length > 0 ? (
          <article className="mt-4 rounded-md border border-blue-200 bg-blue-50 p-3">
            <div className="text-xs font-semibold uppercase tracking-normal text-blue-700">
              Akcja do sprawdzenia
            </div>
            <h3 className="mt-1 text-sm font-semibold text-ink">Podgląd gotowości Demand Gen</h3>
            <p className="mt-2 text-sm leading-6 text-slate-700">
              WILQ pokazuje skondensowany podgląd bezpiecznego następnego kroku. Nie tworzy kampanii,
              nie przenosi budżetu i nie odblokowuje zapisu zmian.
            </p>
            <div className="mt-3 grid gap-3 lg:grid-cols-2">
              {data.preview_cards.map((card) => (
                <DemandGenPreviewCard key={card.id} card={card} />
              ))}
            </div>
            <div className="mt-3 grid gap-2 text-xs text-slate-600">
              <TraceLine
                label="Akcje"
                values={[data.action_summary_label]}
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
                <div className="mt-1 grid gap-1 text-xs text-slate-500">
                  <span>Strona wejścia: {row.landing_page_label}</span>
                  <span>Źródło ruchu: {row.source_medium_label}</span>
                </div>
                <div className="mt-3 grid grid-cols-3 gap-2">
                  <MetricTile label="Aktywni" value={row.active_users_label} />
                  <MetricTile label="Sesje" value={row.sessions_label} />
                  <MetricTile label="Zaangażowanie" value={row.engagement_rate_label} />
                </div>
                <div className="mt-3 text-xs text-slate-600">
                  <TraceLine
                    label="Dowody"
                    values={[row.evidence_summary_label]}
                  />
                </div>
              </article>
            ))}
          </div>
        ) : null}

        {campaignModeReviewRows.length > 0 ? (
          <div className="mt-4 grid gap-3 lg:grid-cols-2">
            {campaignModeReviewRows.slice(0, 4).map((row) => (
              <article
                key={`${row.campaign_id ?? row.campaign_name}-${row.reason}`}
                className="rounded-md border border-line bg-white p-3"
              >
                <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
                  Kontrola trybu kampanii
                </div>
                <h3 className="mt-1 text-sm font-semibold text-ink">{row.campaign_name}</h3>
                <p className="mt-1 text-xs text-slate-500">
                  {row.advertising_channel_type_label || "kanał do sprawdzenia"} /{" "}
                  {row.campaign_status_label || "status do sprawdzenia"}
                </p>
                <div className="mt-3 grid grid-cols-2 gap-2">
                  <MetricTile
                    label="Ocena"
                    value={row.review_status_label}
                  />
                  <MetricTile label="Powód" value={row.reason_label || "powód do sprawdzenia"} />
                </div>
                <div className="mt-3 text-xs text-slate-600">
                  <TraceLine
                    label="Dowody"
                    values={[row.evidence_summary_label]}
                  />
                </div>
              </article>
            ))}
          </div>
        ) : null}
      </section>

      <SafetyGatePanel
        title="Dowody i warunki sprawdzenia Demand Gen"
        description="To jest sprawdzenie gotowości, nie kreator kampanii. Brakujące dane są jawne i muszą powstać w API przed rekomendacjami."
      >
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
            values={[data.action_summary_label]}
          />
          <TraceLine
            label="Warunki sprawdzenia"
            values={data.operator_review_gate_labels}
          />
          <TraceLine
            label="Nie wolno twierdzić"
            values={data.blocked_claims}
          />
        </div>
        <p className="mt-4 text-sm font-medium text-ink">{data.next_step}</p>
      </SafetyGatePanel>
    </>
  );
}

function DemandGenPreviewCard({ card }: { card: ActionPreviewCardViewModel }) {
  return (
    <div className="rounded-md border border-line bg-white p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h4 className="text-sm font-semibold text-ink">{card.title_label}</h4>
          {card.subtitle_label ? (
            <p className="mt-1 text-xs text-slate-500">{card.subtitle_label}</p>
          ) : null}
        </div>
        {card.status_label ? (
          <span className="rounded-full border border-line bg-slate-50 px-2 py-1 text-xs text-slate-600">
            {card.status_label}
          </span>
        ) : null}
      </div>
      <div className="mt-3 grid gap-1.5 text-xs text-slate-700">
        {card.rows.map((row) => (
          <div key={`${card.id}-${row.label}`} className="flex gap-2">
            <span className="min-w-32 text-slate-500">{row.label}:</span>
            <span>{row.value}</span>
          </div>
        ))}
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-600">
        {card.apply_state_label ? <span>{card.apply_state_label}</span> : null}
        {card.system_readiness_label ? <span>{card.system_readiness_label}</span> : null}
      </div>
    </div>
  );
}
