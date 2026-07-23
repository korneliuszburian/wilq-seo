import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { getContentWorkItemEditorialIntegrity } from "../lib/api";
import type { ContentEditorialIntegrityReport as IntegrityReport } from "../lib/api";

export function ContentEditorialIntegrityReport({
  workItemId,
  revisionId
}: {
  workItemId: string;
  revisionId: string;
}) {
  const [opened, setOpened] = useState(false);
  const integrity = useQuery({
    queryKey: ["content-workflow", "work-item", workItemId, "draft-revisions", revisionId, "editorial-integrity"],
    queryFn: () => getContentWorkItemEditorialIntegrity(workItemId, revisionId),
    enabled: opened,
    staleTime: 30_000
  });

  return (
    <section className="mt-4 rounded-xl border border-line bg-slate-50 p-4" data-testid="content-editorial-integrity">
      <p className="text-sm font-semibold text-ink">Integralność redakcyjna</p>
      <p className="mt-1 text-sm leading-6 text-slate-700">Porównaj dokładne rewizje. Raport pokazuje twardą integralność, różnice leksykalne i sygnały redakcyjne, ale nie ocenia automatycznie zachowania znaczenia.</p>
      {!opened ? <button type="button" className="mt-3 rounded-md border border-action/30 px-3 py-2 text-sm font-semibold text-action" onClick={() => setOpened(true)}>Sprawdź zmiany względem wersji bazowej</button> : null}
      {integrity.isLoading ? <p className="mt-3 text-sm text-slate-700">Porównuję dokładne rewizje…</p> : null}
      {integrity.error ? <p className="mt-3 text-sm font-semibold text-wait">Nie udało się odczytać raportu integralności.</p> : null}
      {integrity.data ? <IntegrityReportView report={integrity.data} /> : null}
    </section>
  );
}

function IntegrityReportView({ report }: { report: IntegrityReport }) {
  const lexicalBySection = report.protected_content_units.reduce<Record<string, typeof report.protected_content_units>>((sections, unit) => {
    (sections[unit.section_id] ??= []).push(unit);
    return sections;
  }, {});
  const changedLexicalUnits = report.protected_content_units.filter((unit) => unit.status !== "preserved");
  const mismatches = report.representation_alignment.filter((item) => item.status === "mismatch");
  const changedInvariants = Object.entries(report.structural_invariants).filter(([, value]) => !value);

  return <div className="mt-3 space-y-3 text-sm text-slate-700">
    <p className="font-semibold text-ink">{integrityLabel(report.result)}</p>
    <p>Porównanie: {revisionLabel(report.baseline_revision)} → {report.direct_parent_revision ? revisionLabel(report.direct_parent_revision) : "brak parenta"} → {revisionLabel(report.child_revision)}.</p>
    <div className="grid gap-2 sm:grid-cols-2">
      <StatusCard label="Body i HTML" value={mismatches.length ? `${mismatches.length} niespójnych sekcji` : "zgodne"} tone={mismatches.length ? "wait" : "ok"} />
      <StatusCard label="Struktura dokumentu" value={changedInvariants.length ? `${changedInvariants.length} zmian do sprawdzenia` : "bez zmian"} tone={changedInvariants.length ? "wait" : "ok"} />
      <StatusCard label="Zmiany leksykalne" value={changedLexicalUnits.length ? `${changedLexicalUnits.length} fragmentów do oceny` : "brak"} tone={changedLexicalUnits.length ? "wait" : "ok"} />
      <StatusCard label="Sygnały redakcyjne" value={report.lint_signals.length ? `${report.lint_signals.length} sygnał(y)` : "brak"} tone={report.lint_signals.length ? "wait" : "ok"} />
    </div>
    {report.human_review ? <p className="rounded-lg border border-action/20 bg-action/5 p-3"><span className="font-semibold text-ink">Human review tej rewizji: {reviewLabel(report.human_review.decision)}.</span> Zapisane przez {report.human_review.reviewed_by}. Sygnały leksykalne i lint nie unieważniają tej decyzji.</p> : <p className="rounded-lg border border-line bg-white p-3">Brak zapisanego human review dla dokładnie tej rewizji.</p>}
    <details className="rounded-lg border border-line bg-white p-3">
      <summary className="cursor-pointer font-semibold text-ink">Różnice, konkretne elementy i sygnały</summary>
      <p className="mt-3">Obserwowany scope: {report.observed_scope.fields.length ? report.observed_scope.fields.join(", ") : "brak zmian pól"}; sekcje: {report.observed_scope.section_ids.length || "brak"}. To obserwacja historii, nie zapis autoryzowanego scope’u.</p>
      <h3 className="mt-4 font-semibold text-ink">Struktura dokumentu</h3>
      <ul className="mt-2 space-y-1">{Object.entries(report.structural_invariants).map(([name, unchanged]) => <li key={name}>{structuralLabel(name)}: {unchanged ? "bez zmian" : "zaobserwowano zmianę — wymaga sprawdzenia"}</li>)}</ul>
      <h3 className="mt-4 font-semibold text-ink">Body i HTML</h3>
      <ul className="mt-2 space-y-2">
        {report.representation_alignment.map((item) => <li key={item.section_id} className="rounded border border-line p-2"><span className="font-medium text-ink">{item.section_heading}:</span> {item.status === "aligned" ? "zgodne" : "niespójne"}<details className="mt-1 text-xs text-slate-500"><summary>Identyfikatory techniczne</summary><p>Źródło: {item.source_body_sha256}; HTML: {item.rendered_html_sha256 ?? "brak"}.</p></details></li>)}
      </ul>
      <h3 className="mt-4 font-semibold text-ink">Przed → po: różnice leksykalne</h3>
      <p className="mt-1">To kandydaci do oceny człowieka, nie automatyczny werdykt o utracie znaczenia.</p>
      {changedLexicalUnits.length ? <div className="mt-2 space-y-3">{Object.entries(lexicalBySection).map(([sectionId, units]) => {
        const changes = units.filter((unit) => unit.status !== "preserved");
        return changes.length ? <div key={sectionId} className="rounded border border-line p-3"><p className="font-medium text-ink">{changes[0]?.section_heading}</p>{changes.map((unit) => <div key={unit.unit_id} className="mt-2"><p><span className="font-medium">Przed:</span> {unit.before_excerpt}</p><p><span className="font-medium">Po:</span> {unit.after_excerpt ?? "Brak podobnego fragmentu leksykalnego."}</p></div>)}</div> : null;
      })}</div> : <p className="mt-2">Brak leksykalnych różnic do pokazania.</p>}
      <h3 className="mt-4 font-semibold text-ink">Sygnały redakcyjne</h3>
      {report.lint_signals.length ? <ul className="mt-2 list-disc space-y-1 pl-5">{report.lint_signals.map((signal) => <li key={signal.code}>{signal.reason}</li>)}</ul> : <p className="mt-2">Nie wykryto deterministycznych sygnałów redakcyjnych.</p>}
      <details className="mt-4 text-xs text-slate-500"><summary>Pełne identyfikatory rewizji i digesty</summary><p>{revisionTechnicalLabel("Baseline", report.baseline_revision)}</p>{report.direct_parent_revision ? <p>{revisionTechnicalLabel("Direct parent", report.direct_parent_revision)}</p> : null}<p>{revisionTechnicalLabel("Kandydat", report.child_revision)}</p></details>
    </details>
  </div>;
}

function StatusCard({ label, value, tone }: { label: string; value: string; tone: "ok" | "wait" }) {
  return <div className="rounded-lg border border-line bg-white p-3"><p className="font-medium text-ink">{label}</p><p className={tone === "ok" ? "mt-1 text-emerald-700" : "mt-1 text-wait"}>{value}</p></div>;
}

function revisionLabel(revision: IntegrityReport["child_revision"]) {
  return `R${revision.revision_number}`;
}

function revisionTechnicalLabel(label: string, revision: IntegrityReport["child_revision"]) {
  return `${label}: ${revision.revision_id} · ${revision.content_digest}`;
}

function structuralLabel(name: string) {
  return {
    section_ids_unchanged: "Identyfikatory sekcji",
    section_order_unchanged: "Kolejność sekcji",
    headings_unchanged: "Nagłówki",
    title_unchanged: "Tytuł",
    faq_unchanged: "FAQ",
    cta_semantics_unchanged: "CTA",
    links_unchanged: "Linki",
    evidence_lineage_unchanged: "Lineage dowodów"
  }[name] ?? name;
}

function reviewLabel(decision: "approved" | "needs_changes" | "rejected" | "deferred") {
  return { approved: "zatwierdzone", needs_changes: "wymaga zmian", rejected: "odrzucone", deferred: "odłożone" }[decision];
}

function integrityLabel(result: "integrity_ok" | "invalid_representation" | "structural_change_observed") {
  return {
    integrity_ok: "Twarda integralność zachowana",
    invalid_representation: "Błędna reprezentacja body i HTML",
    structural_change_observed: "Zaobserwowano zmianę strukturalną"
  }[result];
}
