import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

import {
  getContentBriefProposal,
  getContentRequestWorkflow,
  getContentResearchRead
} from "../../lib/api";
import { IntakeBriefReadout } from "./IntakeBriefReadout";

const workflowStepLabels = {
  intake_accepted: "Przyjęta prośba",
  research_read: "Odczyt dowodów",
  human_review: "Decyzja człowieka",
  brief_ready: "Brief gotowy",
  failed: "Niepowodzenie"
};

const workflowStatusLabels = {
  in_progress: "W toku",
  blocked: "Zablokowane",
  ready_for_brief: "Gotowe do briefu",
  failed: "Niepowodzenie"
};

const researchStatusLabels = {
  ready: "Dowody gotowe",
  blocked: "Dowody zablokowane"
};

export function IntakeJourneyReadout({ queueId }: { queueId: string }) {
  const queryClient = useQueryClient();
  const workflow = useQuery({
    queryKey: ["content-intake", "journey", queueId, "workflow"],
    queryFn: () => getContentRequestWorkflow(queueId)
  });
  const research = useQuery({
    queryKey: ["content-intake", "journey", queueId, "research"],
    queryFn: () => getContentResearchRead(queueId)
  });

  useEffect(() => {
    void queryClient.prefetchQuery({
      queryKey: ["content-intake", "journey", queueId, "brief"],
      queryFn: () => getContentBriefProposal(queueId)
    });
  }, [queryClient, queueId]);

  if (workflow.isLoading || research.isLoading) {
    return <section className="mt-5 rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-600" aria-label="Odczytywanie przebiegu pracy">
      <p>Odczytuję przebieg pracy i dowody dla tej prośby…</p>
    </section>;
  }

  if (workflow.isError || research.isError || !workflow.data || !research.data) {
    return <section className="mt-5 rounded-xl border border-wait/30 bg-wait/5 p-4 text-sm text-ink" aria-label="Błąd odczytu przebiegu pracy">
      <p className="leading-6">Nie udało się odczytać przebiegu pracy i dowodów. Odśwież widok — prośba ani jej źródła nie zostały przez to zmienione.</p>
    </section>;
  }

  const workflowData = workflow.data;
  const researchData = research.data;
  const evidenceIds = [...new Set([
    ...workflowData.evidence_ids,
    ...workflowData.gates.flatMap((gate) => gate.evidence_ids),
    ...researchData.blocked_sources.flatMap((source) => source.evidence_ids),
    ...researchData.facts.flatMap((fact) => fact.evidence_ids)
  ])];

  return <section className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700" aria-labelledby="content-intake-journey-heading">
    <div className="flex flex-wrap items-baseline justify-between gap-2">
      <h2 id="content-intake-journey-heading" className="text-lg font-semibold text-ink">Przebieg pracy</h2>
      <p className="font-semibold text-action">{workflowStepLabels[workflowData.current_step]}</p>
    </div>
    <p className="mt-2 font-semibold text-ink">{workflowStatusLabels[workflowData.status]}</p>
    <p className="mt-3 leading-6"><span className="font-semibold text-ink">Następny bezpieczny krok:</span> {workflowData.safe_next_step}</p>
    {workflowData.blocker_code ? <p className="mt-3 rounded-lg border border-wait/30 bg-white px-3 py-2 leading-5 text-wait"><span className="font-semibold">{workflowData.blocker_code}</span>{workflowData.blocker_owner ? <span className="ml-2">Odpowiedzialny: {workflowData.blocker_owner}</span> : null}</p> : null}

    {workflowData.gates.length ? <section className="mt-4" aria-labelledby="content-intake-journey-gates-heading">
      <h3 id="content-intake-journey-gates-heading" className="font-semibold text-ink">Bramki</h3>
      <ul className="mt-2 grid gap-2">
        {workflowData.gates.map((gate) => <li key={gate.code} className="rounded-lg border border-slate-200 bg-white px-3 py-2 leading-5">
          <p className="font-semibold text-ink">{gate.code} · {gate.status} · {gate.owner}</p>
          <p className="mt-1 text-slate-600">{gate.safe_next_step}</p>
        </li>)}
      </ul>
    </section> : null}

    <p className="mt-4 text-xs leading-5 text-slate-600">Dowody: {evidenceIds.join(", ")}</p>

    <section className="mt-5 border-t border-slate-200 pt-4" aria-labelledby="content-intake-research-heading">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 id="content-intake-research-heading" className="font-semibold text-ink">Źródła i dowody</h3>
        <p className="font-semibold text-action">{researchStatusLabels[researchData.status]}</p>
      </div>

      {researchData.facts.length ? <ul className="mt-3 grid gap-2">
        {researchData.facts.map((fact) => <li key={fact.source_fact_id} className="rounded-lg border border-slate-200 bg-white px-3 py-2 leading-5">
          <p className="font-semibold text-ink">{fact.source_fact_id} · {fact.freshness_date}</p>
          <p className="mt-1 text-xs text-slate-600">Dowody: {fact.evidence_ids.join(", ")}</p>
        </li>)}
      </ul> : null}

      {researchData.blocked_sources.length ? <ul className="mt-3 grid gap-2">
        {researchData.blocked_sources.map((source) => <li key={source.source_fact_id} className="rounded-lg border border-wait/30 bg-white px-3 py-2 leading-5">
          <p className="font-semibold text-ink">{source.source_fact_id}</p>
          <p className="mt-1">Odpowiedzialny: {source.blocker_owner}</p>
          <p className="mt-1 text-slate-600">{source.safe_next_step}</p>
        </li>)}
      </ul> : null}

      {researchData.claim_gates.length ? <ul className="mt-3 grid gap-2">
        {researchData.claim_gates.map((gate) => <li key={gate.claim} className="rounded-lg border border-wait/30 bg-white px-3 py-2 leading-5">
          <p className="font-semibold text-ink">{gate.code} ({gate.claim})</p>
          <p className="mt-1 text-slate-600">{gate.detail}</p>
        </li>)}
      </ul> : null}

      {researchData.blockers.length ? <ul className="mt-3 grid gap-2">
        {researchData.blockers.map((blocker) => <li key={blocker.code} className="rounded-lg border border-wait/30 bg-white px-3 py-2 leading-5">
          <p>{blocker.detail}</p>
          <p className="mt-1 font-semibold text-ink">Odpowiedzialny: {blocker.owner}</p>
        </li>)}
      </ul> : null}

      <p className="mt-4 leading-6"><span className="font-semibold text-ink">Następny bezpieczny krok dla dowodów:</span> {researchData.safe_next_step}</p>
    </section>
    <IntakeBriefReadout queueId={queueId} />
  </section>;
}
