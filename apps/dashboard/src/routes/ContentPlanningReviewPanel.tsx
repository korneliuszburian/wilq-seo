import { useState } from "react";

import type {
  ContentPlanningReviewConflict,
  ContentPlanningWorkspace,
  ContentWorkItemServiceCandidate
} from "../lib/api";
import type { WorkflowStepId } from "./contentWorkflowRuntime";

type PlanningStage = Extract<WorkflowStepId, "scope" | "section_map">;

export type ContentPlanningReviewPanelActions = {
  conflict: ContentPlanningReviewConflict | null;
  error: Error | null;
  pending: boolean;
  refresh: () => void;
  save: (
    stage: PlanningStage,
    decision: "approved" | "needs_changes",
    notes: string,
    checkedItems: string[],
    serviceCardId?: string
  ) => void;
};

export function ContentPlanningReviewPanel({
  actions,
  planning,
  serviceCandidates,
  stage
}: {
  actions: ContentPlanningReviewPanelActions;
  planning: ContentPlanningWorkspace;
  serviceCandidates: ContentWorkItemServiceCandidate[];
  stage: PlanningStage;
}) {
  const [decision, setDecision] = useState<"approved" | "needs_changes">("approved");
  const [notes, setNotes] = useState("");
  const [checked, setChecked] = useState(false);
  const proposal = planning.proposal;
  const [selectedServiceCardId, setSelectedServiceCardId] = useState(
    proposal.service_selection_confirmed ? proposal.service_card_id ?? "" : ""
  );
  const selectedService = serviceCandidates.find(
    (candidate) => candidate.service_card_id === selectedServiceCardId
  );
  const latestDecision = stage === "scope" ? planning.scope_decision : planning.section_map_decision;
  const inventoryMapping = planning.proposal.inventory_mapping ?? [];
  const documentScopeSummary = planningScopeSummary(proposal.sections);
  const canSubmit =
    !actions.pending &&
    (decision === "approved" ? checked : notes.trim().length > 0) &&
    (stage !== "scope" || Boolean(selectedServiceCardId));

  return (
    <section
      aria-labelledby="planning-review-title"
      className="rounded-md border border-line bg-white p-4 shadow-sm"
      data-testid={`planning-review-${stage}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            {stage === "scope" ? "Krok 1 z 5" : "Krok 2 z 5"}
          </p>
          <h2 id="planning-review-title" className="mt-1 text-lg font-semibold text-ink">
            {stage === "scope" ? "Zatwierdź zakres treści" : "Zatwierdź plan sekcji"}
          </h2>
        </div>
        {latestDecision ? (
          <span className="rounded-md border border-line bg-surface px-3 py-2 text-xs font-semibold text-slate-600">
            Ostatnia decyzja: {latestDecision.decision === "approved" ? "zaakceptowano" : "do zmiany"}
          </span>
        ) : null}
      </div>

      {stage === "scope" ? (
        <>
          <label className="mt-4 block max-w-xl text-sm font-semibold text-ink">
            Potwierdzona usługa
            <select
              aria-label="Potwierdzona usługa"
              value={selectedServiceCardId}
              onChange={(event) => setSelectedServiceCardId(event.target.value)}
              className="mt-2 h-11 w-full rounded-md border border-line bg-white px-3 font-normal"
            >
              <option value="">Wybierz usługę do tego adresu</option>
              {serviceCandidates.map((candidate) => (
                <option key={candidate.service_card_id} value={candidate.service_card_id}>
                  {candidate.service_label} · {candidate.lifecycle_label}
                  {candidate.recommended ? " · rekomendowana" : " · wybór wymaga review"}
                </option>
              ))}
            </select>
          </label>
          {selectedService ? (
            <p className="mt-2 text-xs leading-5 text-slate-600">
              {selectedService.match_reasons.join(" ")}
            </p>
          ) : null}
          <dl className="mt-4 grid gap-3 sm:grid-cols-2">
            <PlanningFact label="Strona" value={proposal.final_canonical_url} />
            <PlanningFact
              label={proposal.service_selection_confirmed ? "Usługa wybrana" : "Dopasowanie robocze"}
              value={proposal.service_label ?? "Brak dopasowanej usługi"}
            />
            <PlanningFact label="Intencja" value={proposal.search_intent} />
            <PlanningFact label="Odbiorca" value={proposal.target_reader} />
            <PlanningFact label="Problem" value={proposal.buyer_problem} />
            <PlanningFact label="Moment decyzji" value={proposal.buyer_trigger} />
            <PlanningFact label="CTA" value={proposal.cta_direction} />
            <PlanningFact
              label="Linkowanie wewnętrzne"
              value={proposal.internal_link_directions.join(" · ") || "Brak kierunku linkowania"}
            />
          </dl>
          <p
            className="mt-4 rounded-md border border-line bg-surface px-3 py-2 text-xs leading-5 text-slate-600"
            data-testid="planning-source-summary"
          >
            {planningSourceSummary(proposal)}
          </p>
          <SearchDemandSummary demand={proposal.search_demand} />
        </>
      ) : (
        <>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">
          WILQ automatycznie przypisał istniejące sekcje ACF lub treści głównej do planu.
          Sprawdź tylko decyzję redakcyjną i elementy oznaczone jako niejednoznaczne.
        </p>
        {!inventoryMapping.length && planning.proposal.generation_status === "codex_generated" ? (
          <div className="mt-4 rounded-md border border-wait/30 bg-wait/10 p-3 text-sm leading-6 text-slate-700" data-testid="planning-legacy-mapping-notice">
            Ten plan powstał przed pełną mapą istniejącej strony. Wygeneruj świeżą wersję, aby WILQ pokazał decyzję dla każdej sekcji ACF lub treści głównej.
          </div>
        ) : null}
        {inventoryMapping.length ? (
          <div className="mt-4 rounded-md border border-line bg-surface p-3" data-testid="planning-inventory-mapping">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h3 className="text-sm font-semibold text-ink">Pokrycie istniejącej strony</h3>
              <span className="text-xs text-slate-500">
                {inventoryMapping.filter((item) => item.status === "mapped" || item.status === "excluded").length}/
                {inventoryMapping.length} sekcji obsłużonych automatycznie
              </span>
            </div>
            <ul className="mt-2 grid gap-2 md:grid-cols-2">
              {inventoryMapping.map((item) => (
                <li key={item.inventory_section_id} className="rounded border border-line bg-white px-3 py-2 text-xs">
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-medium text-ink">{item.inventory_heading}</span>
                    <span className={item.status === "mapped" ? "font-semibold text-action" : "font-semibold text-wait"}>
                {item.status === "mapped" ? "przypisana" : item.status === "ambiguous" ? "niejednoznaczna" : item.status === "excluded" ? "pominięta do review" : "do sprawdzenia"}
                    </span>
                  </div>
                  {item.mapped_section_heading ? <div className="mt-1 text-slate-500">→ {item.mapped_section_heading} · {item.disposition ?? "bez decyzji"}</div> : null}
                  {item.reason ? <div className="mt-1 text-slate-500">{item.reason === "dated_or_event_inventory" ? "Element datowany lub wydarzenie — nie jest strukturą odpowiedzi." : item.reason === "navigation_or_promotional_inventory" ? "Element nawigacyjny/promocyjny — wymaga osobnego review." : item.reason}</div> : null}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        <p
          className="mt-4 rounded-md border border-action/20 bg-action/5 px-3 py-2 text-sm text-slate-700"
          data-testid="planning-document-scope-summary"
        >
          {documentScopeSummary}
        </p>
        <ol className="mt-4 space-y-3">
          {proposal.sections.map((section, index) => (
            <li key={`${index}-${section.heading}`} className="rounded-md border border-line bg-surface p-3">
              <div className="flex items-start gap-3">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-action text-xs font-bold text-white">
                  {index + 1}
                </span>
                <div className="min-w-0">
                  <h3 className="text-sm font-semibold text-ink">{section.heading}</h3>
                  <div className="mt-2 flex flex-wrap gap-1.5 text-xs">
                    <span className="rounded-full border border-action/30 bg-action/5 px-2 py-1 font-semibold text-action">
                      {inventoryDispositionLabel(section.inventory_disposition)}
                    </span>
                    {section.inventory_heading && section.inventory_heading !== section.heading ? (
                      <span className="rounded-full border border-line bg-white px-2 py-1 text-slate-600">
                        obecna sekcja: {section.inventory_heading}
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-1 text-sm leading-6 text-slate-700">{section.purpose}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    {section.evidence_ids.length} {section.evidence_ids.length === 1 ? "dowód" : "dowodów"}
                  </p>
                  <SectionDemandTerms
                    queryTerms={section.query_terms}
                    rows={proposal.search_demand.gsc_query_rows}
                  />
                </div>
              </div>
            </li>
          ))}
        </ol>
        </>
      )}

      <div className="mt-5 grid gap-3 md:grid-cols-[220px_minmax(0,1fr)]">
        <label className="text-sm font-semibold text-ink">
          Decyzja
          <select
            aria-label="Decyzja planistyczna"
            value={decision}
            onChange={(event) => setDecision(event.target.value as typeof decision)}
            className="mt-2 h-11 w-full rounded-md border border-line bg-white px-3 text-sm font-normal"
          >
            <option value="approved">Akceptuję ten krok</option>
            <option value="needs_changes">Wymaga zmian</option>
          </select>
        </label>
        <label className="text-sm font-semibold text-ink">
          Notatka
          <textarea
            aria-label="Notatka do planu"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            placeholder="Co zaakceptowano albo co trzeba poprawić?"
            className="mt-2 min-h-20 w-full rounded-md border border-line bg-white p-3 text-sm font-normal leading-6"
          />
        </label>
      </div>

      {decision === "approved" ? (
        <label className="mt-3 flex items-start gap-2 text-sm leading-6 text-slate-700">
          <input
            type="checkbox"
            checked={checked}
            onChange={(event) => setChecked(event.target.checked)}
            className="mt-1"
          />
          {stage === "scope"
            ? "Sprawdziłem stronę, usługę, intencję, odbiorcę i CTA."
            : "Sprawdziłem kolejność, cel i dowody każdej sekcji."}
        </label>
      ) : null}

      <button
        type="button"
        disabled={!canSubmit}
        onClick={() =>
          actions.save(
            stage,
            decision,
            notes,
            checked ? [stage === "scope" ? "zakres i CTA" : "kolejność, cel i dowody"] : [],
            stage === "scope" ? selectedServiceCardId : undefined
          )
        }
        className="mt-4 inline-flex h-11 items-center rounded-md bg-action px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
      >
        {actions.pending
          ? "Zapisuję decyzję..."
          : decision === "approved"
            ? "Zapisz decyzję i przejdź dalej"
            : "Zapisz uwagi do poprawy"}
      </button>

      {actions.conflict ? (
        <div role="alert" className="mt-3 rounded-md border border-wait/30 bg-wait/10 p-3 text-sm leading-6 text-slate-700">
          <p className="font-semibold text-wait">Plan zmienił się na serwerze</p>
          <p className="mt-1">Twoja notatka pozostała w formularzu. {actions.conflict.detail}</p>
          <button type="button" onClick={actions.refresh} className="mt-2 font-semibold text-action underline">
            Odśwież aktualny plan
          </button>
        </div>
      ) : null}
      {actions.error ? (
        <p role="alert" className="mt-3 rounded-md border border-danger/30 bg-danger/10 p-3 text-sm text-danger">
          Nie udało się zapisać decyzji. WILQ nie zmienił planu.
        </p>
      ) : null}
    </section>
  );
}

export function inventoryDispositionLabel(
  disposition: ContentPlanningWorkspace["proposal"]["sections"][number]["inventory_disposition"]
) {
  return {
    preserve: "zachowaj",
    merge: "scal po review",
    rewrite: "przepisz",
    remove_review_required: "usuń po review",
    create: "utwórz"
  }[disposition];
}

export function planningScopeSummary(
  sections: Array<{ inventory_disposition: string }>
) {
  const excluded = sections.filter(
    (section) => section.inventory_disposition === "remove_review_required"
  ).length;
  const draftable = sections.length - excluded;
  const sectionLabel =
    draftable === 1
      ? "sekcja"
      : draftable >= 2 && draftable <= 4
        ? "sekcje"
        : "sekcji";
  const excludedLabel = excluded === 1 ? "element" : "elementów";
  return `${draftable} ${sectionLabel} trafi do pełnego tekstu · ${excluded} ${excludedLabel} pozostaje do osobnego review`;
}

type PlanningSourceSummaryInput = Pick<
  ContentPlanningWorkspace["proposal"],
  "evidence_ids" | "source_material_ids" | "knowledge_card_ids" | "source_connectors"
>;

export function planningSourceSummary(proposal: PlanningSourceSummaryInput): string {
  const sourceCount = proposal.evidence_ids.length;
  const materialCount = proposal.source_material_ids.length;
  const knowledgeCount = proposal.knowledge_card_ids.length;
  const connectorCount = proposal.source_connectors.length;
  return `Plan opiera się na ${sourceCount} ${sourceCount === 1 ? "źródle" : "źródłach"} · ${materialCount} ${materialCount === 1 ? "materiale" : "materiałach"} Ekologusa · ${knowledgeCount} ${knowledgeCount === 1 ? "karcie" : "kartach"} · ${connectorCount} ${connectorCount === 1 ? "połączeniu" : "połączeniach"}`;
}

function SearchDemandSummary({
  demand
}: {
  demand: ContentPlanningWorkspace["proposal"]["search_demand"];
}) {
  return (
    <div className="mt-4 rounded-md border border-line bg-surface p-3">
      <h3 className="text-sm font-semibold text-ink">Popyt z wyszukiwarki dla tej strony</h3>
      {demand.gsc_query_rows.length ? (
        <>
          <p className="mt-2 text-xs leading-5 text-slate-600">
            {demand.gsc_query_rows.length > 4
              ? `Pokazujemy 4 najwyższe z ${demand.gsc_query_rows.length} sygnałów planistycznych GSC. Metryki zakresu wyżej są sumą wszystkich tych sygnałów, nie tylko czterech widocznych wierszy.`
              : `Pokazujemy wszystkie ${demand.gsc_query_rows.length} sygnały planistyczne GSC dla tej strony.`}
          </p>
          <ul className="mt-2 grid gap-2 md:grid-cols-2">
          {demand.gsc_query_rows.slice(0, 4).map((row) => (
            <li key={`${row.page}-${row.term}`} className="rounded-md bg-white p-3 text-sm">
              <p className="font-semibold text-ink">{row.term}</p>
              <p className="mt-1 text-xs text-slate-600">
                {formatDemandMetrics(row)} · {demandPeriodLabel(row.period)} · {row.freshness === "fresh" ? "świeże" : "wymaga odświeżenia"}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                {row.section_mapping_status === "intent_relevance"
                  ? "Dopasowanie intencji do planowanej sekcji — wymaga sprawdzenia"
                  : row.section_mapping_status === "lexical_relevance"
                    ? "Starsze dopasowanie słowne — wymaga sprawdzenia"
                    : "Sygnał dla strony — bez potwierdzonej sekcji"}
              </p>
            </li>
          ))}
          </ul>
        </>
      ) : (
        <p className="mt-2 text-sm leading-6 text-slate-700">{demand.safe_next_step}</p>
      )}
      <p className="mt-2 text-xs text-slate-500">
        Ads i Keyword Planner: {demand.optional_ads_status === "exact_rows_available"
          ? "ścisłe dopasowanie dostępne"
          : demand.optional_ads_status === "blocked"
            ? "blokada kompletności albo ścisłego mapowania klikniętego landingu — nie używamy"
            : demand.optional_ads_status === "stale"
              ? "ścisłe dopasowanie jest nieaktualne — odśwież Ads przed użyciem"
            : "brak ścisłego mapowania do strony i usługi — nie używamy"}.
      </p>
      {demand.ads_term_rows.length ? (
        <p className="mt-1 text-xs text-slate-500">
          {demand.ads_term_rows.length} terminów Ads ma metryki i faktycznie kliknięty landing w tym samym 30-dniowym wierszu danych.
        </p>
      ) : null}
    </div>
  );
}

function SectionDemandTerms({
  queryTerms,
  rows
}: {
  queryTerms: string[];
  rows: ContentPlanningWorkspace["proposal"]["search_demand"]["gsc_query_rows"];
}) {
  if (!queryTerms.length) return null;
  const metricsByTerm = new Map(rows.map((row) => [row.term, formatDemandMetrics(row)]));
  const terms = queryTerms.slice(0, 6).map((term) => {
    const metrics = metricsByTerm.get(term);
    return metrics ? `${term} (${metrics})` : term;
  });
  return (
    <p className="mt-2 text-xs leading-5 text-slate-600">
      Zapytania przypisane do sekcji: {terms.join(" · ")}
    </p>
  );
}

function formatDemandMetrics(
  row: ContentPlanningWorkspace["proposal"]["search_demand"]["gsc_query_rows"][number]
) {
  const metrics = [
    row.impressions === null ? null : `${row.impressions} wyśw.`,
    row.clicks === null ? null : `${row.clicks} klik.`,
    row.ctr === null ? null : `CTR ${(row.ctr * 100).toFixed(1)}%`,
    row.average_position === null ? null : `poz. ${row.average_position.toFixed(1)}`
  ].filter(Boolean);
  return metrics.join(" · ") || "Brak metryk liczbowych";
}

function demandPeriodLabel(period: string) {
  const labels: Record<string, string> = {
    connector_refresh: "ostatni odczyt",
    last_28_days: "ostatnie 28 dni",
    search_term_safety_90d: "ostatnie 90 dni",
    keyword_planner: "Keyword Planner"
  };
  return labels[period] ?? "okres ze źródła";
}

function PlanningFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-line bg-surface p-3">
      <dt className="text-xs font-semibold uppercase tracking-normal text-slate-500">{label}</dt>
      <dd className="mt-1 break-words text-sm leading-6 text-ink">{value}</dd>
    </div>
  );
}
