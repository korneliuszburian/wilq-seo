import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import {
  createContentNewPageBrief,
  getContentNewPageBriefWorkspace,
  getContentNewPageTopicRecommendations,
  type ContentNewPageBriefInput,
  type ContentNewPageBriefWorkspace,
  type ContentNewPageTopicCandidate,
  type ContentNewPageTopicRecommendations
} from "../../lib/api";
import { NewPageTextFoundation } from "./Flows";
import {
  BriefField,
  EvidenceIds,
  InfoTile,
  NewPageShell,
  overlapEmptyStateCopy,
  overlapMatchLabel
} from "./Shared";

export function ContentWorkflowNewPageBrief({ briefId, onReturn, onSaved }: { briefId: string | null; onReturn: () => void; onSaved: (briefId: string) => void }) {
  const savedBrief = useQuery({
    queryKey: ["content-workflow", "new-page-brief", briefId],
    queryFn: () => getContentNewPageBriefWorkspace(briefId ?? ""),
    enabled: Boolean(briefId),
    staleTime: 30_000
  });
  const [form, setForm] = useState<ContentNewPageBriefInput>({
    title: "", purpose: "", service: "", audience: "", search_intent: "", proposed_ia_location: ""
  });
  const topicRecommendations = useQuery({
    queryKey: ["content-workflow", "new-page-topics"],
    queryFn: getContentNewPageTopicRecommendations,
    enabled: !briefId,
    staleTime: 30_000
  });
  const saveBrief = useMutation({
    mutationFn: createContentNewPageBrief,
    onSuccess: (workspace) => onSaved(workspace.brief.brief_id)
  });
  const workspace = savedBrief.data;
  if (briefId && savedBrief.isLoading) return <NewPageShell onReturn={onReturn}><p className="text-sm text-slate-600">Wczytuję zapisany brief…</p></NewPageShell>;
  if (briefId && (savedBrief.error || !workspace)) return <NewPageShell onReturn={onReturn}><p className="rounded-xl border border-wait/30 bg-white px-4 py-3 text-sm text-ink">Nie udało się odczytać briefu. Wróć do wyboru i spróbuj ponownie.</p></NewPageShell>;
  if (workspace) return <NewPageSaved workspace={workspace} onReturn={onReturn} />;
  return <NewPageShell onReturn={onReturn}>
    <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-emerald-700">Nowa strona</p>
    <h1 className="mt-3 text-3xl font-semibold tracking-tight text-ink">Zacznij od briefu nowej strony</h1>
    <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-700">Nie potrzebujesz starego adresu ani miejsca w WordPressie. Opisz planowaną stronę, a WILQ sprawdzi jej pokrycie w aktualnym serwisie.</p>
    <NewPageTopicSeeds
      recommendations={topicRecommendations.data ?? null}
      loading={topicRecommendations.isLoading}
      error={topicRecommendations.isError}
      selectedCandidateId={form.topic_candidate_id ?? null}
      onChoose={(candidate) => setForm({
        ...form,
        title: candidate.title,
        topic_candidate_id: candidate.candidate_id,
        topic_candidate_digest: candidate.candidate_digest
      })}
      onClear={() => setForm({
        ...form,
        topic_candidate_id: undefined,
        topic_candidate_digest: undefined
      })}
    />
    <form className="mt-7 grid gap-4" onSubmit={(event) => { event.preventDefault(); saveBrief.mutate(form); }}>
      <BriefField label="Roboczy tytuł strony" value={form.title} onChange={(title) => setForm({ ...form, title, topic_candidate_id: undefined, topic_candidate_digest: undefined })} placeholder="np. Audyt środowiskowy dla inwestycji" />
      <BriefField label="Cel strony" value={form.purpose} onChange={(purpose) => setForm({ ...form, purpose })} placeholder="Co ta strona ma pomóc odbiorcy zrozumieć lub zrobić?" multiline />
      <div className="grid gap-4 md:grid-cols-2"><BriefField label="Obszar tematu" value={form.service} onChange={(service) => setForm({ ...form, service })} placeholder="np. Dokumentacja środowiskowa" /><BriefField label="Odbiorca" value={form.audience} onChange={(audience) => setForm({ ...form, audience })} placeholder="np. Inwestor planujący przedsięwzięcie" /></div>
      <div className="grid gap-4 md:grid-cols-2"><BriefField label="Intencja wyszukiwania" value={form.search_intent} onChange={(search_intent) => setForm({ ...form, search_intent })} placeholder="Jakiego problemu szuka odbiorca?" /><BriefField label="Miejsce w serwisie" value={form.proposed_ia_location} onChange={(proposed_ia_location) => setForm({ ...form, proposed_ia_location })} placeholder="np. Usługi → Dokumentacja środowiskowa" /></div>
      {saveBrief.error ? <p className="text-sm text-wait">Nie udało się zapisać briefu. Uzupełnij wymagane pola i spróbuj ponownie.</p> : null}
      <div className="flex flex-wrap items-center gap-3"><button type="submit" disabled={saveBrief.isPending} className="rounded-xl bg-action px-5 py-3 text-sm font-semibold text-white disabled:opacity-60">{saveBrief.isPending ? "Zapisuję brief…" : "Zapisz brief i sprawdź pokrycie"}</button><p className="text-xs leading-5 text-slate-600">To nie tworzy dokumentu, rewizji ani niczego w WordPressie.</p></div>
    </form>
  </NewPageShell>;
}

function NewPageTopicSeeds({
  recommendations,
  loading,
  error,
  selectedCandidateId,
  onChoose,
  onClear
}: {
  recommendations: ContentNewPageTopicRecommendations | null;
  loading: boolean;
  error: boolean;
  selectedCandidateId: string | null;
  onChoose: (candidate: ContentNewPageTopicCandidate) => void;
  onClear: () => void;
}) {
  if (loading) {
    return <section className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">Sprawdzam, czy dane wskazują temat dla nowej strony…</section>;
  }
  if (error || !recommendations) {
    return <section className="mt-6 rounded-2xl border border-wait/30 bg-wait/5 p-4 text-sm leading-6 text-ink">Nie udało się odczytać rekomendacji tematów. Możesz nadal opisać własny temat — przed zapisem WILQ sprawdzi pokrycie serwisu.</section>;
  }
  if (recommendations.status !== "ready") {
    return <section className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-ink" data-testid="new-page-topic-recommendations-empty"><p className="font-semibold">{recommendations.title}</p><p className="mt-1 text-slate-700">{recommendations.reason}</p><p className="mt-2 text-slate-600">{recommendations.safe_next_step}</p></section>;
  }
  return (
    <section className="mt-6 rounded-2xl border border-emerald-200 bg-emerald-50/50 p-4" data-testid="new-page-topic-recommendations">
      <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-emerald-800">Tematy z danych</p>
      <h2 className="mt-2 text-lg font-semibold text-ink">{recommendations.title}</h2>
      <p className="mt-1 text-sm leading-6 text-slate-700">{recommendations.reason}</p>
      <div className="mt-4 grid gap-3">
        {recommendations.candidates.map((candidate) => (
          <article key={candidate.candidate_id} className="rounded-xl border border-emerald-200 bg-white p-4">
            <h3 className="font-semibold text-ink">{candidate.title}</h3>
            <p className="mt-1 text-sm leading-6 text-slate-700">{candidate.rationale}</p>
            <EvidenceIds evidenceIds={candidate.evidence_ids} label="Dowody tematu" />
            <button type="button" className="mt-3 text-sm font-semibold text-action" onClick={() => onChoose(candidate)}>
              {selectedCandidateId === candidate.candidate_id ? "Wybrany temat" : "Użyj tego tematu"}
            </button>
          </article>
        ))}
      </div>
      {selectedCandidateId ? <button type="button" className="mt-3 text-sm font-semibold text-slate-700 underline" onClick={onClear}>Wpisz własny temat</button> : null}
    </section>
  );
}

function NewPageSaved({ workspace, onReturn }: { workspace: ContentNewPageBriefWorkspace; onReturn: () => void }) {
  const guard = workspace.overlap_guard;
  return <NewPageShell onReturn={onReturn}>
    <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-emerald-700">Brief nowej strony</p>
    <h1 className="mt-3 text-3xl font-semibold tracking-tight text-ink">{workspace.brief.title}</h1>
    <p className="mt-3 text-sm leading-7 text-slate-700">Brief jest zapisany. To zarys nowej strony, nie dokument do publikacji ani układ WordPressa.</p>
    <dl className="mt-6 grid gap-3 sm:grid-cols-2"><InfoTile label="Cel" value={workspace.brief.purpose} /><InfoTile label="Obszar tematu" value={workspace.brief.service} /><InfoTile label="Odbiorca" value={workspace.brief.audience} /><InfoTile label="Intencja wyszukiwania" value={workspace.brief.search_intent} /><InfoTile label="Miejsce w serwisie" value={workspace.brief.proposed_ia_location} /></dl>
    <section className="mt-7 rounded-2xl border border-emerald-200 bg-emerald-50/60 p-5"><p className="text-[11px] font-bold uppercase tracking-[0.14em] text-emerald-800">Pokrycie istniejących treści</p><h2 className="mt-2 text-xl font-semibold text-ink">{guard.label}</h2><p className="mt-2 text-sm leading-6 text-slate-700">{guard.reason}</p><details className="mt-4 rounded-xl border border-emerald-200 bg-white px-3 py-2"><summary className="cursor-pointer text-sm font-semibold text-ink">Sprawdzone strony i dowody</summary>{guard.candidates.length ? <ul className="mt-3 space-y-3">{guard.candidates.map((candidate) => <li key={`${candidate.url}-${candidate.match_kind}`} className="border-t border-slate-100 pt-3 text-sm first:border-t-0 first:pt-0"><span className="font-semibold text-ink">{candidate.title}</span><span className="mt-1 block text-xs text-slate-600">{candidate.url}</span><span className="mt-2 block text-xs text-slate-700">{overlapMatchLabel(candidate.match_kind)}</span><EvidenceIds evidenceIds={candidate.evidence_ids} /></li>)}</ul> : <p className="mt-3 text-sm leading-6 text-slate-700">{overlapEmptyStateCopy(guard.disposition)}</p>}<EvidenceIds evidenceIds={guard.evidence_ids} label="Dowody sprawdzonego katalogu" /></details><p className="mt-4 text-xs leading-5 text-slate-600">{guard.caveat}</p></section>
    <NewPageTextFoundation workspace={workspace} />
  </NewPageShell>;
}
