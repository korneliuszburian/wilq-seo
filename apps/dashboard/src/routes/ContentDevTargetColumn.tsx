import { Code2 } from "lucide-react";

import type { WordPressAuthoringProfile } from "../lib/api";
import { ContentMapColumn, ContentSectionRow } from "./ContentMapPrimitives";
import type { WordPressAuthoringDevPage } from "./contentWorkflowTarget";

type ContentDevTargetColumnProps = {
  profile: WordPressAuthoringProfile | null;
  devPage: WordPressAuthoringDevPage | null;
  devSections: WordPressAuthoringDevPage["sections"];
  onSelectDevPage: (link: string | null) => void;
};

export function ContentDevTargetColumn({
  profile,
  devPage,
  devSections,
  onSelectDevPage
}: ContentDevTargetColumnProps) {
  return (
    <ContentMapColumn
      icon={<Code2 aria-hidden="true" size={18} />}
      title="Dev draft / ACF"
      subtitle={devPage ? `${devPage.section_count} sekcji na devie` : "czeka na odczyt"}
    >
      {profile?.dev_content.pages.length ? (
        <label className="mb-3 block">
          <span className="mb-1 block text-xs font-semibold uppercase tracking-normal text-slate-500">
            Cel dev do podglądu
          </span>
          <select
            className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm text-ink"
            value={devPage?.link ?? ""}
            onChange={(event) => onSelectDevPage(event.target.value || null)}
            aria-label="Cel dev do podglądu"
          >
            {profile.dev_content.pages.map((page) => (
              <option key={page.link} value={page.link}>
                {page.title || page.link} · {page.section_count} sekcji
              </option>
            ))}
          </select>
          <span className="mt-1 block text-xs leading-5 text-slate-500">
            Zmienia tylko kontekst podglądu. Zapis do WordPress nadal wymaga osobnej, bezpiecznej ścieżki.
          </span>
        </label>
      ) : null}
      {devSections.length ? (
        <ol className="space-y-2">
          {devSections.slice(0, 5).map((section) => (
            <ContentSectionRow
              key={`${section.section_index}-${section.layout_name}`}
              icon={<Code2 aria-hidden="true" size={15} />}
              title={section.title || section.layout_label}
              subtitle={section.layout_name}
              meta={section.acf_field_name}
              badge="dev"
              tone="dev"
            />
          ))}
          {devSections.length > 5 ? (
            <li className="rounded-md border border-line bg-surface px-3 py-2 text-xs font-semibold text-slate-600">
              + {devSections.length - 5} sekcji ACF w kontekście
            </li>
          ) : null}
        </ol>
      ) : (
        <p className="rounded-md border border-wait/25 bg-wait/10 p-3 text-sm leading-6 text-slate-700">
          {profile?.dev_content.status === "blocked"
            ? profile.dev_content.blockers[0]?.reason
            : "Nie mamy jeszcze czytelnych sekcji ACF z dev REST dla tej strony."}
        </p>
      )}
    </ContentMapColumn>
  );
}
