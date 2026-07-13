import { FileText, Globe2 } from "lucide-react";

import { ContentMapColumn, ContentSectionRow } from "./ContentMapPrimitives";

type ContentPublicPageColumnProps = {
  publicUrl: string;
  publicSections: string[];
  environmentLabel: string;
};

export function ContentPublicPageColumn({
  publicUrl,
  publicSections,
  environmentLabel
}: ContentPublicPageColumnProps) {
  return (
    <ContentMapColumn
      icon={<Globe2 aria-hidden="true" size={18} />}
      title="Aktualna strona"
      subtitle={publicUrl ? environmentLabel : "publiczna treść"}
    >
      {publicSections.length ? (
        <ol className="space-y-2">
          {publicSections.slice(0, 4).map((section, index) => (
            <ContentSectionRow
              key={`${section}-${index}`}
              icon={<FileText aria-hidden="true" size={15} />}
              title={section}
              subtitle={`Sekcja ${index + 1}`}
            />
          ))}
          {publicSections.length > 4 ? (
            <li className="rounded-md border border-line bg-surface px-3 py-2 text-xs font-semibold text-slate-600">
              + {publicSections.length - 4} sekcji niżej w kontekście
            </li>
          ) : null}
        </ol>
      ) : (
        <p className="rounded-md border border-wait/25 bg-wait/10 p-3 text-sm leading-6 text-slate-700">
          Brakuje listy publicznych sekcji dla tej strony.
        </p>
      )}
    </ContentMapColumn>
  );
}
