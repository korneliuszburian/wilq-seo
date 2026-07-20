import { ShieldCheck, Stamp } from "lucide-react";
import { useMemo, useState } from "react";

import {
  type ContentWorkItemWordPressAuthoringPayloadPreviewResponse,
  type ContentWorkItemWordPressDraftExecutionRequest,
  type WordPressAuthoringProfile
} from "../lib/api";
import { AcfFieldPreviewList } from "./AcfPreviewPanel";
import { ContentPublicInventoryPanel } from "./ContentPublicInventoryPanel";
import {
  defaultSectionBody,
  sectionOverrideKey
} from "./contentWorkflowDraftSectionModel";
import type { ContentWorkflowSnapshot } from "./contentWorkflowRuntime";
import type {
  WordPressAuthoringProfileQuery,
  WordPressDraftActivationPacketQuery
} from "./contentWorkflowQueries";
import { planningInventorySourceLabel } from "./ContentPlanningReviewPanel";

type ContentSectionWritingActions = {
  acfPreviewPending: boolean;
  acfPreviewResult: ContentWorkItemWordPressAuthoringPayloadPreviewResponse["preview_result"] | null;
  executionPending: boolean;
  runAcfPreview: () => void;
  runExecutionDryRunWithSections: (
    sections: WordPressDraftSectionOverride[]
  ) => void;
};

type WordPressDraftSectionOverride = NonNullable<
  ContentWorkItemWordPressDraftExecutionRequest["section_overrides"]
>[number];

function unique(values: string[]) {
  return [...new Set(values)];
}

export function ContentSectionWritingWorkbench({
  actions,
  authoringProfile,
  data,
  draftActivationPacket
}: {
  actions: ContentSectionWritingActions;
  authoringProfile: WordPressAuthoringProfileQuery;
  data: ContentWorkflowSnapshot;
  draftActivationPacket: WordPressDraftActivationPacketQuery;
}) {
  const item = data.preflight.item;
  const draft = data.draftPackage.draft_package_result.draft_package;
  const handoff = data.wordpressHandoff.handoff_result.handoff;
  const publicSections = item.wordpress_section_headings ?? [];
  const draftSections = useMemo(() => draft?.sections ?? [], [draft]);
  const editableSections = useMemo(() => draftSections.slice(0, 4), [draftSections]);
  const sectionDraftDefaults = useMemo(
    () =>
      Object.fromEntries(
        editableSections.map((section) => [
          sectionOverrideKey(section.heading),
          defaultSectionBody(section)
        ])
      ),
    [editableSections]
  );
  const [sectionEditorState, setSectionEditorState] = useState<{
    draftId: string | null;
    texts: Record<string, string>;
  }>({ draftId: null, texts: {} });
  const draftEditorId = draft?.id ?? null;
  const sectionTexts =
    sectionEditorState.draftId === draftEditorId
      ? sectionEditorState.texts
      : sectionDraftDefaults;
  const sourceTitle = item.wordpress_title_or_h1 ?? draft?.title ?? item.topic;
  const sectionInventoryAvailable =
    item.wordpress_section_inventory_status === "available" && publicSections.length > 0;
  const profile: WordPressAuthoringProfile | null = authoringProfile.data ?? null;
  const draftReadback = draftActivationPacket.data?.draft_readback ?? null;
  const dryRunReady = Boolean(
    draftActivationPacket.data?.dry_run_ready &&
      draftActivationPacket.data.execution_blockers.length === 0
  );
  const firstAcfSection = actions.acfPreviewResult?.sections[0] ?? null;
  const firstAcfFields = firstAcfSection?.field_previews ?? [];
  const sourceHref =
    item.source_public_url ?? item.final_canonical_url ?? item.intended_final_url ?? undefined;
  const inventorySourceLabel = planningInventorySourceLabel(
    item.wordpress_acf_section_inventory_status,
    item.wordpress_content_inventory_status
  );
  const canPrepareAcf = Boolean(profile && draft && handoff && !actions.acfPreviewResult);
  const sectionOverrides = editableSections
    .map((section) => ({
      heading: section.heading,
      body_markdown:
        sectionTexts[sectionOverrideKey(section.heading)] ?? defaultSectionBody(section),
      evidence_ids: unique(section.evidence_ids)
    }))
    .filter((section) => section.body_markdown.trim().length > 0);

  return (
    <section className="mb-6 overflow-hidden rounded-md border border-line bg-white shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-line bg-surface px-4 py-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-normal text-action">Roboczy plan treści</p>
          <h2 className="mt-1 text-base font-semibold text-ink">Plan treści i mapowanie</h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-700">
            Zestawienie tego, co jest na publicznej stronie, co ma wejść do szkicu i jak można to przełożyć na dev WordPress. Źródło tej strony: {inventorySourceLabel}.
          </p>
        </div>
        <span className="rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold text-ink">
          {draftReadback?.status === "available" ? "dev draft odczytany" : "dev draft do sprawdzenia"}
        </span>
      </div>
      <div className="grid gap-4 p-4 xl:grid-cols-[1.05fr_1fr_0.95fr]">
        <ContentPublicInventoryPanel
          sourceTitle={sourceTitle}
          sourceHref={sourceHref}
          sectionInventoryAvailable={sectionInventoryAvailable}
          publicSections={publicSections}
        />
        <div className="rounded-md border border-line bg-white p-4">
          <div className="flex items-start gap-3"><div className="rounded-md border border-line bg-surface p-2 text-success"><ShieldCheck aria-hidden="true" size={18} /></div><div><h3 className="text-sm font-semibold text-ink">Tekst sekcji do szkicu</h3><p className="mt-2 text-sm leading-6 text-slate-700">{draftSections.length ? "Przepisz konkretne sekcje tutaj i sprawdź podgląd przed centralną akcją zapisu." : "Szkic nie ma jeszcze sekcji. Najpierw przygotuj paczkę szkicu."}</p></div></div>
          {editableSections.length ? <div className="mt-4 space-y-3 text-sm leading-6 text-slate-700">{editableSections.map((section, index) => { const key = sectionOverrideKey(section.heading); return <label key={`${section.heading}-${index}`} className="block rounded-md border border-line bg-surface p-3"><p className="font-semibold text-ink">{index + 1}. {section.heading}</p><textarea className="mt-3 min-h-32 w-full resize-y rounded-md border border-line bg-white p-3 text-sm leading-6 text-ink outline-none focus:border-action focus:ring-2 focus:ring-action/20" value={sectionTexts[key] ?? defaultSectionBody(section)} onChange={(event) => setSectionEditorState({ draftId: draftEditorId, texts: { ...sectionTexts, [key]: event.target.value } })} aria-label={`Tekst sekcji ${section.heading}`} />{section.draft_notes.length ? <p className="mt-2 text-xs leading-5 text-slate-500">Wskazówka: {section.draft_notes[0]}</p> : null}</label>; })}<div className="rounded-md border border-action/20 bg-action/5 p-3"><p className="text-sm leading-6 text-slate-700">To sprawdzenie bez zapisu obejmuje wyłącznie payload i gotowość szkicu WordPress. Nie ocenia jakości ani poprawności tekstu.</p><div className="mt-3 flex flex-wrap gap-3"><button type="button" onClick={() => actions.runExecutionDryRunWithSections(sectionOverrides)} disabled={!sectionOverrides.length || !dryRunReady || actions.executionPending} className="inline-flex h-9 items-center rounded-md border border-line bg-white px-3 text-sm font-semibold text-ink disabled:cursor-not-allowed disabled:opacity-60">{actions.executionPending ? "Sprawdzam payload..." : "Sprawdź payload WordPress bez zapisu"}</button><button type="button" onClick={() => setSectionEditorState({ draftId: draftEditorId, texts: sectionDraftDefaults })} className="inline-flex h-9 items-center rounded-md border border-line bg-white px-3 text-sm font-semibold text-ink">Przywróć tekst z briefu</button></div><p className="mt-2 text-xs leading-5 text-slate-500">Ten ekran nie wykonuje bezpośredniego zapisu do WordPressa.</p></div></div> : null}
        </div>
        <div className="rounded-md border border-line bg-white p-4"><div className="flex items-start gap-3"><div className="rounded-md border border-line bg-surface p-2 text-action"><Stamp aria-hidden="true" size={18} /></div><div><h3 className="text-sm font-semibold text-ink">Dev WordPress i ACF</h3><p className="mt-2 text-sm leading-6 text-slate-700">{firstAcfSection ? "Mapowanie pokazuje, do których pól można przepiąć szkic." : `${profile?.acf.layouts.length ?? 0} layoutów ACF jest dostępnych do przygotowania mapowania.`}</p></div></div><div className="mt-4 space-y-3 text-sm leading-6 text-slate-700">{draftReadback?.status === "available" ? <div className="rounded-md border border-success/25 bg-success/5 p-3"><p className="font-semibold text-success">Szkic istnieje na devie</p><p className="mt-1 font-semibold text-ink">{draftReadback.title || "Szkic bez tytułu"}</p><p className="mt-1 text-xs text-slate-600">{draftReadback.content_word_count ?? 0} słów · status {draftReadback.post_status || "draft"}</p>{draftReadback.link ? <a href={draftReadback.link} target="_blank" rel="noreferrer" className="mt-2 inline-flex text-sm font-semibold text-action">Otwórz szkic na dev</a> : null}</div> : <div className="rounded-md border border-line bg-surface p-3">Szkic na devie nie jest jeszcze potwierdzony. Najpierw utwórz albo odczytaj draft.</div>}{firstAcfSection ? <div className="rounded-md border border-line bg-surface p-3"><p className="text-xs uppercase tracking-normal text-slate-500">Wybrany layout</p><p className="mt-1 font-semibold text-ink">{firstAcfSection.layout_label} ({firstAcfSection.layout_name})</p>{firstAcfFields.length ? <AcfFieldPreviewList fields={firstAcfFields.slice(0, 3)} /> : null}</div> : <button type="button" onClick={() => actions.runAcfPreview()} disabled={!canPrepareAcf || actions.acfPreviewPending} className="inline-flex h-9 items-center rounded-md bg-action px-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60">{actions.acfPreviewPending ? "Przygotowuję ACF" : "Przygotuj mapowanie sekcji ACF"}</button>}</div></div>
      </div>
    </section>
  );
}
