import { useMutation } from "@tanstack/react-query";
import { FileJson, RefreshCw } from "lucide-react";

import { type ActionPreviewResult, previewAction } from "../../lib/api";
import { TraceLine } from "../../components/TraceLine";
import type { ActionPanelProps } from "./shared";

export function ActionPreviewControls({ action }: ActionPanelProps) {
  const previewMutation = useMutation({
    mutationFn: () => previewAction(action.id)
  });

  return (
    <div className="mt-3 rounded-md border border-line bg-slate-50 p-3 text-xs">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="font-semibold uppercase tracking-normal text-slate-600">
            Podgląd zmian
          </div>
          <p className="mt-1 leading-5 text-slate-600">
            Pokazuje, co WILQ sprawdzi. Nie zapisuje zmian w zewnętrznych systemach;
            zapisuje tylko ślad sprawdzenia.
          </p>
        </div>
        <button
          type="button"
          onClick={() => previewMutation.mutate()}
          disabled={previewMutation.isPending}
          className="inline-flex min-h-9 items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-ink hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {previewMutation.isPending ? (
            <RefreshCw aria-hidden="true" className="animate-spin" size={15} />
          ) : (
            <FileJson aria-hidden="true" size={15} />
          )}
          {previewMutation.isPending ? "Generuję" : "Generuj podgląd"}
        </button>
      </div>
      <ActionPreviewResultPanel
        result={previewMutation.data}
        error={previewMutation.error instanceof Error ? previewMutation.error.message : null}
      />
    </div>
  );
}

function ActionPreviewResultPanel({
  result,
  error
}: {
  result?: ActionPreviewResult;
  error: string | null;
}) {
  if (error) {
    return <div className="mt-3 text-xs leading-5 text-risk">Podgląd zablokowany: {error}</div>;
  }
  if (!result) {
    return null;
  }
  return (
    <div className="mt-3 grid gap-2 text-xs text-slate-700">
      <div>
        Podgląd: <span className="font-semibold">{result.status_label}</span>
      </div>
      <div>
        Bez zapisu zmian: {result.dry_run ? "tak" : "nie"}; zapis zmian:{" "}
        {result.mutation_allowed ? "dopuszczone" : "zablokowane"}
      </div>
      <div>
        Pozycje podglądu: {result.preview_items.length}/{result.preview_items_total}
        {result.omitted_items > 0 ? `, pominięto ${result.omitted_items}` : ""}
      </div>
      <TraceLine
        label="Blokady podglądu"
        values={result.blocker_labels}
        empty="WILQ nie zgłosił blokad podglądu."
      />
      <div>Ślad bezpieczeństwa: {result.audit_event.event_type_label}</div>
    </div>
  );
}
