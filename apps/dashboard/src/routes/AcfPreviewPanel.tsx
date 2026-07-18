import { FileText } from "lucide-react";

import type {
  ContentWorkItemWordPressAuthoringPayloadPreviewResponse
} from "../lib/api";

type AcfFieldPreview =
  ContentWorkItemWordPressAuthoringPayloadPreviewResponse["preview_result"]["sections"][number]["field_previews"][number];

type AcfPreviewPanelProps = {
  result: ContentWorkItemWordPressAuthoringPayloadPreviewResponse["preview_result"] | null;
  safetyText: string;
};

export function AcfPreviewPanel({ result, safetyText }: AcfPreviewPanelProps) {
  const firstSection = result?.sections[0] ?? null;
  const fieldPreviews = firstSection?.field_previews ?? [];
  const filledFields =
    firstSection && !fieldPreviews.length
      ? Object.entries(firstSection.field_values).filter(([, value]) => Boolean(value))
      : [];

  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="flex items-start gap-3">
        <div className="rounded-md border border-line bg-surface p-2 text-action">
          <FileText aria-hidden="true" size={18} />
        </div>
        <div>
          <h2 className="text-sm font-semibold text-ink">Mapowanie ACF</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">{safetyText}</p>
          {result?.page_assets ? (
            <div className="mt-3 rounded-md border border-line bg-surface p-3 text-sm text-slate-700">
              <div className="text-xs uppercase tracking-normal text-slate-500">Page assets zachowane w dry-runie</div>
              <dl className="mt-2 grid gap-2 sm:grid-cols-2">
                <div><dt className="font-medium text-ink">Tytuł / H1</dt><dd className="mt-1 text-xs leading-5">{result.page_assets.wordpress_title} · {result.page_assets.h1}</dd></div>
                <div><dt className="font-medium text-ink">Meta</dt><dd className="mt-1 text-xs leading-5">{result.page_assets.meta_write_status === "mapped" ? "mapowanie potwierdzone" : "przekazanie ręczne — mapowanie niepotwierdzone"}</dd></div>
              </dl>
              {result.page_assets.metadata_blockers.map((blocker) => (
                <p key={blocker.code} className="mt-2 rounded-md bg-wait/10 p-2 text-xs leading-5 text-slate-700">{blocker.label}: {blocker.next_step}</p>
              ))}
            </div>
          ) : null}
          {firstSection ? (
            <div className="mt-3 space-y-3 text-sm text-slate-700">
              <div className="rounded-md border border-line bg-surface p-3">
                <div className="text-xs uppercase tracking-normal text-slate-500">Wybrany layout</div>
                <div className="mt-1 font-semibold text-ink">
                  {firstSection.layout_label} ({firstSection.layout_name})
                </div>
                <div className="mt-1 text-xs text-slate-500">Sekcja: {firstSection.section_heading}</div>
              </div>
              {fieldPreviews.length ? (
                <div className="rounded-md border border-line bg-surface p-3">
                  <div className="text-xs uppercase tracking-normal text-slate-500">Mapowanie pól ACF</div>
                  <AcfFieldPreviewList fields={fieldPreviews.slice(0, 4)} />
                </div>
              ) : filledFields.length ? (
                <div className="rounded-md border border-line bg-surface p-3">
                  <div className="text-xs uppercase tracking-normal text-slate-500">Pola, które WILQ wypełni</div>
                  <dl className="mt-2 space-y-2">
                    {filledFields.slice(0, 4).map(([fieldName, value]) => (
                      <div key={fieldName}>
                        <dt className="font-medium text-ink">{fieldName}</dt>
                        <dd className="mt-1 whitespace-pre-line text-xs leading-5 text-slate-600">{value}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}

export function AcfFieldPreviewList({ fields, depth = 0 }: { fields: AcfFieldPreview[]; depth?: number }) {
  return (
    <dl className={`${depth ? "mt-2 border-l border-line pl-3" : "mt-2"} space-y-2`}>
      {fields.map((field) => (
        <div key={`${field.field_name}-${field.field_type}-${depth}`}>
          <dt className="font-medium text-ink">{field.field_label} ({field.field_name})</dt>
          {field.value_preview ? <dd className="mt-1 whitespace-pre-line text-xs leading-5 text-slate-600">{field.value_preview}</dd> : null}
          {field.note ? <dd className="mt-1 text-xs leading-5 text-slate-500">{field.note}</dd> : null}
          {field.row_candidates.length ? (
            <dd className="mt-2 space-y-2">
              {field.row_candidates.slice(0, 2).map((candidate) => (
                <div key={`${field.field_name}-${candidate.row_type}-${candidate.row_label}`} className="rounded-md border border-line bg-white p-2">
                  <div className="text-xs font-semibold text-ink">Kandydat wiersza ACF: {candidate.row_label}</div>
                  <div className="mt-1 text-xs leading-5 text-slate-500">Do ręcznego przeglądu. {candidate.note}</div>
                  {candidate.field_values.length ? (
                    <dl className="mt-2 space-y-1">
                      {candidate.field_values.slice(0, 4).map((value) => (
                        <div key={`${candidate.row_label}-${value.field_name}`}>
                          <dt className="text-xs font-medium text-ink">{value.field_label} ({value.field_name})</dt>
                          {value.value_preview ? <dd className="mt-0.5 whitespace-pre-line text-xs leading-5 text-slate-600">{value.value_preview}</dd> : value.note ? <dd className="mt-0.5 text-xs leading-5 text-slate-500">{value.note}</dd> : null}
                        </div>
                      ))}
                    </dl>
                  ) : null}
                  {candidate.evidence_ids.length ? <div className="mt-2 text-xs text-slate-500">Dowody: {candidate.evidence_ids.slice(0, 3).join(", ")}</div> : null}
                </div>
              ))}
            </dd>
          ) : null}
          {field.nested_values.length && depth < 2 ? <dd><AcfFieldPreviewList fields={field.nested_values.slice(0, 6)} depth={depth + 1} /></dd> : null}
        </div>
      ))}
    </dl>
  );
}
