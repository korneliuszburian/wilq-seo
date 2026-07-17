import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getContentWorkItemPlanningProposal,
  postContentWorkItemPlanningProposal
} from "../lib/api";

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
    queryFn: () => getContentWorkItemPlanningProposal(workItemId)
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
        <p className="mt-1 text-sm text-slate-700">WILQ nie uruchomił Codexa.</p>
      </section>
    );
  }

  const state = generation.data ?? status.data;
  const proposal = state.proposal;
  const currentProposal = ["created", "idempotent", "ready"].includes(state.status)
    ? proposal
    : null;
  const blocker = state.blockers[0] ?? null;
  const inputSummary = state.input_summary ?? null;
  const usedSourceCount = inputSummary?.source_assessments.filter(
    (source) => source.status === "used"
  ).length ?? 0;
  const landingBoundSourceCount = inputSummary?.source_assessments.filter(
    (source) => source.landing_match_tiers.length > 0
  ).length ?? 0;
  const inputReady = Boolean(
    inputSummary &&
      inputSummary.inventory_status === "available" &&
      !inputSummary.source_assessments.some(
        (source) => source.status === "stale" || source.status === "blocked"
      )
  );
  const canGenerate = Boolean(
    serviceCardId &&
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
              "Codex użyje wyłącznie exact inventory, zatwierdzonej usługi i dowodów WILQ."}
          </p>
        </div>
        <span className="rounded-md border border-line bg-surface px-3 py-2 text-xs font-semibold text-slate-600">
          {planningStatusLabel(state.status)}
        </span>
      </div>

      {currentProposal ? (
        <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(18rem,0.7fr)]">
          <div className="rounded-md border border-line bg-surface p-3">
            <p className="text-xs font-semibold uppercase text-slate-500">Kąt i intencja</p>
            <p className="mt-1 text-sm font-semibold text-ink">{currentProposal.angle}</p>
            <p className="mt-1 text-sm text-slate-700">{currentProposal.search_intent}</p>
          </div>
          <div className="rounded-md border border-line bg-surface p-3">
            <p className="text-xs font-semibold uppercase text-slate-500">Zakres</p>
            <p className="mt-1 text-sm text-slate-700">
              {currentProposal.sections.length} sekcji · {currentProposal.faq.length} FAQ · {currentProposal.cta_blocks.length} CTA
            </p>
          </div>
        </div>
      ) : null}

      {inputSummary ? (
        <div className="mt-4 grid gap-2 sm:grid-cols-3" aria-label="Gotowość danych do planu">
          <div className="rounded-md border border-line bg-surface p-3">
            <p className="text-xs font-semibold uppercase text-slate-500">Źródła użyte</p>
            <p className="mt-1 text-sm font-semibold text-ink">
              {usedSourceCount} z {inputSummary.source_assessments.length}
            </p>
          </div>
          <div className="rounded-md border border-line bg-surface p-3">
            <p className="text-xs font-semibold uppercase text-slate-500">Powiązanie landing</p>
            <p className="mt-1 text-sm font-semibold text-ink">
              {landingBoundSourceCount} {landingBoundSourceCount === 1 ? "źródło" : "źródła"}
            </p>
          </div>
          <div className="rounded-md border border-line bg-surface p-3">
            <p className="text-xs font-semibold uppercase text-slate-500">Dowody wejścia</p>
            <p className="mt-1 text-sm font-semibold text-ink">
              {inputSummary.evidence_id_count}
            </p>
          </div>
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
            ? "Codex buduje plan…"
            : state.status === "stale"
              ? "Wygeneruj aktualny plan"
              : "Wygeneruj plan"}
        </button>
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
          Input: {state.planning_input_digest ?? "brak"} · wersja: {currentProposal?.proposal_version ?? "brak"}
        </p>
        {inputSummary ? (
          <ul className="mt-3 space-y-2">
            {inputSummary.source_assessments.map((source) => (
              <li key={source.source} className="rounded-md border border-line bg-surface p-2">
                <span className="font-semibold text-ink">
                  {planningSourceLabel(source.source)}: {planningSourceStatusLabel(source.status)}
                </span>
                {source.landing_match_tiers.length ? (
                  <span> · landing {source.landing_match_tiers.map(landingTierLabel).join(", ")}</span>
                ) : null}
                <span className="block mt-1 leading-5 text-slate-600">{source.reason}</span>
              </li>
            ))}
          </ul>
        ) : null}
        <p className="mt-1">Codex nigdy nie uruchamia się przy GET ani bez gotowego inputu.</p>
      </details>
    </section>
  );
}

function planningHeadline(status: string, hasCurrentProposal: boolean) {
  if (hasCurrentProposal) return "Plan strony jest gotowy do review";
  if (status === "stale") return "Plan wymaga aktualizacji";
  if (status === "blocked") return "Plan jest zablokowany";
  if (status === "failed") return "Nie udało się zbudować planu";
  return "Zbuduj plan z aktualnych danych";
}

function planningSourceLabel(source: string) {
  const labels: Record<string, string> = {
    wordpress: "WordPress",
    service_profile: "Profil usługi",
    gsc: "GSC",
    ga4: "GA4",
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
    created: "nowy plan",
    idempotent: "ta sama wersja",
    ready: "gotowy do review",
    stale: "wejście zmienione",
    blocked: "zablokowany",
    failed: "błąd bez zapisu"
  };
  return labels[status] ?? status;
}
