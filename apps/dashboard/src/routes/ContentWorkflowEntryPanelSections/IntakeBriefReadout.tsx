import { useQuery } from "@tanstack/react-query";

import { getContentBriefProposal } from "../../lib/api";

const statusLabels = {
  ready: "Gotowy do sprawdzenia",
  blocked: "Zablokowany"
};

const routeLabels = {
  existing_page: "Istniejąca strona",
  new_page: "Nowa strona",
  ambiguous: "Niejednoznaczny wybór"
};

const provenanceLabels = {
  user_input: "od operatora",
  evidence: "z dowodów",
  inference: "wnioskowanie",
  unknown: "brak danych"
};

function researchStatusLabel(status: string): string {
  if (status === "ready") return "dowody gotowe";
  if (status === "blocked") return "dowody zablokowane";
  return status;
}

export function IntakeBriefReadout({ queueId }: { queueId: string }) {
  const brief = useQuery({
    queryKey: ["content-intake", "journey", queueId, "brief"],
    queryFn: () => getContentBriefProposal(queueId)
  });

  if (brief.isLoading) {
    return <section className="mt-5 rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-600" aria-label="Odczytywanie briefu">
      <p>Odczytuję brief do sprawdzenia…</p>
    </section>;
  }

  if (brief.isError || !brief.data) {
    return <section className="mt-5 rounded-xl border border-wait/30 bg-wait/5 p-4 text-sm text-ink" aria-labelledby="content-intake-brief-heading">
      <h3 id="content-intake-brief-heading" className="font-semibold">Brief do sprawdzenia</h3>
      <p className="mt-2 leading-6">Nie udało się odczytać briefu. Odśwież widok — prośba, dowody ani jej przebieg nie zostały przez to zmienione.</p>
    </section>;
  }

  const briefData = brief.data;

  return <section className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700" aria-labelledby="content-intake-brief-heading">
    <div className="flex flex-wrap items-baseline justify-between gap-2">
      <h3 id="content-intake-brief-heading" className="font-semibold text-ink">Brief do sprawdzenia</h3>
      <p className="font-semibold text-action">{statusLabels[briefData.status]}</p>
    </div>

    {briefData.route ? <p className="mt-2 font-semibold text-ink">{routeLabels[briefData.route]}</p> : null}

    {briefData.status === "ready" && briefData.route === "existing_page" ? <section className="mt-3 rounded-lg border border-slate-200 bg-white px-3 py-2 leading-5">
      <p className="font-semibold text-ink">{briefData.target_path}</p>
      {briefData.target_public_url ? <p className="mt-1 break-all text-slate-600">{briefData.target_public_url}</p> : null}
    </section> : null}

    <ul className="mt-4 grid gap-2">
      {briefData.fields.map((field) => <li key={field.field} className="rounded-lg border border-slate-200 bg-white px-3 py-2 leading-5">
        <p className="font-semibold text-ink">{field.field}</p>
        <p className="mt-1 text-slate-700">{field.value}</p>
        <p className="mt-1 text-slate-600">{field.detail}</p>
        <p className="mt-1 text-xs text-slate-600">Źródło: {provenanceLabels[field.provenance]}</p>
        <p className="mt-1 text-xs text-slate-600">Dowody: {field.evidence_ids.join(", ")}</p>
      </li>)}
    </ul>

    {briefData.blockers.length ? <ul className="mt-4 grid gap-2">
      {briefData.blockers.map((blocker) => <li key={blocker.code} className="rounded-lg border border-wait/30 bg-white px-3 py-2 leading-5">
        <p>{blocker.detail}</p>
        <p className="mt-1 font-semibold text-ink">Odpowiedzialny: {blocker.owner}</p>
      </li>)}
    </ul> : null}

    {briefData.research_status ? <p className="mt-4 text-xs leading-5 text-slate-600">Stan dowodów: {researchStatusLabel(briefData.research_status)}</p> : null}
    <p className="mt-4 leading-6"><span className="font-semibold text-ink">Następny bezpieczny krok:</span> {briefData.safe_next_step}</p>
  </section>;
}
