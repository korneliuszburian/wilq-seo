import { ShieldCheck } from "lucide-react";

import type { ContentOpportunityEnrichment } from "../lib/api";
import { ContentWorkflowFactTile as FactTile } from "./ContentWorkflowFactTile";

export function ContentOpportunityEnrichmentPanel({
  enrichment
}: {
  enrichment: ContentOpportunityEnrichment | null;
}) {
  if (!enrichment) {
    return (
      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <div className="flex items-start gap-3">
          <div className="rounded-md border border-line bg-surface p-2 text-action"><ShieldCheck aria-hidden="true" size={18} /></div>
          <div><h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">Wzbogacenie tematu</h2><p className="mt-2 text-sm leading-6 text-slate-600">WILQ nie pokazuje interpretacji tematu bez osobnego kontraktu wzbogacenia z API.</p></div>
        </div>
      </section>
    );
  }

  const facts = enrichment.source_facts.slice(0, 3);
  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2"><ShieldCheck aria-hidden="true" size={18} className="text-action" /><h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">Wzbogacenie tematu</h2></div>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{enrichment.buyer_problem}</p>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">{enrichment.buyer_trigger}</p>
        </div>
        <div className="grid w-full gap-2 text-sm sm:w-auto sm:min-w-80 sm:grid-cols-2"><FactTile label="Intencja" value={enrichment.intent_label} /><FactTile label="Status" value={enrichment.status_label} /></div>
      </div>
      <div className="mt-4 grid gap-3 lg:grid-cols-3">
        <div className="rounded-md border border-line bg-surface p-3"><div className="text-xs uppercase tracking-normal text-slate-500">Kontekst tematu</div><p className="mt-2 text-sm leading-6 text-slate-700">{enrichment.service_fit}</p><p className="mt-1 text-xs leading-5 text-slate-500">Nie zastępuje typed decyzji usługi pokazanej wyżej.</p></div>
        <div className="rounded-md border border-line bg-surface p-3"><div className="text-xs uppercase tracking-normal text-slate-500">Kierunek CTA</div><p className="mt-2 text-sm leading-6 text-slate-700">{enrichment.cta_hypothesis}</p></div>
        <div className="rounded-md border border-line bg-surface p-3"><div className="text-xs uppercase tracking-normal text-slate-500">Pomiar</div><p className="mt-2 text-sm leading-6 text-slate-700">{enrichment.measurement_baseline.label}</p><p className="mt-1 text-xs leading-5 text-slate-500">{enrichment.measurement_baseline.reason}</p></div>
      </div>
      {facts.length ? <div className="mt-4 grid gap-3 lg:grid-cols-3">{facts.map((fact) => <div key={fact.id} className="rounded-md border border-line bg-surface p-3 text-sm"><div className="font-semibold text-ink">{fact.label}</div><p className="mt-2 leading-6 text-slate-700">{fact.summary}</p></div>)}</div> : null}
      {enrichment.blockers.length ? <div className="mt-4 rounded-md border border-wait/30 bg-wait/10 p-3 text-sm text-wait"><div className="font-semibold">{enrichment.blockers[0]?.label}</div><p className="mt-2 leading-6">{enrichment.blockers[0]?.reason}</p><p className="mt-1 text-xs">{enrichment.blockers[0]?.next_step}</p></div> : null}
    </section>
  );
}
