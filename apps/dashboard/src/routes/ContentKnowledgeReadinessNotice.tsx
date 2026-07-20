import type {
  KnowledgeSourceMaterialReadinessQuery,
  KnowledgeSourceMaterialsQuery
} from "./contentWorkflowQueries";

export function ContentKnowledgeReadinessNotice({
  query,
  materials
}: {
  query: KnowledgeSourceMaterialReadinessQuery;
  materials: KnowledgeSourceMaterialsQuery;
}) {
  const readiness = query.data;
  if (query.isError) {
    return (
      <div
        className="mt-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-950"
        data-testid="content-workflow-knowledge-readiness-error"
      >
        Nie udało się odczytać gotowości korpusu źródłowego. Nie zakładaj, że
        generowanie jest odblokowane — odśwież dane przed przygotowaniem planu.
      </div>
    );
  }
  if (query.isLoading) {
    return (
      <div
        className="mt-5 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700"
        data-testid="content-workflow-knowledge-readiness-loading"
      >
        Sprawdzam gotowość korpusu źródłowego przed przygotowaniem planu…
      </div>
    );
  }
  if (!readiness) return null;
  if (readiness.ready_for_generation) {
    if (!materials.data?.length) return null;
    return (
      <details
        className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50/60 px-4 py-3 text-sm text-emerald-950"
        data-testid="content-workflow-knowledge-sources"
      >
        <summary className="cursor-pointer font-semibold">
          Materiały źródłowe używane przez WILQ ({materials.data.length})
        </summary>
        <p className="mt-2 leading-6">
          To zaakceptowany manifest materiałów Ekologusa. WILQ używa ich jako
          źródeł, ale nie pokazuje prywatnych ścieżek ani surowych transcriptów
          w panelu.
        </p>
        <ul className="mt-3 grid gap-2 sm:grid-cols-2">
          {materials.data.map((material) => (
            <li
              key={material.source_id}
              className="rounded-lg border border-emerald-200/80 bg-white/70 px-3 py-2 text-xs"
            >
              <span className="font-semibold">{material.title || material.file_name}</span>
              <span className="mt-1 block text-emerald-900/75">
                {material.kind} · {material.word_count.toLocaleString("pl-PL")} słów ·
                {" "}{material.import_status === "imported" ? "zaimportowany" : "review"}
              </span>
            </li>
          ))}
        </ul>
      </details>
    );
  }
  const pendingParts = [
    readiness.import_pending_count > 0
      ? `${readiness.import_pending_count} oczekuje na kontrolowany import`
      : null,
    readiness.excerpt_review_required_count > 0
      ? `${readiness.excerpt_review_required_count} wymaga review excerptów`
      : null
  ].filter((part): part is string => Boolean(part));
  return (
    <div
      className="mt-5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
      data-testid="content-workflow-knowledge-readiness"
    >
      <p className="font-semibold">Korpus źródłowy nie jest jeszcze kompletny</p>
      <p className="mt-1 leading-6">
        Zaimportowano {readiness.imported_count} z {readiness.total_count} materiałów.
        {pendingParts.length ? ` ${pendingParts.join("; ")}.` : null}{" "}
        {readiness.next_step ||
          "Skontaktuj się z administratorem, aby ustalić kolejny krok dla korpusu źródłowego."}
      </p>
      {materials.data?.length ? (
        <details className="mt-3 rounded-lg border border-amber-200/80 bg-white/50 px-3 py-2">
          <summary className="cursor-pointer font-semibold">Materiały oczekujące na obsługę</summary>
          <ul className="mt-2 space-y-1 text-xs leading-5 text-amber-900">
            {materials.data.map((material) => (
              <li key={material.source_id}>
                <span className="font-medium">{material.title || material.file_name}</span>
                <span className="ml-1 opacity-75">· {material.import_status}</span>
              </li>
            ))}
          </ul>
        </details>
      ) : materials.isError ? (
        <p className="mt-2 text-xs text-amber-900">Lista materiałów jest chwilowo niedostępna.</p>
      ) : null}
    </div>
  );
}
