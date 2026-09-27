import { useMutation } from "@tanstack/react-query";

import { preparePlanningGenerationIntentV3Action } from "../lib/api";

export function PlanningGenerationIntentV3Entry({
  workItemId,
  packetId,
  packetDigest
}: {
  workItemId: string;
  packetId: string;
  packetDigest: string;
}) {
  const preview = useMutation({
    mutationFn: () => preparePlanningGenerationIntentV3Action(workItemId, packetId, packetDigest)
  });

  return (
    <div className="mt-3 rounded-xl border border-line p-3 text-sm text-slate-700">
      <p className="font-semibold text-ink">Zamiar planowania z pakietu v3</p>
      <p className="mt-1 leading-5">
        Ta czynność przygotowuje wyłącznie lokalny ActionObject. Nie uruchamia planowania,
        modelu ani zapisu zewnętrznego.
      </p>
      <button
        type="button"
        onClick={() => preview.mutate()}
        disabled={preview.isPending}
        className="mt-3 rounded-md border border-action px-3 py-2 font-semibold text-action disabled:opacity-60"
      >
        Przygotuj zamiar planowania
      </button>
      {preview.data?.status === "preview_ready" ? (
        <a
          href={`/actions/${encodeURIComponent(preview.data.action_id)}`}
          className="mt-3 block font-semibold text-action underline"
        >
          Otwórz zamiar planowania i decyzję
        </a>
      ) : null}
      {preview.data?.status === "blocked" ? (
        <p className="mt-3 leading-5" role="status">
          {preview.data.safe_next_step} Odpowiedzialny: {preview.data.blocker_owner}. Dowody: {preview.data.evidence_ids.join(", ") || "brak"}.
        </p>
      ) : null}
      {preview.isError ? (
        <p className="mt-3 text-risk" role="alert">
          Nie udało się przygotować zamiaru planowania. Spróbuj ponownie.
        </p>
      ) : null}
    </div>
  );
}
