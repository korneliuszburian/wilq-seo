import type { ContentWorkflowSnapshot } from "./contentWorkflowRuntime";
import type { WordPressAuthoringDevContentObject } from "./contentWorkflowTarget";

type DraftPackage = ContentWorkflowSnapshot["draftPackage"]["draft_package_result"]["draft_package"];
type DraftPackageSection = NonNullable<DraftPackage>["sections"][number];

export function AcfCurrentVsProposedPanel({
  devSections,
  draftSections
}: {
  devSections: WordPressAuthoringDevContentObject["sections"];
  draftSections: DraftPackageSection[];
}) {
  if (!devSections.length && !draftSections.length) return null;
  const totalRows = Math.max(devSections.length, draftSections.length);
  const rows = Array.from({ length: totalRows }, (_, index) => ({
    current: devSections[index],
    proposed: draftSections[index]
  })).slice(0, 5);
  return (
    <details className="rounded-md border border-line bg-white p-4 shadow-sm">
      <summary className="cursor-pointer text-sm font-semibold text-action">
        Porównaj sekcje dev z propozycją szkicu
      </summary>
      <p className="mt-2 text-sm leading-6 text-slate-600">
        Odczyt bieżącego devu i propozycja szkicu obok siebie. To porównanie nie wykonuje zapisu ani aktualizacji ACF.
      </p>
      <div className="mt-3 space-y-2">
        {rows.map(({ current, proposed }, index) => (
          <div key={`${current?.section_index ?? "none"}-${proposed?.heading ?? index}`} className="grid gap-2 rounded-md border border-line bg-surface p-3 md:grid-cols-2">
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-normal text-slate-500">Dev teraz · sekcja {index + 1}</div>
              <div className="mt-1 text-sm font-semibold text-ink">{current?.title || current?.layout_label || "Brak odczytu"}</div>
              <div className="mt-1 text-xs text-slate-500">{current?.layout_name || "Nie ma odpowiadającego layoutu"}</div>
            </div>
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-normal text-slate-500">Propozycja szkicu</div>
              <div className="mt-1 text-sm font-semibold text-ink">{proposed?.heading || "Brak propozycji"}</div>
              <div className="mt-1 line-clamp-2 text-xs leading-5 text-slate-600">{proposed?.purpose || "Ta sekcja nie ma jeszcze propozycji."}</div>
            </div>
          </div>
        ))}
      </div>
      {rows.length < totalRows ? (
        <div className="mt-2 text-xs text-slate-500">Pokazano pierwsze 5 sekcji; pełny tekst pozostaje w edytorze szkicu.</div>
      ) : null}
    </details>
  );
}
