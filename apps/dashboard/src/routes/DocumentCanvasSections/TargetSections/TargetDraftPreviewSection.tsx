import { useMutation } from "@tanstack/react-query";

import { postContentRevisionTargetDraftAction } from "../../../lib/api";
import type { ContentTargetDraftPreview } from "../shared";

export function TargetDraftPreviewDetails({ preview }: { preview: ContentTargetDraftPreview }) {
  const draftAction = useMutation({
    mutationFn: () => {
      if (!preview.target || !preview.confirmation || !preview.payload_digest) {
        throw new Error("Brakuje dokładnego podglądu danych do szkicu.");
      }
      return postContentRevisionTargetDraftAction(
        preview.work_item_id,
        preview.revision.revision_id,
        {
          expected_revision_digest: preview.revision.content_digest,
          expected_target_contract_digest: preview.target.target_contract_digest,
          expected_confirmation_digest: preview.confirmation.confirmation_digest,
          expected_payload_digest: preview.payload_digest,
          requested_by: "operator_local_dashboard"
        }
      );
    }
  });
  if (preview.status === "blocked") {
    return <>
      {preview.blockers.map((blocker) => <div key={blocker.code} className="mt-3 rounded-lg bg-wait/10 p-3">
        <p className="font-semibold text-ink">{blocker.label}</p>
        <p className="mt-2 leading-6">{blocker.reason}</p>
        <p className="mt-2 leading-6 text-slate-600">{blocker.next_step}</p>
      </div>)}
      {preview.caveats.map((caveat) => <p key={caveat} className="mt-2 leading-6 text-slate-600">{caveat}</p>)}
    </>;
  }
  return <>
    <p className="mt-3 font-semibold text-ink">Dane są gotowe do osobnego sprawdzenia</p>
    <p className="mt-2 leading-6">Podgląd pokazuje, co wynika z zatwierdzonego dokumentu i potwierdzonego przypisania. Nie zapisuje zmian na dev.</p>
    <p className="mt-3 text-sm leading-6 text-slate-600">Pole układu: {preview.root_field}. Elementów: {preview.components.length}.</p>
    {preview.preserved_source_summary ? (
      <section className="mt-3 rounded-lg border border-action/20 bg-action/5 p-3">
        <p className="font-semibold text-ink">{preview.preserved_source_summary.label}</p>
        <p className="mt-2 text-sm leading-6 text-slate-700">
          Pola główne ACF w źródle: {preview.preserved_source_summary.source_root_field_count}. Wiersze w polu {preview.root_field}: {preview.preserved_source_summary.source_row_count}.
        </p>
        <p className="mt-1 text-sm leading-6 text-slate-700">
          Wiersze zmieniane: {preview.preserved_source_summary.changed_row_count}. Wiersze bez zmian: {preview.preserved_source_summary.unchanged_row_count}. Sąsiednie pola główne bez zmian: {preview.preserved_source_summary.preserved_sibling_root_field_count}.
        </p>
      </section>
    ) : null}
    <details className="mt-3 rounded-lg bg-slate-50 p-3">
      <summary className="cursor-pointer font-semibold text-ink">Pokaż przygotowane elementy</summary>
      <ul className="mt-3 space-y-3">
        {preview.components.map((component) => <li key={component.component_id} className="rounded-lg bg-white p-3">
          <p className="font-semibold text-ink">{component.label}</p>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            Układ: {component.layout_name}{component.target_section_index != null ? ` · sekcja ${component.target_section_index}` : ""}
          </p>
          {component.fields.map((field) => <div key={`${component.component_id}-${field.target_field}`} className="mt-2 rounded-md border border-line p-2">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">{field.target_field}</p>
            {field.value_kind === "html" ? (
              <div
                className="mt-1 break-words leading-6 text-slate-700"
                dangerouslySetInnerHTML={{ __html: field.value }}
              />
            ) : <p className="mt-1 break-words leading-6 text-slate-700">{field.value}</p>}
          </div>)}
        </li>)}
      </ul>
    </details>
    <section className="mt-4 rounded-lg border border-action/25 bg-action/5 p-3">
      <p className="font-semibold text-ink">Przygotuj akcję dla szkicu</p>
      <p className="mt-2 text-sm leading-6 text-slate-700">
        Utworzysz w WILQ osobną akcję z tym dokładnym dokumentem, przypisaniem i odczytem dev. Następnie sprawdzisz ją, zapiszesz review i potwierdzenie. To nadal nie tworzy szkicu ani nie zmienia WordPressa.
      </p>
      <button
        type="button"
        className="mt-3 w-full rounded-md bg-action px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
        disabled={draftAction.isPending}
        onClick={() => draftAction.mutate()}
      >
        {draftAction.isPending ? "Przygotowuję akcję…" : "Przygotuj akcję szkicu na dev"}
      </button>
      {draftAction.isError ? (
        <p className="mt-3 text-sm font-semibold text-wait">{draftAction.error.message}</p>
      ) : null}
      {draftAction.data ? (
        <div className="mt-3 rounded-md bg-white p-3 text-sm leading-6 text-slate-700">
          <p className="font-semibold text-ink">Akcja jest przygotowana w WILQ.</p>
          <p className="mt-1">Otwórz ją, aby wykonać oddzielne sprawdzenie, review, potwierdzenie i audyt. Zapis WordPress pozostaje zablokowany.</p>
          <a className="mt-2 inline-block font-semibold text-action hover:underline" href={`/actions/${draftAction.data.id}`}>
            Otwórz akcję szkicu
          </a>
        </div>
      ) : null}
    </section>
  </>;
}
