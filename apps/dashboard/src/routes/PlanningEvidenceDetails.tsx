import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getContentRegulatorySourceFactProposal,
  postContentRegulatorySourceFactProposal,
  postContentRegulatorySourceFactProposalReview,
  type ContentDocumentWorkspace,
  type ContentPlanningProposalResponse
} from "../lib/api";

export function PlanningEvidenceDetails({
  input,
  proposal
}: {
  input: NonNullable<ContentPlanningProposalResponse["input_summary"]>;
  proposal: ContentPlanningProposalResponse["proposal"];
}) {
  const queryClient = useQueryClient();
  const queries = proposal?.search_demand?.gsc_query_rows ?? input.gsc_query_rows ?? [];
  const regulatoryReviewCandidates = input.regulatory_review_candidates ?? [];
  const metricComparisons = input.metric_comparisons ?? [];
  const hasPlan = Boolean(proposal);
  const isNewPage = input.goal === "new_page";

  return <details className="mt-4 rounded-md border border-line bg-slate-50 p-3 text-sm text-slate-700" data-testid="content-planning-evidence">
    <summary className="cursor-pointer font-semibold text-ink">Na jakich danych oprze się tekst</summary>
    <p className="mt-2 leading-6">WILQ użyje tylko źródeł dokładnie przypisanych do {hasPlan ? "tego planu" : "tych danych wejściowych"}. Brakujące dane nie są zastępowane domysłami.</p>
    <div className="mt-3 grid gap-3 sm:grid-cols-3">
      <EvidenceCount label="Materiały źródłowe" value={input.source_material_ids.length} />
      <EvidenceCount label="Karty wiedzy" value={input.knowledge_card_count} />
      <EvidenceCount label="Dowody" value={input.evidence_id_count} />
    </div>
    {input.source_assessments.length ? <ul className="mt-3 space-y-2 text-slate-600">{input.source_assessments.map((source) => <li key={source.source}><span className="font-semibold text-ink">{planningSourceLabel(source.source)}: </span>{planningSourceStatusCopy(source.status)}{source.reason ? ` ${source.reason}` : ""}</li>)}</ul> : null}
    <RegulatorySourceReviewCandidates
      candidates={regulatoryReviewCandidates}
      onRecorded={() => void queryClient.invalidateQueries({ queryKey: ["content-workflow"] })}
      title="Źródła urzędowe do sprawdzenia przed przygotowaniem treści"
    />
    {!isNewPage && metricComparisons.length ? <MeasurementComparisonDetails comparisons={metricComparisons} /> : null}
    {isNewPage ? <p className="mt-3 leading-6">Nowa strona nie ma własnej historii GSC. WILQ nie pokazuje tu historycznych zapytań ani metryk.</p> : queries.length ? <div className="mt-3"><p className="font-semibold text-ink">Zapytania GSC przypisane do tej strony</p><ul className="mt-2 space-y-1">{queries.slice(0, 6).map((query) => <li key={`${query.term}-${query.period}`} className="rounded bg-white px-2 py-1">{query.term} · okres: {query.period}{query.impressions !== null ? ` · ${query.impressions} wyświetleń` : ""}{query.clicks !== null ? ` · ${query.clicks} kliknięć` : ""}</li>)}</ul>{queries.length > 6 ? <p className="mt-2 text-xs text-slate-600">Pokazano 6 z {queries.length} exact zapytań GSC.</p> : null}</div> : <p className="mt-3 leading-6">Brak exact zapytań GSC {hasPlan ? "w aktualnym planie" : "w danych wejściowych"} — WILQ nie pokazuje zastępczej listy słów kluczowych.</p>}
  </details>;
}

type PlanningMetricComparison = NonNullable<NonNullable<ContentPlanningProposalResponse["input_summary"]>["metric_comparisons"]>[number];

function MeasurementComparisonDetails({ comparisons }: { comparisons: PlanningMetricComparison[] }) {
  return <section className="mt-3 rounded border border-line bg-white p-3" data-testid="content-planning-measurement-comparisons">
    <p className="font-semibold text-ink">Porównanie okresów tej strony</p>
    <p className="mt-1 leading-6">WILQ pokazuje porównanie tylko wtedy, gdy oba okresy są dokładnie powiązane z tą stroną i ich dowodami.</p>
    <ul className="mt-3 space-y-3">
      {comparisons.map((comparison) => <li key={comparison.source_connector}>
        {hasExactComparisonValues(comparison) ? <ExactMeasurementComparison comparison={comparison} /> : <UnavailableMeasurementComparison comparison={comparison} />}
      </li>)}
    </ul>
  </section>;
}

function ExactMeasurementComparison({ comparison }: { comparison: PlanningMetricComparison }) {
  return <div className="rounded bg-slate-50 p-3">
    <p className="font-semibold text-ink">{measurementConnectorLabel(comparison.source_connector)}</p>
    <p className="mt-1 text-slate-600">Dokładne okresy: {comparison.baseline_period} → {comparison.comparison_period}</p>
    <ul className="mt-2 space-y-1">
      {comparison.metric_names.map((metricName) => <li key={metricName}>{measurementMetricLabel(metricName)}: {formatMeasurementValue(comparison.baseline_values[metricName]!)} → {formatMeasurementValue(comparison.comparison_values[metricName]!)}</li>)}
    </ul>
  </div>;
}

function UnavailableMeasurementComparison({ comparison }: { comparison: PlanningMetricComparison }) {
  return <div className="rounded bg-slate-50 p-3">
    <p className="font-semibold text-ink">{measurementConnectorLabel(comparison.source_connector)}: brak bezpiecznego porównania</p>
    <p className="mt-1 leading-6 text-slate-600">{comparison.reason}</p>
  </div>;
}

function hasExactComparisonValues(comparison: PlanningMetricComparison) {
  return comparison.status === "available"
    && Boolean(comparison.baseline_period?.trim())
    && Boolean(comparison.comparison_period?.trim())
    && comparison.metric_names.length > 0
    && comparison.metric_names.every((name) => (
      typeof comparison.baseline_values[name] === "number"
      && typeof comparison.comparison_values[name] === "number"
    ));
}

function measurementConnectorLabel(connector: PlanningMetricComparison["source_connector"]) {
  return connector === "google_search_console" ? "Google Search Console" : "Google Analytics 4";
}

function measurementMetricLabel(metric: string) {
  return {
    clicks: "Kliknięcia",
    impressions: "Wyświetlenia",
    ctr: "CTR",
    average_position: "Średnia pozycja",
    sessions: "Sesje",
    engaged_sessions: "Zaangażowane sesje",
    engagement_rate: "Współczynnik zaangażowania",
    key_events: "Kluczowe zdarzenia"
  }[metric] ?? metric;
}

function formatMeasurementValue(value: number) {
  return new Intl.NumberFormat("pl-PL", { maximumFractionDigits: 2 }).format(value);
}

type RegulatoryReviewCandidate = ContentDocumentWorkspace["regulatory_review_candidates"][number];

export function RegulatorySourceReviewCandidates({
  candidates,
  onRecorded,
  title = "Źródła urzędowe do sprawdzenia"
}: {
  candidates: RegulatoryReviewCandidate[];
  onRecorded: () => void;
  title?: string;
}) {
  if (!candidates.length) return null;
  return <div className="mt-3 rounded border border-wait/30 bg-wait/5 p-3" data-testid="content-regulatory-source-review">
    <p className="font-semibold text-ink">{title}</p>
    <p className="mt-1 leading-6">Te materiały nie są jeszcze dowodem w planie ani podstawą twierdzeń. Sprawdź materiał, zapisz dokładny fakt człowieka i dopiero wtedy WILQ odświeży gotowość.</p>
    <ul className="mt-2 space-y-3">{candidates.map((candidate) => <li key={candidate.candidate_id}><RegulatorySourceReviewCandidate candidate={candidate} onRecorded={onRecorded} /></li>)}</ul>
  </div>;
}

function RegulatorySourceReviewCandidate({
  candidate,
  onRecorded
}: {
  candidate: RegulatoryReviewCandidate;
  onRecorded: () => void;
}) {
  const [message, setMessage] = useState<string | null>(null);
  const existingProposal = useQuery({
    queryKey: ["content-workflow", "regulatory-source", candidate.candidate_id, "fact-proposal"],
    queryFn: () => getContentRegulatorySourceFactProposal(candidate.candidate_id),
  });
  const capture = useMutation({
    mutationFn: () => postContentRegulatorySourceFactProposal(candidate.candidate_id),
    onSuccess: async (result) => {
      await existingProposal.refetch();
      setMessage(result.status === "ready" ? null : result.reason);
    }
  });
  const record = useMutation({
    mutationFn: (decision: "accepted" | "rejected") => {
      const proposalResult = existingProposal.data;
      const proposal = proposalResult?.proposal;
      if (proposalResult?.status !== "ready" || !proposal) {
        throw new Error("Brakuje aktualnej propozycji factu.");
      }
      return postContentRegulatorySourceFactProposalReview(proposal.proposal_id, {
        expected_source_snapshot_id: proposal.source_snapshot_id,
        expected_source_snapshot_digest: proposal.source_snapshot_digest,
        decision,
        reviewer: "Wilku"
      });
    },
    onSuccess: (result) => {
      if ("code" in result) {
        setMessage(result.reason);
        return;
      }
      setMessage(
        result.decision === "accepted"
          ? "Zapisano review źródła. WILQ odświeża gotowość tekstu."
          : "Zapisano odrzucenie źródła. Nie weszło ono do planu."
      );
      onRecorded();
    },
    onError: () => setMessage("Nie udało się zapisać review. Nic nie zostało promowane do planu.")
  });
  const proposal = existingProposal.data?.status === "ready" ? existingProposal.data.proposal : null;

  return <div className="rounded bg-white p-3"><p><a className="font-medium text-action underline" href={candidate.source_url} target="_blank" rel="noreferrer">{candidate.source_title}</a><span> · {candidate.requirement_labels.join(", ")} · odczyt kandydacki: {candidate.observed_on}</span></p><p className="mt-1 text-xs leading-5 text-slate-600">{candidate.safe_next_step}</p>{!proposal ? <button type="button" className="mt-2 rounded border border-action/30 px-3 py-1.5 text-xs font-semibold text-action disabled:opacity-60" disabled={capture.isPending} onClick={() => capture.mutate()}>{capture.isPending ? "Przygotowuję propozycję…" : "Przygotuj propozycję do review"}</button> : <div className="mt-2 rounded border border-line bg-slate-50 p-2"><p className="text-xs text-slate-600">Snapshot: {proposal.observed_on} · SHA-256: {proposal.source_snapshot_digest.slice(0, 12)}…</p><p className="mt-2 text-sm leading-6">{proposal.proposed_fact}</p><p className="mt-2 text-xs text-slate-600">To propozycja WILQ, nie zatwierdzony dowód. Porównaj ją z materiałem urzędowym przed decyzją.</p><div className="mt-2 flex flex-wrap gap-2"><button type="button" className="rounded bg-action px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-60" disabled={record.isPending} onClick={() => record.mutate("accepted")}>Przyjmij propozycję po review</button><button type="button" className="rounded border border-line px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:opacity-60" disabled={record.isPending} onClick={() => record.mutate("rejected")}>Odrzuć po review</button></div></div>}{message ? <p className="mt-2 text-xs leading-5 text-slate-700">{message}</p> : null}</div>;
}

function planningSourceStatusCopy(status: string) {
  if (status === "used") return "Wykorzystane.";
  if (status === "missing") return "Brak danych.";
  if (status === "stale") return "Dane wymagają odświeżenia.";
  if (status === "blocked") return "Źródło jest zablokowane.";
  if (status === "not_applicable") return "To źródło nie dotyczy tej pracy.";
  return "Źródło nie zostało użyte.";
}

function EvidenceCount({ label, value }: { label: string; value: number }) {
  return <div className="rounded bg-white px-3 py-2"><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p><p className="mt-1 font-semibold text-ink">{value}</p></div>;
}

function planningSourceLabel(source: string) {
  return {
    wordpress: "materiał strony",
    service_profile: "kontekst usługi",
    gsc: "Google Search Console",
    ga4: "Google Analytics 4",
    google_ads: "Google Ads",
    ahrefs: "Ahrefs",
    keyword_planner: "Keyword Planner",
    merchant: "Merchant Center",
    localo: "Localo",
    social: "media społecznościowe",
    knowledge: "baza wiedzy"
  }[source] ?? source;
}
