import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getKnowledgeSourceMaterialReadiness,
  getContentWorkItemPlanningProposal,
  postContentWorkItemPlanningProposal
} from "../lib/api";
import type { ContentPlanningProposalResponse } from "../lib/api";

export function ContentPlanningGenerationPanel({
  serviceCardId,
  workItemId
}: {
  serviceCardId: string | null | undefined;
  workItemId: string;
}) {
  const queryClient = useQueryClient();
  const queryKey = ["content-workflow", "work-item", workItemId, "planning-proposal"];
  const status = useQuery({
    queryKey,
    queryFn: () => getContentWorkItemPlanningProposal(workItemId),
    staleTime: 5_000,
    refetchInterval: (query) =>
      query.state.data?.status === "generating" ? 1500 : false
  });
  const materialReadiness = useQuery({
    queryKey: ["content-workflow", "knowledge-source-material-readiness"],
    queryFn: getKnowledgeSourceMaterialReadiness,
    staleTime: 60_000
  });
  const generation = useMutation({
    mutationFn: () => {
      const digest = status.data?.planning_input_digest;
      if (!digest || !serviceCardId) throw new Error("Planning input is not ready.");
      return postContentWorkItemPlanningProposal(
        {
          service_card_id: serviceCardId,
          expected_planning_input_digest: digest,
          operator_hint: "",
          requested_by: "wilku"
        },
        workItemId
      );
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey }),
        queryClient.invalidateQueries({
          queryKey: ["content-workflow", "work-item", workItemId],
          exact: true
        })
      ]);
    }
  });

  if (status.isLoading) {
    return (
      <section className="rounded-md border border-line bg-white p-4 shadow-sm">
        <p className="text-sm text-slate-600">Sprawdzam gotowość planowania…</p>
      </section>
    );
  }
  if (status.error || !status.data) {
    return (
      <section className="rounded-md border border-danger/30 bg-danger/5 p-4 shadow-sm">
        <p className="font-semibold text-danger">Nie udało się odczytać stanu planu</p>
        <p className="mt-1 text-sm text-slate-700">
          Odśwież stronę albo spróbuj ponownie, gdy stan danych będzie dostępny.
        </p>
      </section>
    );
  }

  const state = generation.data ?? status.data;
  const proposal = state.proposal;
  const currentProposal = ["created", "idempotent", "ready"].includes(state.status)
    ? proposal
    : null;
  const blocker = state.blockers?.[0] ?? null;
  const inputSummary = state.input_summary ?? null;
  const pendingMaterialTitles = (materialReadiness.data?.pending_materials ?? []).map(
    (material) => material.title
  );
  const usedSourceCount = inputSummary?.source_assessments.filter(
    (source) => source.status === "used"
  ).length ?? 0;
  const landingBoundSourceCount = inputSummary?.source_assessments.filter(
    (source) => source.landing_match_tiers.length > 0
  ).length ?? 0;
  const inputReady = Boolean(
    inputSummary &&
      inputSummary.inventory_status === "available" &&
      inputSummary.content_inventory_status === "available" &&
      !inputSummary.source_assessments.some(
        (source) => source.status === "stale" || source.status === "blocked"
      )
  );
  const serviceSelectionConfirmed =
    state.proposal?.service_selection_confirmed === true ||
    (state.status === "failed" && state.service_card_id === serviceCardId);
  const canGenerate = Boolean(
    serviceCardId &&
      serviceSelectionConfirmed &&
      state.planning_input_digest &&
      inputReady &&
      (["not_generated", "failed"].includes(state.status) ||
        (state.status === "stale" && state.blockers.every((item) => item.code === "stale_input")))
  );

  return (
    <section
      aria-labelledby="content-planning-generation-title"
      className="rounded-md border border-line bg-white p-4 shadow-sm"
      data-testid="content-planning-generation"
    >
      <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">
        Strategia
      </p>
      <div className="mt-1 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="content-planning-generation-title" className="text-lg font-semibold text-ink">
            {planningHeadline(state.status, Boolean(currentProposal))}
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-700">
            {blocker?.reason ??
              currentProposal?.value_proposition ??
              "Plan powstanie z aktualnej strony, wybranej usługi i dostępnych danych."}
          </p>
        </div>
        <span className="rounded-md border border-line bg-surface px-3 py-2 text-xs font-semibold text-slate-600">
          {planningStatusLabel(state.status)}
        </span>
      </div>

      {inputSummary ? (
        <div className="mt-4 rounded-md border border-line bg-surface p-3">
          <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Na czym opiera się ta decyzja
          </p>
          <div className="mt-2 grid gap-2 text-sm sm:grid-cols-5">
            <PlanningInputFact label="Fakty firmy" value={inputSummary.source_fact_count} />
            <PlanningInputFact label="Materiały firmy" value={inputSummary.source_material_ids.length} />
            <PlanningInputFact label="Karty wiedzy" value={inputSummary.knowledge_card_count} />
            <PlanningInputFact label="Metryki" value={inputSummary.measurement_metrics.length} />
            <PlanningInputFact label="Ślady źródeł" value={inputSummary.evidence_id_count} />
          </div>
          <p className="mt-2 text-xs leading-5 text-slate-600" data-testid="content-planning-source-summary">
            {planningSourceSummary(inputSummary)}
          </p>
          <PlanningSourceOutcomeStrip assessments={inputSummary.source_assessments} />
          <PlanningSourceFactPreview facts={inputSummary.source_fact_previews} total={inputSummary.source_fact_count} />
          <PlanningMetricComparisons comparisons={inputSummary.metric_comparisons} />
        </div>
      ) : null}

      {materialReadiness.data?.status === "import_pending" ? (
        <p
          className="mt-3 rounded-md border border-wait/30 bg-wait/10 p-3 text-sm text-slate-700"
          data-testid="content-material-readiness-warning"
        >
          Materiały firmy: {materialReadiness.data.imported_count}/
          {materialReadiness.data.total_count} dostępnych. {materialReadiness.data.blocker} {materialReadiness.data.next_step}
          {pendingMaterialTitles.length > 0 ? (
            <> Czekają: {pendingMaterialTitles.slice(0, 3).join(" · ")}{pendingMaterialTitles.length > 3 ? ` · +${pendingMaterialTitles.length - 3}` : ""}.</>
          ) : null}
        </p>
      ) : null}

      {currentProposal ? (
        <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(18rem,0.7fr)]">
          <div className="rounded-md border border-line bg-surface p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs font-semibold uppercase text-slate-500">Aktualny plan</p>
              <span className="rounded-full border border-action/20 bg-action/5 px-2 py-1 text-[11px] font-semibold text-action">
                gotowy do review
              </span>
            </div>
            <p className="mt-2 text-xs font-semibold uppercase text-slate-500">Kąt i intencja</p>
            <p className="mt-1 text-sm font-semibold text-ink">{currentProposal.angle}</p>
            <p className="mt-1 text-sm text-slate-700">{currentProposal.search_intent}</p>
          </div>
          <div className="rounded-md border border-line bg-surface p-3">
            <p className="text-xs font-semibold uppercase text-slate-500">Zakres</p>
            <p className="mt-1 text-sm text-slate-700">
              {currentProposal.sections.length} sekcji · {currentProposal.faq.length} FAQ · {currentProposal.cta_blocks.length} CTA · {currentProposal.internal_links.length} linków
            </p>
          </div>
        </div>
      ) : null}

      {currentProposal ? (
        <div
          className="mt-4 rounded-md border border-action/20 bg-action/5 p-4"
          data-testid="content-planning-page-assets"
        >
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">
              Podgląd elementów strony
            </p>
            <span className="text-xs text-slate-500">wynik planu · bez zapisu do WordPress</span>
          </div>
          <dl className="mt-3 grid gap-3 sm:grid-cols-2">
            <PlanningPageAsset label="Tytuł WordPress" value={currentProposal.page_assets.title} />
            <PlanningPageAsset label="H1" value={currentProposal.page_assets.h1} />
            <PlanningPageAsset label="Meta title" value={currentProposal.page_assets.meta_title} />
            <PlanningPageAsset label="Meta description" value={currentProposal.page_assets.meta_description} />
            <div className="sm:col-span-2">
              <PlanningPageAsset label="Lead" value={currentProposal.page_assets.lead} />
            </div>
          </dl>
        </div>
      ) : null}

      {currentProposal?.search_demand.gsc_query_rows.length ? (
        <div className="mt-4 rounded-md border border-line bg-surface p-3">
          <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Metryki, od których zaczynamy
          </p>
          <div className="mt-2 grid gap-2 sm:grid-cols-3">
            {currentProposal.search_demand.gsc_query_rows.slice(0, 3).map((row) => (
              <div key={`${row.term}-${row.page}`} className="rounded-md border border-line bg-white p-3">
                <p className="text-sm font-semibold text-ink">{row.term}</p>
                <p className="mt-1 text-xs leading-5 text-slate-600">
                  {formatDemandMetrics(row)}
                </p>
              </div>
            ))}
          </div>
          <p className="mt-2 text-xs text-slate-500">
            To punkt wyjścia do decyzji o treści, nie obietnica wyniku.
          </p>
        </div>
      ) : null}

      {canGenerate ? (
        <button
          type="button"
          disabled={generation.isPending}
          onClick={() => generation.mutate()}
          className="mt-4 inline-flex h-11 items-center rounded-md bg-action px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
        >
          {generation.isPending
            ? "Przygotowujemy plan…"
            : state.status === "failed"
              ? "Spróbuj ponownie"
            : state.status === "stale"
              ? "Wygeneruj aktualny plan"
              : "Wygeneruj plan"}
        </button>
      ) : null}

      {!serviceSelectionConfirmed && serviceCardId ? (
        <p
          className="mt-4 rounded-md border border-wait/30 bg-wait/10 p-3 text-sm leading-6 text-slate-700"
          data-testid="content-planning-service-confirmation-gate"
        >
          Najpierw potwierdź usługę w kroku zakresu. Rekomendowane dopasowanie jest
          wskazówką, nie zgodą na uruchomienie planu.
        </p>
      ) : null}

      {state.status === "generating" ? (
        <p
          aria-live="polite"
          className="mt-4 rounded-md border border-action/20 bg-action/5 p-3 text-sm text-slate-700"
        >
          Plan jest przygotowywany z aktualnej strony, metryk i wybranej usługi.
          Ten panel odświeży wynik automatycznie. Możesz przejść do innego kroku;
          nie uruchamiaj kolejnego planu dla tego samego wejścia.
        </p>
      ) : null}

      {blocker ? (
        <p className="mt-3 rounded-md border border-wait/30 bg-wait/10 p-3 text-sm text-slate-700">
          <span className="font-semibold text-wait">Bloker: </span>
          {blocker.label}. {blocker.next_step}
        </p>
      ) : null}
      {generation.error ? (
        <p role="alert" className="mt-3 text-sm text-danger">
          Nie zapisano planu. Odśwież gotowość i spróbuj ponownie.
        </p>
      ) : null}

      <details className="mt-3 text-xs text-slate-500">
        <summary className="cursor-pointer font-semibold text-action">Dlaczego ten stan?</summary>
        <p className="mt-2 break-all">
          Input: {state.planning_input_digest ?? "brak"} · zapis techniczny: {currentProposal?.proposal_version ?? "brak"}
        </p>
        {inputSummary ? (
          <>
            <p className="mt-2">
              Użyto {usedSourceCount} z {inputSummary.source_assessments.length} źródeł;
              {" "}{landingBoundSourceCount} ma potwierdzone powiązanie z tą stroną;
              {" "}{inputSummary.evidence_id_count} zapisów źródłowych.
            </p>
            <ul className="mt-3 space-y-2">
            {inputSummary.source_assessments.map((source) => (
              <li key={source.source} className="rounded-md border border-line bg-surface p-2">
                <span className="font-semibold text-ink">
                  Źródło: {planningSourceLabel(source.source)} · status: {planningSourceStatusLabel(source.status)}
                </span>
                {source.landing_match_tiers.length ? (
                  <span> · landing {source.landing_match_tiers.map(landingTierLabel).join(", ")}</span>
                ) : null}
                <span className="block mt-1 leading-5 text-slate-600">{source.reason}</span>
              </li>
            ))}
            </ul>
          </>
        ) : null}
        {blocker?.source_codes?.length ? (
          <p className="mt-2" data-testid="content-planning-blocker-trace">
            Ślad runtime: {blocker.source_codes.join(", ")}
          </p>
        ) : null}
        {state.status === "failed" && state.runtime?.run_id ? (
          <p className="mt-2" data-testid="content-planning-runtime-run">
            Ostatnia próba: {state.runtime.run_id}
          </p>
        ) : null}
        <p className="mt-1">Samo otwarcie tego widoku nie uruchamia generowania.</p>
      </details>
    </section>
  );
}

function PlanningSourceFactPreview({
  facts,
  total
}: {
  facts?: NonNullable<ContentPlanningProposalResponse["input_summary"]>["source_fact_previews"];
  total: number;
}) {
  if (!facts?.length) return null;
  const visible = facts.slice(0, 6);
  return (
    <div className="mt-4" data-testid="content-planning-source-facts">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">
          Fakty użyte przez plan
        </p>
        <span className="text-[11px] text-slate-500">
          {visible.length} z {total}
        </span>
      </div>
      <ul className="mt-2 grid gap-2 md:grid-cols-2">
        {visible.map((fact) => (
          <li key={fact.fact_id} className="rounded-md border border-line bg-white p-3">
            <p className="text-sm leading-6 text-ink">{fact.summary}</p>
            <p className="mt-2 text-[11px] text-slate-500">
              {planningSourceLabel(fact.source_connector)} · {fact.source_material_ids.length} materiałów · {fact.evidence_ids.length} {fact.evidence_ids.length === 1 ? "evidence" : "evidence IDs"}
            </p>
          </li>
        ))}
      </ul>
      {total > visible.length ? (
        <p className="mt-2 text-xs text-slate-500">
          Pozostałe fakty są związane z tym samym input digestem i pozostają w technicznym śladzie planu.
        </p>
      ) : null}
    </div>
  );
}

function PlanningInputFact({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-line bg-white px-3 py-2">
      <span className="block text-xs text-slate-500">{label}</span>
      <span className="mt-1 block text-base font-semibold text-ink">{value}</span>
    </div>
  );
}

function PlanningPageAsset({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-line bg-white p-3">
      <dt className="text-[11px] font-semibold uppercase tracking-normal text-slate-500">{label}</dt>
      <dd className="mt-1 text-sm leading-6 text-ink">{value || "Brak elementu w planie"}</dd>
    </div>
  );
}

type PlanningSourceAssessment = NonNullable<
  ContentPlanningProposalResponse["input_summary"]
>["source_assessments"][number];

export function planningSourceOutcomeLabels(
  assessments: PlanningSourceAssessment[]
): string[] {
  return assessments
    .filter((assessment) =>
      ["wordpress", "gsc", "ga4", "google_ads", "ahrefs"].includes(assessment.source)
    )
    .map((assessment) => {
      const landing = assessment.landing_match_tiers.length
        ? ` · ${assessment.landing_match_tiers.map(landingTierLabel).join(", ")}`
        : "";
      return `${planningSourceLabel(assessment.source)}: ${planningSourceStatusLabel(assessment.status)}${landing}`;
    });
}

function PlanningSourceOutcomeStrip({
  assessments
}: {
  assessments: PlanningSourceAssessment[];
}) {
  const outcomes = planningSourceOutcomeLabels(assessments);
  if (!outcomes.length) return null;
  return (
    <div className="mt-3" data-testid="content-planning-source-outcomes">
      <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">
        Źródła i dopasowanie strony
      </p>
      <div className="mt-2 flex flex-wrap gap-2">
        {outcomes.map((outcome) => (
          <span
            key={outcome}
            className="rounded-full border border-line bg-white px-2.5 py-1 text-xs font-medium text-slate-700"
          >
            {outcome}
          </span>
        ))}
      </div>
    </div>
  );
}

function PlanningMetricComparisons({
  comparisons
}: {
  comparisons?: NonNullable<ContentPlanningProposalResponse["input_summary"]>["metric_comparisons"];
}) {
  if (!comparisons?.length) return null;
  return (
    <div className="mt-4" data-testid="content-planning-metric-comparisons">
      <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">
        Rzeczywiste zmiany metryk strony
      </p>
      <div className="mt-2 grid gap-2 md:grid-cols-2">
        {comparisons.map((comparison) => (
          <div key={comparison.source_connector} className="rounded-md border border-line bg-white p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-sm font-semibold text-ink">
                {planningSourceLabel(comparison.source_connector)}
              </span>
              <span className="text-xs font-semibold text-slate-500">
                {comparisonStatusLabel(comparison.status)}
              </span>
            </div>
            {comparison.status === "available" ? (
              <>
                <p className="mt-1 text-xs text-slate-500">
                  {comparison.baseline_period ?? "okres bazowy"} → {comparison.comparison_period ?? "ostatni okres"}
                </p>
                <ul className="mt-2 grid gap-1 text-xs text-slate-700 sm:grid-cols-2">
                  {comparison.metric_names.map((metric) => (
                    <li key={metric}>
                      <span className="font-medium">{metricLabel(metric)}:</span>{" "}
                      {formatMetricValue(comparison.baseline_values[metric])} → {formatMetricValue(comparison.comparison_values[metric])}
                    </li>
                  ))}
                </ul>
              </>
            ) : (
              <p className="mt-1 text-xs leading-5 text-slate-600">{comparison.reason}</p>
            )}
            {comparison.evidence_ids.length ? (
              <p className="mt-2 text-[11px] text-slate-500">
                Evidence: {comparison.evidence_ids.length} exact {comparison.evidence_ids.length === 1 ? "ślad" : "ślady"}
              </p>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}

function comparisonStatusLabel(status: string) {
  return {
    available: "porównywalne",
    not_available: "brak porównania",
    ambiguous: "niejednoznaczne"
  }[status] ?? status;
}

function metricLabel(metric: string) {
  return {
    clicks: "kliknięcia",
    impressions: "wyświetlenia",
    ctr: "CTR",
    average_position: "średnia pozycja",
    sessions: "sesje",
    engaged_sessions: "sesje zaangażowane",
    engagement_rate: "zaangażowanie",
    key_events: "key events"
  }[metric] ?? metric;
}

function formatMetricValue(value: number | undefined) {
  if (value === undefined) return "brak";
  return Number.isInteger(value)
    ? value.toLocaleString("pl-PL")
    : value.toLocaleString("pl-PL", { maximumFractionDigits: 2 });
}

function formatDemandMetrics(
  row: NonNullable<ContentPlanningProposalResponse["proposal"]>["search_demand"]["gsc_query_rows"][number]
) {
  const metrics = [
    row.impressions === null ? null : `${row.impressions} wyśw.`,
    row.clicks === null ? null : `${row.clicks} klik.`,
    row.ctr === null ? null : `CTR ${(row.ctr * 100).toFixed(1)}%`,
    row.average_position === null ? null : `poz. ${row.average_position.toFixed(1)}`
  ].filter(Boolean);
  return metrics.join(" · ") || "Brak metryk liczbowych";
}

function planningHeadline(status: string, hasCurrentProposal: boolean) {
  if (hasCurrentProposal) return "Plan strony jest gotowy do review";
  if (status === "generating") return "Przygotowujemy plan strony";
  if (status === "stale") return "Plan wymaga aktualizacji";
  if (status === "blocked") return "Plan jest zablokowany";
  if (status === "failed") return "Nie udało się zbudować planu";
  return "Zbuduj plan z aktualnych danych";
}

function planningSourceLabel(source: string) {
  const labels: Record<string, string> = {
    wordpress: "WordPress",
    public_site: "Publiczna strona Ekologusa",
    ekologus_ai_private_source_catalog: "Materiały Ekologusa",
    service_profile: "Profil usługi",
    gsc: "GSC",
    google_search_console: "Google Search Console",
    ga4: "GA4",
    google_analytics_4: "Google Analytics 4",
    google_ads: "Google Ads",
    ahrefs: "Ahrefs",
    keyword_planner: "Keyword Planner",
    merchant: "Merchant",
    localo: "Localo",
    social: "Social"
  };
  return labels[source] ?? source;
}

function planningSourceStatusLabel(status: string) {
  const labels: Record<string, string> = {
    used: "użyte",
    not_applicable: "nie dotyczy",
    missing: "brak",
    stale: "nieaktualne",
    blocked: "zablokowane"
  };
  return labels[status] ?? status;
}

export function planningSourceSummary(
  inputSummary: NonNullable<ContentPlanningProposalResponse["input_summary"]>
) {
  const used = inputSummary.source_assessments.filter((source) => source.status === "used").length;
  const landingBound = inputSummary.source_assessments.filter(
    (source) => source.landing_match_tiers.length > 0
  ).length;
  const extraSources = inputSummary.source_assessments
    .filter((source) => ["ga4", "google_ads"].includes(source.source) && source.status !== "used")
    .map((source) => `${planningSourceLabel(source.source)}: ${planningSourceStatusLabel(source.status)}`);
  const suffix = extraSources.length ? ` ${extraSources.join(" · ")}.` : "";
  return `Źródła planu: ${used}/${inputSummary.source_assessments.length} użyte · ${landingBound} z exact powiązaniem ze stroną.${suffix}`;
}

function landingTierLabel(tier: string) {
  const labels: Record<string, string> = {
    exact: "exact",
    tracking_only: "po usunięciu trackingu",
    host_alias: "alias hosta"
  };
  return labels[tier] ?? tier;
}

function planningStatusLabel(status: string) {
  const labels: Record<string, string> = {
    not_generated: "nie wygenerowano",
    generating: "w przygotowaniu",
    created: "nowy plan",
    idempotent: "ta sama wersja",
    ready: "gotowy do review",
    stale: "wejście zmienione",
    blocked: "zablokowany",
    failed: "błąd bez zapisu"
  };
  return labels[status] ?? status;
}
