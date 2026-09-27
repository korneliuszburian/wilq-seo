import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import {
  createContentIntakeRequest,
  getContentIntakeRequest
} from "../../lib/api";
import { IntakeJourneyReadout } from "./IntakeJourneyReadout";

export function IntakeQueueSection() {
  const [ask, setAsk] = useState("");
  const intake = useMutation({
    mutationFn: async () => {
      const created = await createContentIntakeRequest({
        request_id: crypto.randomUUID(),
        ask
      });
      return getContentIntakeRequest(created.queue_id);
    }
  });
  const queueItem = intake.data;
  const evidenceIds = queueItem?.provenance.flatMap((entry) => entry.evidence_ids) ?? [];

  return (
    <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-5" aria-labelledby="content-intake-heading">
      <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-action">Nowa prośba</p>
      <h2 id="content-intake-heading" className="mt-2 text-xl font-semibold text-ink">Zacznij od celu</h2>
      <p className="mt-2 text-sm leading-6 text-slate-700">WILQ zapisze prośbę, sprawdzi jej stan w kolejce i pokaże najbezpieczniejszy następny krok.</p>
      <form
        className="mt-4 grid gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          if (ask.trim().length >= 3 && !intake.isPending) intake.mutate();
        }}
      >
        <label className="grid gap-2 text-sm font-semibold text-ink" htmlFor="content-intake-ask">
          Co chcesz osiągnąć?
          <textarea
            id="content-intake-ask"
            value={ask}
            onChange={(event) => setAsk(event.target.value)}
            placeholder="np. Odśwież stronę o operacie wodnoprawnym"
            className="min-h-28 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-normal text-ink outline-none transition focus:border-action focus:bg-white focus:ring-4 focus:ring-action/10"
          />
        </label>
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="submit"
            disabled={ask.trim().length < 3 || intake.isPending}
            className="rounded-xl bg-action px-5 py-3 text-sm font-semibold text-white disabled:opacity-60"
          >
            Przyjmij prośbę
          </button>
          <p className="text-xs leading-5 text-slate-600">Nie tworzy to treści, rewizji ani publikacji.</p>
        </div>
      </form>
      {intake.isPending ? <p className="mt-3 text-sm text-slate-600" role="status">Przyjmuję prośbę i sprawdzam zapis kolejki…</p> : null}
      {intake.error ? <p className="mt-3 text-sm text-risk" role="alert">Nie udało się przyjąć prośby. Sprawdź połączenie i spróbuj ponownie.</p> : null}
      {queueItem ? (
        <>
          <section className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700" aria-label="Stan kolejki WILQ">
            <dl className="grid gap-3 sm:grid-cols-2">
              <div>
                <dt className="text-xs font-semibold text-slate-500">Identyfikator kolejki WILQ</dt>
                <dd className="mt-1 break-all font-semibold text-ink">{queueItem.queue_id}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold text-slate-500">Status</dt>
                <dd className="mt-1 font-semibold text-ink">{queueItem.status === "queued" ? "W kolejce" : "Zablokowane"}</dd>
              </div>
            </dl>
            <p className="mt-4 leading-6"><span className="font-semibold text-ink">Następny bezpieczny krok:</span> {queueItem.safe_next_step}</p>
            {queueItem.blockers.length ? (
              <section className="mt-4" aria-labelledby="content-intake-blockers-heading">
                <h3 id="content-intake-blockers-heading" className="font-semibold text-ink">Blokady</h3>
                <ul className="mt-2 grid gap-2">
                  {queueItem.blockers.map((blocker) => (
                    <li key={blocker.code} className="rounded-lg border border-wait/30 bg-white px-3 py-2 leading-5">
                      <span>{blocker.detail}</span><span className="ml-1 font-semibold">Odpowiedzialny: {blocker.owner}</span>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
            {evidenceIds.length ? <p className="mt-4 text-xs leading-5 text-slate-600">Dowody: {evidenceIds.join(", ")}</p> : null}
          </section>
          <IntakeJourneyReadout queueId={queueItem.queue_id} />
        </>
      ) : null}
    </section>
  );
}
