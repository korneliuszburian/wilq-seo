import { FileText } from "lucide-react";

import type { ContentWorkItemStructuredDraftPreviewResponse } from "../lib/api";

type StructuredDraftPreviewPanelProps = {
  result: ContentWorkItemStructuredDraftPreviewResponse["preview_result"] | null;
  safetyText: string;
};

export function StructuredDraftPreviewPanel({ result, safetyText }: StructuredDraftPreviewPanelProps) {
  const preview = result?.preview;
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="flex items-start gap-3">
        <div className="rounded-md border border-line bg-surface p-2 text-action">
          <FileText aria-hidden="true" size={18} />
        </div>
        <div>
          <h2 className="text-sm font-semibold text-ink">Podgląd treści</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">{safetyText}</p>
          {preview ? (
            <div className="mt-3 space-y-3 text-sm text-slate-700">
              <div className="rounded-md border border-line bg-surface p-3">
                <div className="text-xs uppercase tracking-normal text-slate-500">Tytuł</div>
                <div className="mt-1 font-semibold text-ink">{preview.title}</div>
              </div>
              {preview.sections.slice(0, 2).map((section) => (
                <div key={section.heading} className="rounded-md border border-line bg-surface p-3">
                  <div className="font-semibold text-ink">{section.heading}</div>
                  <p className="mt-2 whitespace-pre-line leading-6">{section.body_markdown}</p>
                  <div className="mt-2 text-xs text-slate-500">
                    Dowody sekcji: {section.evidence_ids.join(", ")}
                  </div>
                </div>
              ))}
              {preview.human_review_checklist.length ? (
                <div className="rounded-md border border-line bg-surface p-3">
                  <div className="text-xs uppercase tracking-normal text-slate-500">Do sprawdzenia przez człowieka</div>
                  <ul className="mt-2 space-y-1">
                    {preview.human_review_checklist.map((item) => <li key={item}>{item}</li>)}
                  </ul>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
