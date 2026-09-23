import { useMutation } from "@tanstack/react-query";

import { prepareContentResearchPacketV2Action } from "../../lib/api";

export function CurrentResearchPacketEntry({ workItemId }: { workItemId: string }) {
  const preview = useMutation({
    mutationFn: () => prepareContentResearchPacketV2Action(workItemId)
  });

  return (
    <div className="mt-3 rounded-xl border border-line p-3 text-sm text-slate-700">
      <p className="font-semibold text-ink">Pakiet badawczy v2</p>
      <p className="mt-1 leading-5">
        Sprawdź fakty, źródła i wymagania po zatwierdzeniu materiału obecnej strony.
      </p>
      <button
        type="button"
        onClick={() => preview.mutate()}
        disabled={preview.isPending}
        className="mt-3 rounded-md border border-action px-3 py-2 font-semibold text-action disabled:opacity-60"
      >
        {preview.isPending ? "Przygotowuję…" : "Przygotuj przegląd pakietu"}
      </button>
      {preview.data?.status === "preview_ready" ? (
        <a
          href={`/actions/${encodeURIComponent(preview.data.action_id)}`}
          className="mt-3 block font-semibold text-action underline"
        >
          Otwórz cały pakiet i decyzję
        </a>
      ) : null}
      {preview.data?.status === "blocked" ? (
        <p className="mt-3 leading-5" role="status">
          {preview.data.safe_next_step} Odpowiedzialny: {preview.data.blocker_owner}.
        </p>
      ) : null}
      {preview.error instanceof Error ? (
        <p className="mt-3 text-risk" role="alert">
          Nie udało się przygotować pakietu. Spróbuj ponownie.
        </p>
      ) : null}
    </div>
  );
}
