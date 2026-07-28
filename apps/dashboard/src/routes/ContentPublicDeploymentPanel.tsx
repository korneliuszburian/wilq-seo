import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { postContentRevisionPublicDeployment } from "../lib/api";
import { useContentRevisionPublicDeployment } from "./contentWorkflowQueries";
import { ContentMeasurementPanel } from "./ContentMeasurementPanel";

export function ContentPublicDeploymentPanel({
  workItemId,
  revisionId,
  revisionDigest
}: {
  workItemId: string;
  revisionId: string;
  revisionDigest: string;
}) {
  const [open, setOpen] = useState(false);
  const [confirmedBy, setConfirmedBy] = useState("");
  const [selectedEvidenceId, setSelectedEvidenceId] = useState("");
  const queryClient = useQueryClient();
  const deployment = useContentRevisionPublicDeployment(workItemId, revisionId, open);
  const confirmation = useMutation({
    mutationFn: () => {
      const observation = deployment.data?.publication_observations.find(
        (candidate) => candidate.publication_evidence_id === selectedEvidenceId
      );
      if (!observation) throw new Error("Wybierz odczyt publicznego obiektu.");
      return postContentRevisionPublicDeployment(workItemId, revisionId, {
        expected_revision_digest: revisionDigest,
        wordpress_post_id: observation.wordpress_post_id,
        publication_evidence_id: observation.publication_evidence_id,
        confirmed_by: confirmedBy.trim()
      });
    },
    onSuccess: () => void queryClient.invalidateQueries({
      queryKey: [
        "content-workflow",
        "work-item",
        workItemId,
        "draft-revisions",
        revisionId,
        "public-deployment"
      ]
    })
  });
  const readyToConfirm = Boolean(
    confirmedBy.trim() && selectedEvidenceId && !deployment.data?.deployment
  );

  return (
    <details
      className="mt-3 rounded-xl border border-line p-3 text-sm text-slate-700"
      onToggle={(event) => {
        if ((event.currentTarget as HTMLDetailsElement).open) setOpen(true);
      }}
      data-testid="public-deployment-panel"
    >
      <summary className="cursor-pointer font-semibold text-ink">
        Potwierdzenie publicznego wdrożenia
      </summary>
      {!open ? (
        <p className="mt-3 leading-6">
          Otwórz po niezależnym wdrożeniu, aby sprawdzić zapisane obserwacje publicznej strony.
          WILQ nie publikuje tej treści.
        </p>
      ) : null}
      {deployment.isPending ? <p className="mt-3 leading-6">Sprawdzam lokalny odczyt publicznej strony…</p> : null}
      {deployment.isError ? <p className="mt-3 leading-6">Nie udało się odczytać potwierdzenia wdrożenia. Spróbuj ponownie później.</p> : null}
      {deployment.data?.deployment ? (
        <>
          <section className="mt-3 rounded-lg bg-emerald-50 p-3" data-testid="public-deployment-confirmed">
            <p className="font-semibold text-ink">Publiczne wdrożenie jest potwierdzone</p>
            <a className="mt-2 block break-all font-medium text-action hover:underline" href={deployment.data.deployment.public_url} target="_blank" rel="noreferrer">
              {deployment.data.deployment.public_url}
            </a>
            <p className="mt-2 leading-6">{deployment.data.safe_next_step}</p>
          </section>
          <ContentMeasurementPanel
            workItemId={workItemId}
            revisionId={revisionId}
            state={deployment.data}
          />
        </>
      ) : null}
      {deployment.data && !deployment.data.deployment ? (
        <section className="mt-3 rounded-lg bg-slate-50 p-3">
          <p className="font-semibold text-ink">WILQ nie potwierdził jeszcze publicznego wdrożenia</p>
          <p className="mt-2 leading-6">{deployment.data.safe_next_step}</p>
          {deployment.data.publication_observations.length === 0 ? (
            <p className="mt-3 leading-6 text-slate-600">
              Nie ma lokalnego odczytu opublikowanego obiektu dokładnie dla tej wersji i adresu. Nie zapisujemy potwierdzenia na podstawie domysłu.
            </p>
          ) : (
            <>
              <label className="mt-3 block font-semibold text-ink" htmlFor="public-deployment-observation">
                Zaobserwowany publiczny obiekt
              </label>
              <select
                id="public-deployment-observation"
                className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2"
                value={selectedEvidenceId}
                onChange={(event) => setSelectedEvidenceId(event.target.value)}
              >
                <option value="">Wybierz odczyt</option>
                {deployment.data.publication_observations.map((observation) => (
                  <option key={observation.publication_evidence_id} value={observation.publication_evidence_id}>
                    Obiekt {observation.wordpress_post_id} · {new Date(observation.observed_at).toLocaleString("pl-PL")}
                  </option>
                ))}
              </select>
              <label className="mt-3 block font-semibold text-ink" htmlFor="public-deployment-confirmed-by">
                Potwierdza
              </label>
              <input
                id="public-deployment-confirmed-by"
                className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2"
                value={confirmedBy}
                onChange={(event) => setConfirmedBy(event.target.value)}
                placeholder="Imię i nazwisko"
              />
              <button
                type="button"
                className="mt-3 w-full rounded-md bg-action px-3 py-2 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
                disabled={!readyToConfirm || confirmation.isPending}
                onClick={() => confirmation.mutate()}
              >
                {confirmation.isPending ? "Zapisuję potwierdzenie…" : "Zapisz potwierdzenie wdrożenia"}
              </button>
              {confirmation.isError ? <p className="mt-3 font-semibold text-wait">{confirmation.error.message}</p> : null}
            </>
          )}
        </section>
      ) : null}
      <p className="mt-3 text-xs leading-5 text-slate-600">
        Ten krok zapisuje wyłącznie lokalne potwierdzenie wcześniej zaobserwowanego publicznego wdrożenia. Nie publikuje, nie aktualizuje i nie usuwa niczego w WordPressie.
      </p>
    </details>
  );
}
