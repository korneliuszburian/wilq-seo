import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  type ContentDocumentWorkspace,
  type ContentTargetDiscovery,
  type ContentTargetDraftPreview,
  type ContentTargetMappingPreview,
  postContentRevisionTargetDraftAction,
  postContentRevisionTargetMappingConfirmation
} from "../lib/api";
import {
  useContentRevisionTargetMapping,
  useContentRevisionTargetDraftPreview,
  useContentTargetDiscovery
} from "./contentWorkflowQueries";
import { ContentApprovedHtmlPackage } from "./ContentApprovedHtmlPackage";
import { ContentPlanningGenerationPanel } from "./ContentPlanningGenerationPanel";
import { ContentPlanningPlanReview } from "./ContentPlanningPlanReview";
import { ContentPublicDeploymentPanel } from "./ContentPublicDeploymentPanel";
import { ContentWorkflowWorkspaceHeader } from "./ContentWorkflowWorkspaceHeader";

type View = "source" | "document" | "comparison";

export function ContentDocumentWorkspaceCanvas({
  workspace,
  onOpenReview
}: {
  workspace: ContentDocumentWorkspace;
  onOpenReview: () => void;
}) {
  const [view, setView] = useState<View>("source");
  const [devDetailsOpen, setDevDetailsOpen] = useState(false);
  const [mappingOpen, setMappingOpen] = useState(false);
  const [draftPreviewOpen, setDraftPreviewOpen] = useState(false);
  const targetDiscovery = useContentTargetDiscovery(workspace.work_item_id, devDetailsOpen);
  const targetMapping = useContentRevisionTargetMapping(
    workspace.work_item_id,
    workspace.canonical_document.revision_id ?? null,
    mappingOpen && workspace.canonical_document.status === "approved"
  );
  const targetDraftPreview = useContentRevisionTargetDraftPreview(
    workspace.work_item_id,
    workspace.canonical_document.revision_id ?? null,
    draftPreviewOpen && workspace.canonical_document.status === "approved"
  );
  const hasReviewAction = workspace.next_action.kind === "open_review";

  return (
    <main className="mx-auto max-w-[92rem] px-4 py-5 lg:px-8" data-testid="content-text-workspace">
      <ContentWorkflowWorkspaceHeader />
      <section className="rounded-2xl border border-action/25 bg-white p-5 shadow-sm lg:p-6">
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-start">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-action">Praca nad treścią</p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight text-ink lg:text-3xl">
              {workspace.source_snapshot.title ?? "Wybrana strona"}
            </h1>
            {workspace.source_snapshot.url ? (
              <a className="mt-2 block break-all text-sm font-medium text-action hover:underline" href={workspace.source_snapshot.url} target="_blank" rel="noreferrer">
                {workspace.source_snapshot.url}
              </a>
            ) : null}
            <p className="mt-2 text-sm font-medium text-slate-700">Usługa: {workspace.service_label ?? "niepotwierdzona"}</p>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-700">
              W jednym miejscu sprawdzisz obecną stronę, dokładny stan dokumentu i materiały zapisane przy tej rewizji. To nie zmienia WordPressa.
            </p>
          </div>
          <section className="min-w-64 rounded-xl border border-line bg-surface p-4" data-testid="content-document-state">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-wait">Stan nowej wersji</p>
            <p className="mt-2 text-base font-semibold text-ink">{workspace.canonical_document.label}</p>
            <p className="mt-1 text-sm leading-5 text-slate-700">{workspace.canonical_document.reason}</p>
            {hasReviewAction ? (
              <button type="button" className="mt-3 w-full rounded-md bg-action px-3 py-2 text-sm font-semibold text-white" onClick={onOpenReview}>
                {workspace.next_action.label}
              </button>
            ) : null}
          </section>
        </div>
      </section>

      {workspace.canonical_document.status !== "approved" ? (
        <section className="mt-4 space-y-4">
          <ContentPlanningGenerationPanel workItemId={workspace.work_item_id} />
          <ContentPlanningPlanReview workItemId={workspace.work_item_id} />
        </section>
      ) : null}

      <nav className="mt-4 flex gap-1 border-b border-line" aria-label="Widok dokumentu">
        <Tab active={view === "source"} onClick={() => setView("source")}>Obecna strona</Tab>
        <Tab active={view === "document"} onClick={() => setView("document")}>Nowa wersja</Tab>
        <Tab active={view === "comparison"} onClick={() => setView("comparison")}>Zmiany w treści</Tab>
      </nav>

      <section className="mt-4 grid gap-4 xl:grid-cols-[17rem_minmax(0,1fr)_18rem]">
        <section className="order-1 min-w-0 rounded-2xl border border-line bg-white p-5 shadow-sm lg:p-7 xl:order-2" data-testid="content-workspace-canvas">
          {view === "source" ? <CurrentSource workspace={workspace} /> : null}
          {view === "document" ? <CanonicalDocument workspace={workspace} /> : null}
          {view === "comparison" ? <Comparison workspace={workspace} /> : null}
        </section>
        <aside className="order-2 rounded-2xl border border-line bg-white p-4 shadow-sm xl:order-1" aria-label="Struktura strony">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Struktura strony</p>
          <p className="mt-2 text-sm leading-6 text-slate-700">{outlineLead(view)}</p>
          <ol className="mt-4 space-y-2">
            {outline(view, workspace).map((label, index) => (
              <li key={`${label}-${index}`} className="rounded-lg bg-slate-50 px-3 py-2 text-sm leading-5 text-slate-700">
                <span className="mr-2 font-semibold text-slate-500">{index + 1}.</span>{label}
              </li>
            ))}
          </ol>
        </aside>
        <aside className="order-3 rounded-2xl border border-line bg-white p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Kontekst pracy</p>
          <StatusCard label="Materiał obecnej strony" value={sourceStatus(workspace.source_snapshot.status)} />
          <StatusCard label="Nowy dokument" value={documentStatus(workspace.canonical_document.status)} />
          <DocumentLineage workspace={workspace} />
          {workspace.canonical_document.status === "approved" && workspace.canonical_document.revision_id && workspace.canonical_document.content_digest ? (
            <ContentApprovedHtmlPackage
              workItemId={workspace.work_item_id}
              revisionId={workspace.canonical_document.revision_id}
              revisionDigest={workspace.canonical_document.content_digest}
            />
          ) : null}
          {workspace.canonical_document.status === "approved" && workspace.canonical_document.revision_id && workspace.canonical_document.content_digest ? (
            <ContentPublicDeploymentPanel
              workItemId={workspace.work_item_id}
              revisionId={workspace.canonical_document.revision_id}
              revisionDigest={workspace.canonical_document.content_digest}
            />
          ) : null}
          <details className="mt-3 rounded-xl border border-line p-3 text-sm text-slate-700">
            <summary className="cursor-pointer font-semibold text-ink">Źródła i ograniczenia</summary>
            <p className="mt-3 leading-6">{workspace.source_snapshot.reason}</p>
            {workspace.secondary_disclosures.map((detail) => <p key={detail} className="mt-3 leading-6">{detail}</p>)}
          </details>
          <details className="mt-3 rounded-xl border border-line p-3 text-sm text-slate-700" onToggle={(event) => {
            if ((event.currentTarget as HTMLDetailsElement).open) setDevDetailsOpen(true);
          }}>
            <summary className="cursor-pointer font-semibold text-ink">Strona robocza na dev</summary>
            {!devDetailsOpen ? <p className="mt-3 leading-6">Otwórz, aby sprawdzić, co WILQ odczytał na dev. To nie zmienia strony ani nie uruchamia WordPressa.</p> : null}
            {targetDiscovery.isPending ? <p className="mt-3 leading-6">Wczytuję odczyt strony roboczej na dev…</p> : null}
            {targetDiscovery.isError ? <p className="mt-3 leading-6">Nie udało się odczytać strony roboczej na dev. Spróbuj ponownie później.</p> : null}
            {targetDiscovery.data ? <DevTargetDetails discovery={targetDiscovery.data} /> : null}
          </details>
          {workspace.canonical_document.status === "approved" ? <details className="mt-3 rounded-xl border border-line p-3 text-sm text-slate-700" onToggle={(event) => {
            if ((event.currentTarget as HTMLDetailsElement).open) setMappingOpen(true);
          }}>
            <summary className="cursor-pointer font-semibold text-ink">Przypisanie dokumentu do dev</summary>
            {!mappingOpen ? <p className="mt-3 leading-6">Otwórz, aby sprawdzić, które elementy zatwierdzonego dokumentu wymagają jeszcze potwierdzenia w układzie dev.</p> : null}
            {targetMapping.isPending ? <p className="mt-3 leading-6">Sprawdzam przypisanie zatwierdzonego dokumentu…</p> : null}
            {targetMapping.isError ? <p className="mt-3 leading-6">Nie udało się odczytać przypisania dokumentu. Spróbuj ponownie później.</p> : null}
            {targetMapping.data ? <TargetMappingDetails preview={targetMapping.data} /> : null}
          </details> : null}
          {workspace.canonical_document.status === "approved" ? <details className="mt-3 rounded-xl border border-line p-3 text-sm text-slate-700" onToggle={(event) => {
            if ((event.currentTarget as HTMLDetailsElement).open) setDraftPreviewOpen(true);
          }}>
            <summary className="cursor-pointer font-semibold text-ink">Podgląd danych do szkicu na dev</summary>
            {!draftPreviewOpen ? <p className="mt-3 leading-6">Otwórz po potwierdzeniu przypisania, aby zobaczyć dane przygotowane z dokładnej wersji dokumentu. To nadal nie tworzy szkicu.</p> : null}
            {targetDraftPreview.isPending ? <p className="mt-3 leading-6">Przygotowuję podgląd danych do szkicu…</p> : null}
            {targetDraftPreview.isError ? <p className="mt-3 leading-6">Nie udało się przygotować podglądu danych. Spróbuj ponownie później.</p> : null}
            {targetDraftPreview.data ? <TargetDraftPreviewDetails preview={targetDraftPreview.data} /> : null}
          </details> : null}
        </aside>
      </section>
    </main>
  );
}

function TargetDraftPreviewDetails({ preview }: { preview: ContentTargetDraftPreview }) {
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
    <details className="mt-3 rounded-lg bg-slate-50 p-3">
      <summary className="cursor-pointer font-semibold text-ink">Pokaż przygotowane elementy</summary>
      <ul className="mt-3 space-y-3">
        {preview.components.map((component) => <li key={component.component_id} className="rounded-lg bg-white p-3">
          <p className="font-semibold text-ink">{component.label}</p>
          <p className="mt-1 text-sm leading-6 text-slate-600">Układ: {component.layout_name}</p>
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

function TargetMappingDetails({ preview }: { preview: ContentTargetMappingPreview }) {
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
  const [selections, setSelections] = useState<Record<string, { layoutName: string; fields: Record<string, string> }>>({});
  const target = preview.target;
  const layouts = target?.target_contract.authoring_surface?.layouts ?? [];
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
          selections: preview.components.map((component) => ({
            component_id: component.component_id,
            layout_name: selections[component.component_id]?.layoutName ?? "",
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
    confirmedBy.trim() && preview.components.every((component) => {
      const selection = selections[component.component_id];
      return selection?.layoutName && component.source_fields.every((field) => selection.fields[field.key]);
    })
  );
  const updateLayout = (componentId: string, layoutName: string) => {
    setSelections((current) => ({
      ...current,
      [componentId]: { layoutName, fields: {} }
    }));
  };
  const updateField = (componentId: string, sourceField: string, targetField: string) => {
    setSelections((current) => ({
      ...current,
      [componentId]: {
        layoutName: current[componentId]?.layoutName ?? "",
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
          const selection = selections[component.component_id];
          const layout = layouts.find((candidate) => candidate.name === selection?.layoutName);
          return (
            <fieldset key={component.component_id} className="rounded-lg border border-line bg-white p-3">
              <legend className="px-1 text-sm font-semibold text-ink">{component.label}</legend>
              <label className="mt-2 block text-sm font-medium text-slate-700">
                Layout
                <select
                  className="mt-1 block w-full rounded-md border border-line bg-white px-3 py-2 text-slate-800"
                  value={selection?.layoutName ?? ""}
                  onChange={(event) => updateLayout(component.component_id, event.target.value)}
                >
                  <option value="">Wybierz odczytany layout</option>
                  {layouts.map((candidate) => <option key={candidate.name} value={candidate.name}>{candidate.name}</option>)}
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
                    {layout?.fields.map((field) => <option key={field} value={field}>{field}</option>)}
                  </select>
                </label>
              ))}
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
  target: NonNullable<ContentTargetMappingPreview["target"]>;
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
      {surface ? (
        <>
          <p className="mt-3 font-semibold text-ink">Zaobserwowane możliwości układu</p>
          <p className="mt-1 leading-6 text-slate-700">
            Pole układu: {surface.root_field}
          </p>
          <p className="mt-1 leading-6 text-slate-700">
            Dostępne układy: {surface.layouts.map((layout) => layout.name).join(", ")}
          </p>
          <p className="mt-2 leading-6 text-slate-600">
            To są odczytane możliwości, a nie decyzja, gdzie trafi element dokumentu.
          </p>
        </>
      ) : null}
    </div>
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

function DevTargetDetails({ discovery }: { discovery: ContentTargetDiscovery }) {
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
  return <>
    <p className="mt-3 font-semibold text-ink">{discovery.label}</p>
    <p className="mt-2 leading-6">{discovery.reason}</p>
    {target ? <div className="mt-3 rounded-lg bg-slate-50 p-3">
      <p className="font-semibold text-ink">Zaobserwowana strona robocza</p>
      <p className="mt-1 break-all leading-6">{target.url}</p>
      <p className="mt-2 leading-6">To {target.post_type === "post" ? "artykuł" : "strona"}. Status na dev: {wordpressStatus(target.post_status)}. {target.target_contract.authoring_surface ? "WILQ odczytał układ ACF Flexible Content." : "Nie rozpoznano układu treści na tym obiekcie."}</p>
    </div> : null}
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

function Tab({ active, children, onClick }: { active: boolean; children: string; onClick: () => void }) {
  return <button type="button" className={`border-b-2 px-4 py-3 text-sm font-semibold ${active ? "border-action text-action" : "border-transparent text-slate-600 hover:text-ink"}`} onClick={onClick}>{children}</button>;
}

function StatusCard({ label, value }: { label: string; value: string }) {
  return <div className="mt-4 rounded-xl bg-slate-50 p-3"><p className="text-sm font-semibold text-ink">{label}</p><p className="mt-1 text-sm text-slate-700">{value}</p></div>;
}

function outlineLead(view: View) {
  return { source: "To, co jest dziś widoczne na publicznej stronie.", document: "Układ przygotowanej wersji dokumentu.", comparison: "Zaobserwowane zmiany nagłówków i fragmentów, bez oceny wyglądu ani znaczenia." }[view];
}

function outline(view: View, workspace: ContentDocumentWorkspace): string[] {
  if (view === "source") return workspace.source_snapshot.ordered_sections.map((section) => section.heading);
  if (view === "document") return workspace.canonical_document.preview?.sections.map((section) => section.heading) ?? [workspace.canonical_document.label];
  return workspace.comparison.items.map((item) => item.document_heading ?? item.source_heading ?? "Element bez nazwy");
}

function CurrentSource({ workspace }: { workspace: ContentDocumentWorkspace }) {
  return <div data-testid="content-source-snapshot">
    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-action">Obecna strona</p>
    <h2 className="mt-2 text-2xl font-semibold text-ink">{workspace.source_snapshot.title ?? "Publiczny materiał źródłowy"}</h2>
    <p className="mt-3 text-sm leading-6 text-slate-700">{workspace.source_snapshot.reason}</p>
    {workspace.source_snapshot.lead ? <p className="mt-6 border-l-2 border-action/40 pl-4 text-base leading-7 text-slate-700">{workspace.source_snapshot.lead}</p> : null}
    <div className="mt-7 space-y-5">
      {workspace.source_snapshot.ordered_sections.map((section, index) => (
        <section key={`${section.heading}-${index}`} className="border-t border-line pt-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{index + 1}. fragment obecnej strony</p>
          <h3 className="mt-2 text-lg font-semibold text-ink">{section.heading}</h3>
          <p className="mt-3 whitespace-pre-line text-sm leading-7 text-slate-700">{section.excerpt ?? "WILQ odczytał ten nagłówek, ale nie ma bezpiecznego wycinka tekstu do pokazania."}</p>
        </section>
      ))}
    </div>
  </div>;
}

function CanonicalDocument({ workspace }: { workspace: ContentDocumentWorkspace }) {
  const preview = workspace.canonical_document.preview;
  if (!preview) return <>
    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-wait">Nowa wersja</p>
    <h2 className="mt-2 text-2xl font-semibold text-ink">{workspace.canonical_document.label}</h2>
    <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-700">{workspace.canonical_document.reason}</p>
    <div className="mt-6 rounded-xl border border-wait/25 bg-wait/5 p-4 text-sm leading-6 text-slate-700"><p className="font-semibold text-ink">Następny krok</p><p className="mt-1">{workspace.next_action.reason}</p></div>
  </>;
  return <>
    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-wait">Nowa wersja</p>
    <h2 className="mt-2 text-2xl font-semibold text-ink">{preview.h1 ?? preview.title}</h2>
    {preview.lead ? <p className="mt-4 text-base leading-7 text-slate-700">{preview.lead}</p> : null}
    <p className="mt-4 text-sm text-slate-600">{preview.sections.length} sekcji · {preview.faq_count} pytań i odpowiedzi · {preview.cta_count} wezwań do działania</p>
    <div className="mt-7 space-y-7">{preview.sections.map((section) => <section key={section.section_id ?? section.heading} className="border-t border-line pt-6"><h3 className="text-xl font-semibold text-ink">{section.heading}</h3><p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-700">{section.body_markdown}</p></section>)}</div>
  </>;
}

function DocumentLineage({ workspace }: { workspace: ContentDocumentWorkspace }) {
  const lineage = workspace.document_lineage;
  return <details className="mt-3 rounded-xl border border-line p-3 text-sm text-slate-700">
    <summary className="cursor-pointer font-semibold text-ink">Materiały użyte w dokumencie</summary>
    <p className="mt-3 leading-6">{lineage.reason}</p>
    {lineage.knowledge_cards.length ? <ul className="mt-3 space-y-3">
      {lineage.knowledge_cards.map((card) => <li key={card.id} className="rounded-lg bg-slate-50 p-3">
        <p className="font-semibold text-ink">{card.title}</p>
        <p className="mt-1 leading-6">{card.summary}</p>
      </li>)}
    </ul> : null}
    {lineage.source_material_ids.length ? <p className="mt-3 leading-6">Zapisane materiały źródłowe: {lineage.source_material_ids.length}.</p> : null}
    {lineage.unresolved_knowledge_card_ids.length ? <p className="mt-3 leading-6 text-wait">Nie można obecnie odczytać {lineage.unresolved_knowledge_card_ids.length} przypisanych kart wiedzy.</p> : null}
  </details>;
}

function Comparison({ workspace }: { workspace: ContentDocumentWorkspace }) {
  if (workspace.comparison.status === "unavailable") return <><p className="text-xs font-semibold uppercase tracking-[0.14em] text-action">Zmiany w treści</p><h2 className="mt-2 text-2xl font-semibold text-ink">Nie ma jeszcze czego zestawić</h2><p className="mt-3 text-sm leading-6 text-slate-700">{workspace.comparison.reason}</p></>;
  return <>
    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-action">Zmiany w treści</p>
    <h2 className="mt-2 text-2xl font-semibold text-ink">Co zmienia się między wersjami</h2>
    <p className="mt-3 text-sm leading-6 text-slate-700">{workspace.comparison.reason} WILQ zestawia tylko bezpośrednio zaobserwowane nagłówki i fragmenty — nie porównuje wyglądu strony ani znaczenia tekstu.</p>
    <div className="mt-6 space-y-4">{workspace.comparison.items.map((item, index) => <article key={`${item.status}-${item.source_heading ?? item.document_heading}-${index}`} className="rounded-xl border border-line p-4"><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{comparisonLabel(item.status)}</p><div className="mt-3 grid gap-4 lg:grid-cols-2"><ComparisonSide label="Obecna strona" heading={item.source_heading} excerpt={item.source_excerpt} empty="Brak bezpośrednio rozpoznanego elementu." /><ComparisonSide label="Nowa wersja" heading={item.document_heading} excerpt={item.document_excerpt} empty="Brak bezpośrednio rozpoznanego elementu." /></div><p className="mt-4 text-sm leading-6 text-slate-600">{item.reason}</p></article>)}</div>
  </>;
}

function ComparisonSide({ label, heading, excerpt, empty }: { label: string; heading: string | null | undefined; excerpt: string | null | undefined; empty: string }) {
  return <section className="rounded-lg bg-slate-50 p-3"><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>{heading ? <h3 className="mt-2 text-sm font-semibold text-ink">{heading}</h3> : null}<p className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-700">{excerpt ?? empty}</p></section>;
}

function comparisonLabel(status: "same_heading" | "source_only" | "document_only") {
  return { same_heading: "ten sam nagłówek", source_only: "tylko na obecnej stronie", document_only: "tylko w nowej wersji" }[status];
}

function sourceStatus(status: "available" | "partial" | "unavailable") {
  return { available: "materiał dostępny", partial: "materiał częściowy", unavailable: "materiał niedostępny" }[status];
}

function documentStatus(status: "not_created" | "unreviewed" | "needs_changes" | "approved" | "rejected" | "deferred") {
  return { not_created: "nie utworzono", unreviewed: "czeka na review", needs_changes: "wymaga zmian", approved: "zatwierdzony", rejected: "odrzucony", deferred: "odłożony" }[status];
}
