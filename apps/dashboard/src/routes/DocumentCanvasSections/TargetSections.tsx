import { useEffect, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  postContentRevisionTargetDraftAction,
  postContentRevisionTargetMappingConfirmation
} from "../../lib/api";
import type {
  ContentTargetDiscovery,
  ContentTargetDraftPreview,
  ContentTargetMappingPreview,
  TargetMappingSelections,
  TargetMappingTarget
} from "./shared";

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

export function TargetMappingDetails({ preview }: { preview: ContentTargetMappingPreview }) {
  if (preview.status === "blocked") {
    return (
      <>
        {preview.target ? (
          <TargetMappingTargetSummary target={preview.target} />
        ) : null}
        {preview.blockers.map((blocker) => (
          <div key={blocker.code} className="mt-3 rounded-lg bg-wait/10 p-3">
            <p className="font-semibold text-ink">{blocker.label}</p>
            <p className="mt-2 leading-6">{blocker.reason}</p>
            <p className="mt-2 leading-6 text-slate-600">{blocker.next_step}</p>
          </div>
        ))}
        <ComponentMappingList components={preview.components} />
        {preview.caveats.map((caveat) => (
          <p key={caveat} className="mt-2 leading-6 text-slate-600">
            {caveat}
          </p>
        ))}
      </>
    );
  }
  const humanOnly = preview.components.filter(
    (component) => component.status === "human_only"
  );
  return (
    <>
      {preview.target ? <TargetMappingTargetSummary target={preview.target} /> : null}
      <p className="mt-3 font-semibold text-ink">
        Dokument jest gotowy do ręcznego przypisania
      </p>
      <p className="mt-2 leading-6">
        Odczytano układ dev, ale żaden element dokumentu nie został przypisany
        automatycznie. Dzięki temu WILQ nie zgaduje pól ani layoutów.
      </p>
      <p className="mt-3 text-sm leading-6 text-slate-600">
        {humanOnly.length} elementów wymaga decyzji człowieka.
      </p>
      <ComponentMappingList components={preview.components} />
      <TargetMappingConfirmationForm preview={preview} />
      {preview.caveats.map((caveat) => (
        <p key={caveat} className="mt-2 leading-6 text-slate-600">
          {caveat}
        </p>
      ))}
      <details className="mt-3 rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
        <summary className="cursor-pointer font-semibold text-slate-700">
          Szczegóły techniczne odczytu
        </summary>
        <p className="mt-2 break-all">Wersja dokumentu: {preview.revision.revision_id}</p>
        <p className="mt-2 break-all">Identyfikator przypisania: {preview.binding_digest}</p>
        <p className="mt-2 break-all">
          Identyfikator kontraktu: {preview.target?.target_contract_digest}
        </p>
      </details>
    </>
  );
}

function TargetMappingConfirmationForm({
  preview
}: {
  preview: ContentTargetMappingPreview;
}) {
  const queryClient = useQueryClient();
  const [confirmedBy, setConfirmedBy] = useState("");
  const [selections, setSelections] = useState<TargetMappingSelections>({});
  const [deliveryScope, setDeliveryScope] = useState<"full_document" | "selected_components">("full_document");
  const [selectedComponentIds, setSelectedComponentIds] = useState<Record<string, boolean>>({});
  const target = preview.target;
  const surface = target?.target_contract.authoring_surface;
  const layouts = surface?.layouts ?? [];
  const selectedComponents = deliveryScope === "full_document"
    ? preview.components
    : preview.components.filter((component) => selectedComponentIds[component.component_id]);
  const confirmation = useMutation({
    mutationFn: () => {
      if (!target || !preview.binding_digest) throw new Error("Brakuje dokładnego odczytu targetu.");
      return postContentRevisionTargetMappingConfirmation(
        preview.work_item_id,
        preview.revision.revision_id,
        {
          expected_revision_digest: preview.revision.content_digest,
          expected_target_contract_digest: target.target_contract_digest,
          expected_binding_digest: preview.binding_digest,
          confirmed_by: confirmedBy,
          delivery_scope: deliveryScope,
          selections: selectedComponents.map((component) => ({
            component_id: component.component_id,
            layout_name: selections[component.component_id]?.layoutName ?? "",
            target_section_index: selections[component.component_id]?.targetSectionIndex ?? null,
            field_bindings: component.source_fields.map((sourceField) => ({
              source_field: sourceField.key,
              target_field: selections[component.component_id]?.fields[sourceField.key] ?? ""
            }))
          }))
        }
      );
    },
    onSuccess: () => void queryClient.invalidateQueries({
      queryKey: ["content-workflow", "work-item", preview.work_item_id, "draft-revisions", preview.revision.revision_id, "target-mapping"]
    })
  });
  const readyToConfirm = Boolean(
    confirmedBy.trim() && selectedComponents.length > 0 && selectedComponents.every((component) => {
      const selection = selections[component.component_id];
      return selection?.layoutName
        && (surface?.kind !== "acf_flexible_content" || selection.targetSectionIndex != null)
        && component.source_fields.every((field) => selection.fields[field.key]);
    })
  );
  const updateLayout = (componentId: string, layoutName: string) => {
    setSelections((current) => ({
      ...current,
      [componentId]: { layoutName, targetSectionIndex: null, fields: {} }
    }));
  };
  const updateTargetSection = (componentId: string, sectionIndex: number) => {
    const layout = layouts.find((candidate) => candidate.section_index === sectionIndex);
    if (!layout) return;
    setSelections((current) => ({
      ...current,
      [componentId]: { layoutName: layout.name, targetSectionIndex: sectionIndex, fields: {} }
    }));
  };
  const updateField = (componentId: string, sourceField: string, targetField: string) => {
    setSelections((current) => ({
      ...current,
      [componentId]: {
        layoutName: current[componentId]?.layoutName ?? "",
        targetSectionIndex: current[componentId]?.targetSectionIndex ?? null,
        fields: { ...current[componentId]?.fields, [sourceField]: targetField }
      }
    }));
  };

  return (
    <section className="mt-4 rounded-lg border border-action/25 bg-action/5 p-3" data-testid="target-mapping-confirmation">
      <p className="font-semibold text-ink">Potwierdź przypisanie ręcznie</p>
      <p className="mt-2 leading-6 text-slate-700">
        Wybierasz wyłącznie odczytane layouty i pola. Ten zapis pozostaje w WILQ; nie tworzy draftu ani nie zmienia WordPressa.
      </p>
      {surface?.kind === "acf_flexible_content" ? (
        <fieldset className="mt-4 rounded-lg border border-line bg-white p-3">
          <legend className="px-1 text-sm font-semibold text-ink">Zakres szkicu ACF</legend>
          <label className="mt-2 flex items-start gap-2 text-sm leading-6 text-slate-700">
            <input
              checked={deliveryScope === "full_document"}
              name="acf-delivery-scope"
              type="radio"
              value="full_document"
              onChange={() => setDeliveryScope("full_document")}
            />
            <span>Cały dokument — wymaga przypisania każdego elementu rewizji.</span>
          </label>
          <label className="mt-2 flex items-start gap-2 text-sm leading-6 text-slate-700">
            <input
              checked={deliveryScope === "selected_components"}
              name="acf-delivery-scope"
              type="radio"
              value="selected_components"
              onChange={() => setDeliveryScope("selected_components")}
            />
            <span>Tylko wybrane sekcje treści — WILQ zachowa pozostałe pola i layouty z dev.</span>
          </label>
        </fieldset>
      ) : null}
      {preview.confirmation ? (
        <p className="mt-3 rounded-md bg-white p-3 text-sm leading-6 text-slate-700">
          Ostatnie przypisanie zapisał(a) {preview.confirmation.confirmed_by}. Ponowne potwierdzenie utworzy kolejną decyzję dla tej samej wersji i tego samego odczytu targetu.
        </p>
      ) : null}
      <label className="mt-4 block text-sm font-semibold text-ink">
        Potwierdza
        <input
          className="mt-1 block w-full rounded-md border border-line bg-white px-3 py-2 font-normal text-slate-800"
          value={confirmedBy}
          onChange={(event) => setConfirmedBy(event.target.value)}
          placeholder="Imię i nazwisko"
        />
      </label>
      <div className="mt-4 space-y-4">
        {preview.components.map((component) => {
          const canSelectPartial = component.kind === "rich_text";
          const included = deliveryScope === "full_document" || Boolean(selectedComponentIds[component.component_id]);
          const selection = selections[component.component_id];
          const layout = surface?.kind === "acf_flexible_content"
            ? layouts.find((candidate) => candidate.section_index === selection?.targetSectionIndex)
            : layouts.find((candidate) => candidate.name === selection?.layoutName);
          return (
            <fieldset key={component.component_id} className="rounded-lg border border-line bg-white p-3">
              <legend className="px-1 text-sm font-semibold text-ink">{component.label}</legend>
              {deliveryScope === "selected_components" ? (
                <label className="mt-2 flex items-center gap-2 text-sm font-medium text-slate-700">
                  <input
                    checked={included}
                    disabled={!canSelectPartial}
                    type="checkbox"
                    onChange={(event) => setSelectedComponentIds((current) => ({
                      ...current,
                      [component.component_id]: event.target.checked
                    }))}
                  />
                  {canSelectPartial ? "Uwzględnij tę sekcję w szkicu ACF" : "Ten element wymaga pełnego mapowania dokumentu"}
                </label>
              ) : null}
              {included ? <>
              <label className="mt-2 block text-sm font-medium text-slate-700">
                {surface?.kind === "acf_flexible_content" ? "Sekcja na dev" : "Layout"}
                <select
                  className="mt-1 block w-full rounded-md border border-line bg-white px-3 py-2 text-slate-800"
                  value={surface?.kind === "acf_flexible_content"
                    ? String(selection?.targetSectionIndex ?? "")
                    : selection?.layoutName ?? ""}
                  onChange={(event) => {
                    if (surface?.kind === "acf_flexible_content") {
                      if (!event.target.value) {
                        setSelections((current) => ({
                          ...current,
                          [component.component_id]: {
                            layoutName: "",
                            targetSectionIndex: null,
                            fields: {}
                          }
                        }));
                      } else {
                        updateTargetSection(component.component_id, Number(event.target.value));
                      }
                    } else {
                      updateLayout(component.component_id, event.target.value);
                    }
                  }}
                >
                  <option value="">Wybierz odczytaną sekcję</option>
                  {layouts.map((candidate) => surface?.kind === "acf_flexible_content" ? (
                    <option key={`${candidate.section_index}-${candidate.name}`} value={candidate.section_index ?? ""}>
                      {candidate.section_index != null ? `Sekcja ${candidate.section_index} · ` : ""}{candidate.label || candidate.name}
                    </option>
                  ) : <option key={candidate.name} value={candidate.name}>{candidate.label || candidate.name}</option>)}
                </select>
              </label>
              {component.source_fields.map((sourceField) => (
                <label key={sourceField.key} className="mt-3 block text-sm font-medium text-slate-700">
                  {sourceField.label}
                  <select
                    className="mt-1 block w-full rounded-md border border-line bg-white px-3 py-2 text-slate-800 disabled:bg-slate-50"
                    disabled={!layout}
                    value={selection?.fields[sourceField.key] ?? ""}
                    onChange={(event) => updateField(component.component_id, sourceField.key, event.target.value)}
                  >
                    <option value="">Wybierz pole</option>
                    {(surface?.kind === "acf_flexible_content" && layout?.writable_fields.length
                      ? layout.writable_fields
                      : layout?.fields
                    )?.map((field) => <option key={field} value={field}>{field}</option>)}
                  </select>
                </label>
              ))}
              </> : null}
            </fieldset>
          );
        })}
      </div>
      <button
        type="button"
        className="mt-4 w-full rounded-md bg-action px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
        disabled={!readyToConfirm || confirmation.isPending}
        onClick={() => confirmation.mutate()}
      >
        {confirmation.isPending ? "Zapisuję przypisanie…" : "Zapisz potwierdzenie przypisania"}
      </button>
      {confirmation.isError ? <p className="mt-3 text-sm font-semibold text-wait">{confirmation.error.message}</p> : null}
      {confirmation.isSuccess ? <p className="mt-3 text-sm font-semibold text-action">Przypisanie zapisane w WILQ. Nadal nie utworzono draftu na dev.</p> : null}
    </section>
  );
}

function TargetMappingTargetSummary({
  target
}: {
  target: TargetMappingTarget;
}) {
  const surface = target.target_contract.authoring_surface;
  return (
    <div className="mt-3 rounded-lg bg-slate-50 p-3">
      <p className="font-semibold text-ink">
        Znaleziono {wordpressObjectLabel(target.target_contract.post_type)} na dev
      </p>
      <a
        className="mt-1 block break-all font-medium leading-6 text-action hover:underline"
        href={target.target_contract.url}
        rel="noreferrer"
        target="_blank"
      >
        {target.target_contract.url}
      </a>
      <p className="mt-2 leading-6 text-slate-700">
        Środowisko: {target.target_contract.environment}.
      </p>
      <DevTargetLivePreview url={target.target_contract.url} />
      {surface ? (
        <>
          <p className="mt-3 font-semibold text-ink">Zaobserwowane możliwości układu</p>
          <p className="mt-1 leading-6 text-slate-700">
            {authoringSurfaceLabel(surface.kind)}: {surface.root_field}
          </p>
          <p className="mt-1 leading-6 text-slate-700">
            Odczytane sekcje: {surface.layouts.map((layout) => (
              layout.section_index != null
                ? `${layout.section_index}. ${layout.label || layout.name}`
                : layout.label || layout.name
            )).join(", ")}
          </p>
          {surface.kind === "acf_flexible_content" ? (
            <>
              <p className="mt-2 leading-6 text-slate-600">
                {surface.schema_status === "available"
                  ? `Schema ACF z dev rozpoznany${surface.schema_digest ? " dla dokładnego obiektu" : ""}. ` +
                    "WILQ zachowa istniejący układ i może podmienić wyłącznie potwierdzone pola tekstowe."
                  : `Schema ACF nie jest jeszcze dostępny: ${surface.schema_reason || "brakuje odczytu OPTIONS."}`}
              </p>
              {surface.schema_status === "available" ? (
                <details className="mt-2 text-sm text-slate-600">
                  <summary className="cursor-pointer font-medium text-ink">
                    Rozpoznane pola ACF
                  </summary>
                  <ul className="mt-2 space-y-1">
                    {surface.layouts.map((layout) => (
                      <li key={`${layout.section_index}-${layout.name}`}>
                        <span className="font-medium text-ink">
                          {layout.section_index != null ? `Sekcja ${layout.section_index} · ` : ""}{layout.label || layout.name}:
                        </span>{" "}
                        {layout.schema_fields.length > 0
                          ? layout.schema_fields.join(", ")
                          : "brak pola w schema dla tego obserwowanego layoutu"}
                      </li>
                    ))}
                  </ul>
                </details>
              ) : null}
            </>
          ) : null}
          <p className="mt-2 leading-6 text-slate-600">
            {surface.write_profile_status === "ready"
              ? surface.write_profile_reason
              : `Nie przygotujemy szkicu ACF: ${surface.write_profile_reason || "brakuje dokładnego profilu pól."}`}
          </p>
          <p className="mt-2 leading-6 text-slate-600">
            To są odczytane możliwości, a nie decyzja, gdzie trafi element dokumentu.
          </p>
        </>
      ) : null}
    </div>
  );
}

export function DevTargetLivePreview({ url }: { url: string }) {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    if (!open) return;
    const dialog = dialogRef.current;
    const trigger = triggerRef.current;
    if (!dialog) return;
    if (typeof dialog.showModal === "function") {
      dialog.showModal();
    } else {
      dialog.setAttribute("open", "");
    }
    closeRef.current?.focus();
    return () => {
      if (typeof dialog.close === "function" && dialog.open) {
        dialog.close();
      } else {
        dialog.removeAttribute("open");
      }
      trigger?.focus();
    };
  }, [open]);

  return (
    <>
      <button
        className="mt-3 w-full rounded-md border border-line bg-white px-3 py-2 text-left text-sm font-semibold text-action hover:border-action"
        ref={triggerRef}
        type="button"
        onClick={() => setOpen(true)}
      >
        Otwórz podgląd strony dev
      </button>
      {open ? (
        <dialog
          aria-labelledby="dev-target-live-preview-title"
          className="h-[min(88vh,64rem)] w-[min(96vw,90rem)] rounded-2xl bg-white p-4 shadow-2xl backdrop:bg-slate-950/45 lg:p-5"
          onCancel={(event) => {
            event.preventDefault();
            setOpen(false);
          }}
          ref={dialogRef}
        >
          <section className="flex h-full flex-col">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-ink" id="dev-target-live-preview-title">Podgląd strony dev</h2>
                <p className="mt-1 text-sm leading-6 text-slate-700">
                  To jest bieżąca strona dev jako punkt odniesienia. Nie pokazuje niezapisanych zmian z mapowania i nie zmienia WordPressa.
                </p>
              </div>
              <button
                aria-label="Zamknij podgląd strony dev"
                className="rounded-md border border-line px-3 py-2 text-sm font-semibold text-slate-700 hover:border-action hover:text-action"
                ref={closeRef}
                type="button"
                onClick={() => setOpen(false)}
              >
                Zamknij
              </button>
            </div>
            <div className="mt-3 flex justify-end">
              <a
                className="text-sm font-semibold text-action hover:underline"
                href={url}
                rel="noreferrer"
                target="_blank"
              >
                Otwórz stronę dev w nowej karcie
              </a>
            </div>
            <iframe
              className="mt-3 min-h-0 flex-1 rounded-md border border-line bg-white"
              referrerPolicy="no-referrer"
              sandbox="allow-same-origin"
              src={url}
              title="Referencyjny podgląd strony dev"
            />
          </section>
        </dialog>
      ) : null}
    </>
  );
}

function ComponentMappingList({
  components
}: {
  components: ContentTargetMappingPreview["components"];
}) {
  if (components.length === 0) {
    return null;
  }
  return (
    <details className="mt-3 rounded-lg bg-slate-50 p-3">
      <summary className="cursor-pointer font-semibold text-ink">
        Elementy dokumentu ({components.length})
      </summary>
      <ul className="mt-3 space-y-2">
        {components.map((component) => (
          <li key={component.component_id} className="rounded-lg bg-white p-3">
            <p className="font-semibold text-ink">{component.label}</p>
            <p className="mt-1 leading-6 text-slate-700">{component.reason}</p>
          </li>
        ))}
      </ul>
    </details>
  );
}

export function DevTargetDetails({ discovery }: { discovery: ContentTargetDiscovery }) {
  if (discovery.relation_status === "unavailable") return <>
    <p className="mt-3 font-semibold text-ink">{discovery.label}</p>
    <p className="mt-2 leading-6">{discovery.reason}</p>
    {discovery.caveats.map((caveat) => <p key={caveat} className="mt-2 leading-6 text-slate-600">{caveat}</p>)}
  </>;
  if (discovery.relation_status === "ambiguous") return <>
    <p className="mt-3 font-semibold text-ink">{discovery.label}</p>
    <p className="mt-2 leading-6">{discovery.reason}</p>
    <ul className="mt-3 space-y-2">
      {discovery.candidates.map((candidate) => <li key={candidate.observation_evidence.evidence_id} className="rounded-lg bg-slate-50 p-3">
        <p className="font-semibold text-ink">{candidate.post_type === "post" ? "Artykuł" : "Strona"} · {wordpressStatus(candidate.post_status)}</p>
        <p className="mt-1 break-all leading-6">{candidate.url}</p>
      </li>)}
    </ul>
    {discovery.caveats.map((caveat) => <p key={caveat} className="mt-2 leading-6 text-slate-600">{caveat}</p>)}
  </>;
  const target = discovery.target;
  const observedRelationships = target?.target_contract.authoring_surface?.layouts.flatMap((layout) =>
    layout.relationships.map((relationship) => ({ layout, relationship }))
  ) ?? [];
  return <>
    <p className="mt-3 font-semibold text-ink">{discovery.label}</p>
    <p className="mt-2 leading-6">{discovery.reason}</p>
    {target ? <div className="mt-3 rounded-lg bg-slate-50 p-3">
      <p className="font-semibold text-ink">Zaobserwowana strona robocza</p>
      <p className="mt-1 break-all leading-6">{target.url}</p>
      <p className="mt-2 leading-6">To {target.post_type === "post" ? "artykuł" : "strona"}. Status na dev: {wordpressStatus(target.post_status)}. {target.target_contract.authoring_surface ? `WILQ odczytał ${authoringSurfaceLabel(target.target_contract.authoring_surface.kind).toLocaleLowerCase("pl-PL")}.` : "Nie rozpoznano układu treści na tym obiekcie."}</p>
    </div> : null}
    {observedRelationships.length > 0 ? <details className="mt-3 rounded-lg bg-slate-50 p-3">
      <summary className="cursor-pointer font-semibold text-ink">Odczytane relacje ACF</summary>
      <p className="mt-2 text-sm leading-6 text-slate-700">To jest odczyt bieżącego układu deva. Nie zmienia kolejności ani relacji automatycznie.</p>
      <div className="mt-3 space-y-3">
        {observedRelationships.map(({ layout, relationship }) => <section key={`${layout.section_index ?? layout.name}-${relationship.field_name}`} className="rounded-md bg-white p-3 text-sm">
          <p className="font-semibold text-ink">{layout.label || layout.name} · {relationship.field_name}</p>
          <p className="mt-1 leading-6 text-slate-700">{relationship.reason}</p>
          {relationship.status === "available" ? <ul className="mt-2 space-y-1 text-slate-700">
            {relationship.items.map((item) => <li key={item.relationship_id}>{item.label}</li>)}
          </ul> : null}
        </section>)}
      </div>
    </details> : null}
    {discovery.caveats.map((caveat) => <p key={caveat} className="mt-2 leading-6 text-slate-600">{caveat}</p>)}
    <details className="mt-3 rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
      <summary className="cursor-pointer font-semibold text-slate-700">Szczegóły techniczne odczytu</summary>
      <p className="mt-2">Środowisko: {target?.target_contract.environment ?? "brak"}. Zapis: niedozwolony.</p>
      <p className="mt-2 break-all">Identyfikator obserwacji: {target?.observation_evidence.evidence_id ?? "brak"}</p>
      <p className="mt-2 break-all">Identyfikator kontraktu: {target?.target_contract_digest ?? "brak"}</p>
    </details>
  </>;
}

function wordpressStatus(status: string) {
  return { publish: "opublikowany", draft: "szkic", pending: "oczekuje na przegląd" }[status] ?? status;
}

function wordpressObjectLabel(postType: string) {
  return { post: "artykuł", page: "stronę" }[postType] ?? "obiekt";
}

function authoringSurfaceLabel(kind: "acf_flexible_content" | "wordpress_post_content") {
  return kind === "acf_flexible_content" ? "Układ ACF Flexible Content" : "Treść wpisu WordPress";
}

