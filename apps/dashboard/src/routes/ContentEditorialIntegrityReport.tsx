import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { getContentWorkItemEditorialIntegrity } from "../lib/api";

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
      <p className="mt-1 text-sm leading-6 text-slate-700">Porównaj tę rewizję z wersją bazową. Raport wskazuje różnice i sygnały do oceny, ale niczego nie poprawia ani nie zatwierdza.</p>
      {!opened ? <button type="button" className="mt-3 rounded-md border border-action/30 px-3 py-2 text-sm font-semibold text-action" onClick={() => setOpened(true)}>Sprawdź zmiany względem wersji bazowej</button> : null}
      {integrity.isLoading ? <p className="mt-3 text-sm text-slate-700">Porównuję dokładne rewizje…</p> : null}
      {integrity.error ? <p className="mt-3 text-sm font-semibold text-wait">Nie udało się odczytać raportu integralności.</p> : null}
      {integrity.data ? <div className="mt-3 space-y-3 text-sm text-slate-700">
        <p className="font-semibold text-ink">{integrityLabel(integrity.data.result)}</p>
        <p>Wersja bazowa: {integrity.data.baseline_revision.revision_id.slice(0, 12)} · kandydat: {integrity.data.child_revision.revision_id.slice(0, 12)}</p>
        <p>{integrity.data.human_readable_diff}</p>
        <details className="rounded-lg border border-line bg-white p-3">
          <summary className="cursor-pointer font-semibold text-ink">Różnice, konkretne elementy i sygnały</summary>
          <p className="mt-3">Zmodyfikowane sekcje: {integrity.data.observed_scope.section_ids.length || "brak"}.</p>
          <p className="mt-2">Zachowane elementy: {integrity.data.protected_content_units.filter((unit) => unit.status === "preserved").length}; zmienione: {integrity.data.protected_content_units.filter((unit) => unit.status === "changed").length}; usunięte: {integrity.data.protected_content_units.filter((unit) => unit.status === "removed").length}.</p>
          {integrity.data.lint_signals.length ? <ul className="mt-3 list-disc space-y-1 pl-5">{integrity.data.lint_signals.map((signal) => <li key={signal.code}>{signal.reason}</li>)}</ul> : <p className="mt-3">Nie wykryto deterministycznych sygnałów redakcyjnych.</p>}
        </details>
      </div> : null}
    </section>
  );
}

function integrityLabel(result: "pass" | "review_required" | "invalid_representation" | "unauthorized_scope_change") {
  switch (result) {
    case "pass": return "Integralność zachowana";
    case "review_required": return "Wymaga sprawdzenia redakcyjnego";
    case "invalid_representation": return "Błędna reprezentacja body i HTML";
    case "unauthorized_scope_change": return "Zmiana poza obserwowanym zakresem";
  }
}
