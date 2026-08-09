import type { ReactNode } from "react";

import type { ContentNewPageBriefWorkspace } from "../../lib/api";

export function NewPageShell({ onReturn, children }: { onReturn: () => void; children: ReactNode }) {
  return <main className="min-h-screen bg-[radial-gradient(circle_at_top_right,_#e7f8ee,_transparent_32%),linear-gradient(180deg,_#fbfdff_0%,_#ffffff_58%)] px-4 py-5 lg:px-7 lg:py-8" data-testid="content-workflow-new-page-brief"><div className="mx-auto max-w-4xl"><button type="button" className="text-sm font-semibold text-action" onClick={onReturn}>← Wróć do wyboru pracy</button><section className="mt-6 rounded-2xl border border-emerald-200 bg-white p-6 shadow-[0_18px_48px_-36px_rgba(15,23,42,0.55)] lg:p-9">{children}</section></div></main>;
}

export function BriefField({ label, value, onChange, placeholder, multiline = false }: { label: string; value: string; onChange: (value: string) => void; placeholder: string; multiline?: boolean }) {
  const className = "mt-2 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-ink outline-none focus:border-action focus:bg-white focus:ring-4 focus:ring-action/10";
  return <label className="block text-sm font-semibold text-ink"><span>{label}</span>{multiline ? <textarea required value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} rows={3} className={className} /> : <input required value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} className={className} />}</label>;
}

export function InfoTile({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl border border-slate-200 bg-slate-50 p-4"><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p><p className="mt-2 text-sm leading-6 text-slate-700">{value}</p></div>;
}

export function EvidenceIds({ evidenceIds, label = "Dowody" }: { evidenceIds: string[]; label?: string }) {
  const count = evidenceIds.length;
  const lastTwoDigits = count % 100;
  const endsWithFew = count % 10 >= 2 && count % 10 <= 4;
  const usesFewForm = endsWithFew && !(lastTwoDigits >= 12 && lastTwoDigits <= 14);
  const summary = count === 1 ? "1 dowód źródłowy" : usesFewForm ? `${count} dowody źródłowe` : `${count} dowodów źródłowych`;
  return count ? <p className="mt-2 text-[11px] leading-5 text-slate-500">{label}: {summary}</p> : <p className="mt-2 text-[11px] leading-5 text-wait">{label}: brak potwierdzonego dowodu</p>;
}

export function overlapMatchLabel(kind: ContentNewPageBriefWorkspace["overlap_guard"]["candidates"][number]["match_kind"]) {
  if (kind === "same_title") return "Podstawa dopasowania: ten sam tytuł strony.";
  if (kind === "shared_intent") return "Podstawa dopasowania: wspólna intencja wyszukiwania.";
  return "Podstawa dopasowania: wspólna usługa.";
}

export function overlapEmptyStateCopy(disposition: ContentNewPageBriefWorkspace["overlap_guard"]["disposition"]) {
  if (disposition === "no_conflict") return "Nie znaleziono strony z bezpośrednim pokryciem. Poniżej są dowody z katalogu sprawdzonego dla tego briefu.";
  return "Nie ma potwierdzonych danych pozwalających ocenić pokrycie.";
}
