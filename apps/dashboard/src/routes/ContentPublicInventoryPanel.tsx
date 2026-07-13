import { FileText } from "lucide-react";

type ContentPublicInventoryPanelProps = {
  sourceTitle: string;
  sourceHref?: string;
  sectionInventoryAvailable: boolean;
  publicSections: string[];
};

export function ContentPublicInventoryPanel({
  sourceTitle,
  sourceHref,
  sectionInventoryAvailable,
  publicSections
}: ContentPublicInventoryPanelProps) {
  return (
    <div className="rounded-md border border-line bg-white p-4">
      <div className="flex items-start gap-3">
        <div className="rounded-md border border-line bg-surface p-2 text-action">
          <FileText aria-hidden="true" size={18} />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-ink">Aktualna publiczna treść</h3>
          <p className="mt-2 text-sm font-semibold text-ink">{sourceTitle}</p>
          <a href={sourceHref} target="_blank" rel="noreferrer" className="mt-1 inline-flex text-sm font-semibold text-action">
            Otwórz obecną stronę
          </a>
        </div>
      </div>
      {sectionInventoryAvailable ? (
        <ol className="mt-4 space-y-2 text-sm leading-6 text-slate-700">
          {publicSections.slice(0, 6).map((section, index) => (
            <li key={`${section}-${index}`} className="rounded-md border border-line bg-surface px-3 py-2">
              {index + 1}. {section}
            </li>
          ))}
        </ol>
      ) : (
        <p className="mt-4 rounded-md border border-wait/25 bg-wait/10 px-3 py-2 text-sm leading-6 text-slate-700">
          Brakuje czytelnej listy sekcji z publicznego WordPressa. Nie przepisuj strony w ciemno:
          najpierw odczytaj sekcje albo pracuj tylko na sprawdzonym szkicu z dev.
        </p>
      )}
    </div>
  );
}
