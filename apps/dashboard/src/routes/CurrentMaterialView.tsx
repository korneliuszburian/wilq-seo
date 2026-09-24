import type { CurrentMaterialTextResponse } from "@wilq/shared-schemas";

import { materialReviewPageUrl } from "./ActionPanels/materialReviewDecision";

export function CurrentMaterialView({
  material,
  loading,
  unavailable
}: {
  material: CurrentMaterialTextResponse | undefined;
  loading: boolean;
  unavailable: boolean;
}) {
  const exact = material && "text" in material && material.status === "exact" ? material : null;
  const sourceUrl = exact ? materialReviewPageUrl({ public_url: exact.source_url }) : null;

  return (
    <main className="mx-auto max-w-5xl px-4 py-7 lg:px-8">
      <h1 className="text-2xl font-semibold leading-tight text-ink">
        Aktualna treść strony{exact?.title ? `: ${exact.title}` : ""}
      </h1>
      <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">
        Bieżący tekst odczytany z WordPressa. WILQ automatycznie sprawdza zgodność odczytu
        z dokładnym adresem i zapisanym obrazem strony. To materiał źródłowy do nowej wersji artykułu.
      </p>

      {exact ? (
        <>
          <article className="mt-6 rounded-xl border border-line bg-white px-5 py-6 shadow-sm md:px-9 md:py-8">
            <div className="max-w-[74ch] whitespace-pre-wrap break-words text-[15px] leading-8 text-slate-800">
              {exact.text}
            </div>
          </article>
          <section className="mt-5 rounded-xl border border-line bg-white p-5 text-sm leading-6 text-slate-700">
            <h2 className="font-semibold text-ink">Źródło</h2>
            {sourceUrl ? (
              <a className="mt-2 block break-all text-teal-800 underline" href={sourceUrl}
                target="_blank" rel="noopener noreferrer">{sourceUrl}</a>
            ) : null}
            <p className="mt-2">Odczyt: {new Date(exact.read_at).toLocaleString("pl-PL")}</p>
            <p>Pełny tekst pasuje do dokładnego odczytu tej strony.</p>
          </section>
        </>
      ) : (
        <section className="mt-6 rounded-xl border border-line bg-white p-5 text-sm leading-6 text-slate-700">
          {material?.status === "blocked" ? (
            <>
              <h2 className="font-semibold text-risk">Odczyt strony wymaga odświeżenia</h2>
              <p className="mt-2">{material.safe_next_step}</p>
              <p className="mt-2 text-xs text-slate-500">
                {material.blocker_code} · {material.blocker_owner}
              </p>
            </>
          ) : loading ? (
            <p>Odczytuję bieżący tekst strony…</p>
          ) : (
            <>
              <h2 className="font-semibold text-risk">Nie mogę potwierdzić odczytu strony</h2>
              <p className="mt-2">
                {unavailable
                  ? "WILQ content workflow: przygotuj nowy dokładny odczyt tego adresu."
                  : "WILQ WordPress connector: ponów odczyt tej strony."}
              </p>
            </>
          )}
        </section>
      )}
    </main>
  );
}
