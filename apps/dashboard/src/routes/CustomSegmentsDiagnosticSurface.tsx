import { useQuery } from "@tanstack/react-query";
import { ShieldAlert } from "lucide-react";

import { AdsDiagnosticsResponse, getAdsDiagnostics } from "../lib/api";
import { BlockerNotice, LoadingBand, MetricTile } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import { LinkedTraceLine, TraceLine } from "../components/TraceLine";
import {
  adsBlockedClaimLabel,
  adsMissingReadContractLabel
} from "./marketingLabels";

type AdsCustomSegmentCandidate =
  AdsDiagnosticsResponse["custom_segments_read_contract"]["candidates"][number];
type AdsCustomSegmentAudienceForecastRow =
  AdsDiagnosticsResponse["custom_segments_read_contract"]["audience_forecast_read_contract"]["forecast_rows"][number];

export function AdsCustomSegmentCandidatesPanel({
  candidates,
  compact = false
}: {
  candidates: AdsCustomSegmentCandidate[];
  compact?: boolean;
}) {
  if (candidates.length === 0) {
    return compact ? null : (
      <BlockerNotice message="Brak kandydatów custom segments. WILQ potrzebuje realnych search terms i walidacji Keyword Planner, zanim przygotuje payload." />
    );
  }
  return (
    <div className={compact ? "mt-3 grid gap-2" : "rounded-md border border-line bg-slate-50 p-3"}>
      {!compact ? (
        <div className="mb-3">
          <h3 className="text-sm font-semibold text-ink">
            Kandydaci custom segments z search terms
          </h3>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            To jest prepare-only kolejka. WILQ nie twierdzi, że segment ma zasięg,
            ROAS albo wpływ na kampanię bez osobnego forecastu i walidacji.
          </p>
        </div>
      ) : null}
      <div className={compact ? "grid gap-2" : "grid gap-3 md:grid-cols-2"}>
        {candidates.slice(0, compact ? 2 : 6).map((candidate) => {
          const rejectionEntries = Object.entries(candidate.source_quality.rejection_reasons);
          return (
          <article key={candidate.id} className="rounded-md border border-line bg-white p-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h4 className="text-sm font-semibold text-ink">{candidate.name}</h4>
                <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
                  {candidate.intent} / pewność: {candidate.confidence}
                </p>
              </div>
              <span className="rounded-md border border-line bg-slate-50 px-2 py-1 text-xs text-slate-600">
                {candidate.review_priority} / {candidate.review_score}
              </span>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-700">
              {candidate.review_reason}
            </p>
            <div className="mt-2 rounded-md border border-amber-100 bg-amber-50 p-2 text-xs leading-5 text-slate-700">
              <div className="font-semibold uppercase tracking-normal text-amber-700">
                Jakość źródeł
              </div>
              <div className="mt-1 flex flex-wrap gap-2">
                <span>przyjęte: {candidate.source_quality.accepted_terms}</span>
                <span>odrzucone: {candidate.source_quality.rejected_terms}</span>
                <span>braki metryk: {candidate.source_quality.missing_metric_terms}</span>
              </div>
              {rejectionEntries.length > 0 ? (
                <div className="mt-1 text-slate-600">
                  Powody:{" "}
                  {rejectionEntries
                    .slice(0, 3)
                    .map(([reason, count]) => `${reason} (${count})`)
                    .join(", ")}
                </div>
              ) : null}
            </div>
            <p className="mt-1 text-xs leading-5 text-slate-600">
              Walidacja:{" "}
              {candidate.validation_status === "pending_validation"
                ? "do walidacji"
                : "blocked"}
            </p>
            <p className="mt-2 text-sm font-medium text-ink">{candidate.next_step}</p>
            {candidate.payload_preview ? (
              <div className="mt-2 rounded-md border border-blue-100 bg-blue-50 p-2 text-xs leading-5 text-slate-700">
                <div className="font-semibold uppercase tracking-normal text-blue-700">
                  Podgląd segmentu
                </div>
                <div>{candidate.payload_preview.custom_segment_name}</div>
                <div className="text-slate-600">
                  Typ wejścia: {candidate.payload_preview.member_type}. Wdrożenie:{" "}
                  {candidate.payload_preview.apply_allowed
                    ? "wymaga walidacji"
                    : "zablokowany"}
                  .
                </div>
                <div className="mt-1 text-slate-600">
                  Safety: {candidate.payload_preview.safety_review.safety_contract} /{" "}
                  {candidate.payload_preview.safety_review.audit_required
                    ? "audyt wymagany"
                    : "audyt niewymagany"}
                  . Braki:{" "}
                  {candidate.payload_preview.safety_review.missing_requirements
                    .map(adsMissingReadContractLabel)
                    .join(", ")}
                  .
                </div>
                {candidate.payload_preview.targeting_preview.length > 0 ? (
                  <div className="mt-1 text-slate-600">
                    Targeting preview:{" "}
                    {candidate.payload_preview.targeting_preview
                      .slice(0, 2)
                      .map((target) =>
                        [
                          target.campaign_name || target.campaign_id || "kampania do review",
                          target.apply_allowed ? "apply możliwy" : "apply zablokowany"
                        ].join(" / ")
                      )
                      .join(", ")}
                  </div>
                ) : null}
              </div>
            ) : null}
            {candidate.keyword_planner_ideas.length > 0 ? (
              <div className="mt-2 rounded-md border border-emerald-100 bg-emerald-50 p-2 text-xs leading-5 text-slate-700">
                <div className="font-semibold uppercase tracking-normal text-emerald-700">
                  Keyword Planner enrichment
                </div>
                <div className="mt-1 grid gap-1">
                  {candidate.keyword_planner_ideas.slice(0, compact ? 2 : 4).map((idea) => (
                    <div key={`${candidate.id}-${idea.idea_text}`} className="text-slate-700">
                      <span className="font-medium text-ink">{idea.idea_text}</span>
                      {typeof idea.avg_monthly_searches === "number" ? (
                        <span> / avg monthly searches: {idea.avg_monthly_searches}</span>
                      ) : null}
                      {idea.competition ? <span> / competition: {idea.competition}</span> : null}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
            <div className="mt-2 grid gap-2 text-xs text-slate-600">
              <TraceLine
                label="Review człowieka"
                values={candidate.human_review_gates}
                empty="brak"
              />
              <TraceLine label="Source terms" values={candidate.source_terms.slice(0, 8)} />
              <TraceLine label="Odrzucone" values={candidate.rejected_terms.slice(0, 6)} />
              <LinkedTraceLine
                label="Dowody"
                values={candidate.evidence_ids.slice(0, 4)}
                kind="evidence"
              />
              <TraceLine
                label="Nie wolno twierdzić"
                values={candidate.blocked_claims.map(adsBlockedClaimLabel)}
              />
            </div>
          </article>
          );
        })}
      </div>
    </div>
  );
}

export function AdsCustomSegmentAudienceForecastPanel({
  rows,
  compact = false
}: {
  rows: AdsCustomSegmentAudienceForecastRow[];
  compact?: boolean;
}) {
  if (rows.length === 0) {
    return compact ? null : (
      <BlockerNotice message="Brak wierszy forecast/audience size. WILQ nie może ocenić zasięgu segmentów bez osobnego read contract." />
    );
  }
  return (
    <div className={compact ? "mt-3 grid gap-2" : "rounded-md border border-line bg-slate-50 p-3"}>
      {!compact ? (
        <div className="mb-3">
          <h3 className="text-sm font-semibold text-ink">
            Forecast i audience size custom segments
          </h3>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            To jest safety contract. Wiersz oznacza, że kandydat został
            sprawdzony, ale WILQ nadal nie ma dowodu zasięgu ani forecastu.
          </p>
        </div>
      ) : null}
      <div className={compact ? "grid gap-2" : "grid gap-3 md:grid-cols-2"}>
        {rows.slice(0, compact ? 2 : 6).map((row) => (
          <article key={row.id} className="rounded-md border border-line bg-white p-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h4 className="text-sm font-semibold text-ink">
                  {row.custom_segment_name}
                </h4>
                <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
                  {row.status === "ready" ? "forecast ready" : "forecast missing"}
                </p>
              </div>
              <span className="rounded-md border border-line bg-slate-50 px-2 py-1 text-xs text-slate-600">
                audience: {typeof row.audience_size === "number" ? row.audience_size : "brak"}
              </span>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-700">{row.reason}</p>
            <div className="mt-2 grid gap-2 text-xs text-slate-600">
              <TraceLine label="Source terms" values={row.source_terms.slice(0, 8)} />
              <LinkedTraceLine
                label="Dowody"
                values={row.evidence_ids.slice(0, 4)}
                kind="evidence"
              />
              <TraceLine
                label="Nie wolno twierdzić"
                values={row.blocked_claims.map(adsBlockedClaimLabel)}
              />
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

export function CustomSegmentsDiagnosticSurface() {
  const diagnostics = useQuery({
    queryKey: ["ads-diagnostics", "custom-segments"],
    queryFn: getAdsDiagnostics
  });

  if (diagnostics.isLoading) return <LoadingBand />;
  if (diagnostics.error || !diagnostics.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać /api/ads/diagnostics. Custom segments nie mogą być oceniane bez WILQ API." />
      </main>
    );
  }

  const data = diagnostics.data;
  const contract = data.custom_segments_read_contract;
  const audienceForecast = contract.audience_forecast_read_contract;
  const keywordPlanner = data.keyword_planner_read_contract;
  const customDecision = data.decision_queue.find(
    (decision) => decision.id === "ads_prepare_custom_segments_from_search_terms"
  );
  const sourceTermCount = contract.candidates.reduce(
    (total, candidate) => total + candidate.source_terms.length,
    0,
  );
  const rejectedTermCount = contract.candidates.reduce(
    (total, candidate) => total + candidate.rejected_terms.length,
    0,
  );

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Custom Segments</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Dedykowany widok kandydatów segmentów z Google Ads search terms.
            WILQ pokazuje tylko source terms z evidence i payload preview do
            review; zasięg, uplift, ROAS i targeting apply pozostają zablokowane.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs sm:grid-cols-4">
          <MetricTile label="Segmenty" value={contract.candidates.length} />
          <MetricTile label="Source terms" value={sourceTermCount} />
          <MetricTile label="Odrzucone" value={rejectedTermCount} />
          <MetricTile label="KP ideas" value={keywordPlanner.idea_rows.length} />
          <MetricTile label="Forecast" value={audienceForecast.forecast_row_count} />
        </div>
      </div>

      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Status Custom Segments / search terms evidence
            </h2>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
              {contract.summary}
            </p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <StatusBadge value={contract.status === "ready" ? "gotowe" : "zablokowane"} />
            <StatusBadge value={customDecision?.status === "ready" ? "do review" : "blocked"} />
            <StatusBadge value={keywordPlanner.status === "ready" ? "KP ready" : "KP blocked"} />
            <StatusBadge
              value={audienceForecast.status === "ready" ? "forecast ready" : "forecast blocked"}
            />
          </div>
        </div>
        <p className="mt-3 text-sm font-medium text-ink">{contract.next_step}</p>
        <p className="mt-2 text-xs leading-5 text-slate-600">
          Keyword Planner: {keywordPlanner.summary}
        </p>
        <p className="mt-1 text-xs leading-5 text-slate-600">
          Forecast/audience size: {audienceForecast.summary}
        </p>
      </section>

      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
              Operator segmentów
            </div>
            <h2 className="mt-1 text-base font-semibold tracking-normal">
              Co marketer może przygotować teraz
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              Użyj kandydatów tylko jako listy do review. Odrzuć frazy brandowe,
              niskointencyjne lub zbyt szerokie, a przed apply wymagaj Keyword
              Planner enrichment, forecastu i potwierdzenia człowieka.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-2 text-center text-xs">
            <MetricTile
              label="Braki kontraktu"
              value={contract.missing_read_contracts.length}
            />
            <MetricTile
              label="Review gates"
              value={contract.operator_review_gates.length}
            />
          </div>
        </div>
        <AdsCustomSegmentCandidatesPanel candidates={contract.candidates} />
        <div className="mt-4">
          <AdsCustomSegmentAudienceForecastPanel
            rows={audienceForecast.forecast_rows}
            compact
          />
        </div>
      </section>

      <section className="rounded-md border border-line bg-white p-4">
        <div className="mb-3 flex items-start gap-3">
          <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
            <ShieldAlert aria-hidden="true" size={18} />
          </div>
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Dowody i ograniczenia segmentów
            </h2>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
              Ten ekran nie służy do tworzenia audience bez walidacji. Pokazuje
              tylko review-only kontrakt z WILQ API.
            </p>
          </div>
        </div>
        <div className="grid gap-2 text-xs text-slate-600">
          <TraceLine
            label="Brakujące kontrakty"
            values={uniqueValues([
              ...contract.missing_read_contracts,
              ...audienceForecast.missing_read_contracts
            ]).map(adsMissingReadContractLabel)}
          />
          <TraceLine
            label="Wymaga review"
            values={uniqueValues([
              ...contract.operator_review_gates,
              ...audienceForecast.operator_review_gates
            ]).map(adsOperatorReviewGateLabel)}
          />
          <TraceLine
            label="Nie wolno twierdzić"
            values={uniqueValues([
              ...contract.blocked_claims,
              ...audienceForecast.blocked_claims
            ]).map(adsBlockedClaimLabel)}
          />
          <TraceLine label="Źródła" values={contract.source_connectors} />
          <LinkedTraceLine label="Dowody" values={contract.evidence_ids} kind="evidence" />
          <LinkedTraceLine label="Akcje" values={contract.action_ids} kind="actions" />
          <TraceLine label="Tryb Codexa" values={["Custom Segments"]} />
        </div>
      </section>
    </main>
  );
}

function adsOperatorReviewGateLabel(value: string) {
  const labels: Record<string, string> = {
    human_strategy_review: "review strategii przez człowieka",
    review_recommendation_type: "sprawdzenie typu rekomendacji",
    review_impact_metrics: "sprawdzenie impact metrics",
    review_change_history: "sprawdzenie historii zmian",
    review_business_goal: "sprawdzenie celu biznesowego",
    configure_business_goal: "uzupełnienie celu biznesowego",
    review_profit_margin_model: "sprawdzenie modelu marży",
    configure_profit_margin_or_value_model: "uzupełnienie marży albo modelu wartości",
    review_human_budget_goal: "sprawdzenie celu budżetu",
    configure_human_budget_goal: "uzupełnienie celu budżetu",
    confirm_target_roas_or_cpa: "potwierdzenie targetu ROAS albo CPA",
    review_target_fit: "sprawdzenie dopasowania do targetu",
    review_campaign_goal: "sprawdzenie celu kampanii",
    review_conversion_quality: "sprawdzenie jakości konwersji",
    review_budget_context: "sprawdzenie kontekstu budżetu",
    review_search_terms_before_budget_decision: "search terms przed decyzją budżetową",
    review_conversion_tracking: "sprawdzenie trackingu konwersji",
    review_pmax_asset_feed_context: "sprawdzenie PMax/feed/assets",
    review_draft_campaign_status: "sprawdzenie statusu draftu",
    recommendation_apply_preview: "podgląd apply rekomendacji",
    google_ads_rmf_compliance_review: "review Google Ads RMF/compliance",
    human_confirm_before_apply: "potwierdzenie człowieka przed wdrożeniem",
    negative_keyword_action_validation: "walidacja ActionObject dla wykluczeń",
    human_intent_review: "ręczny review intencji",
    review_source_terms: "sprawdzenie source terms",
    reject_brand_or_low_intent_terms: "odrzucenie brand/low intent terms",
    keyword_planner_enrichment: "enrichment Keyword Planner",
    forecast_or_audience_size: "forecast albo audience size"
  };
  return labels[value] ?? value;
}

function uniqueValues(values: string[]) {
  return Array.from(new Set(values));
}
