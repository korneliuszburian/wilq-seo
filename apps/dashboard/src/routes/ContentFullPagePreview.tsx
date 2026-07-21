import type { ContentDraftRevision, ContentPlanningProposal } from "../lib/api";
import { ContentHtmlPreview } from "./ContentHtmlPreview";

export function ContentFullPagePreview({
  revision,
  proposal
}: {
  revision: ContentDraftRevision;
  proposal: ContentPlanningProposal | null;
}) {
  const assets = revision.page_assets;
  if (!assets) return null;
  const queryCount = proposal
    ? proposal.search_demand.gsc_query_rows.length +
      proposal.search_demand.ads_term_rows.length +
      proposal.search_demand.keyword_planner_rows.length
    : 0;

  return (
    <article
      className="overflow-hidden rounded-md border border-line bg-white shadow-sm"
      data-testid="content-full-page-preview"
    >
      <div className="border-b border-line bg-surface px-4 py-3 text-xs text-slate-600">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="font-semibold text-ink">Tekst strony · wersja robocza</p>
            <p className="mt-1">Niepublikowany podgląd exact revision. WordPress pozostaje bez zmian.</p>
          </div>
          <span className="rounded-full border border-action/20 bg-action/5 px-2.5 py-1 text-[11px] font-semibold text-action">
            {revision.sections.length} sekcji · {revision.faq.length} FAQ
          </span>
        </div>
        <p className="mt-3">Meta: {assets.meta_title}</p>
        <p className="mt-1">{assets.meta_description}</p>
      </div>
      <div className="grid lg:grid-cols-[minmax(0,1fr)_220px]">
      <div className="min-w-0 px-5 py-7 sm:px-8 sm:py-9">
        <h1 className="text-3xl font-semibold leading-tight text-ink">{assets.h1}</h1>
        <p className="mt-4 text-base leading-7 text-slate-700">{assets.lead}</p>
        {revision.cta_blocks
          .filter((cta) => cta.placement === "after_lead")
          .map((cta) => <CtaPreview key={cta.cta_id} body={cta.body_markdown} />)}
        <LinkPreview
          links={revision.internal_links.filter((link) => link.placement === "after_lead")}
        />
        <div className="mt-8 space-y-8">
          {revision.sections.map((section, index) => (
            <section key={section.section_id ?? section.heading} id={previewSectionId(section.section_id, index)}>
              <h2 className="text-xl font-semibold leading-7 text-ink">{section.heading}</h2>
              {section.content_html ? (
                <ContentHtmlPreview
                  contentHtml={section.content_html}
                  title={`Podgląd HTML sekcji ${section.heading}`}
                  className="mt-3"
                  minHeightClass="min-h-56"
                />
              ) : (
                <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-700">
                  {section.body_markdown}
                </p>
              )}
              {revision.cta_blocks
                .filter((cta) => cta.placement === section.section_id)
                .map((cta) => (
                  <CtaPreview key={cta.cta_id} body={cta.body_markdown} />
                ))}
              <LinkPreview
                links={revision.internal_links.filter(
                  (link) => link.placement === section.section_id
                )}
              />
            </section>
          ))}
        </div>
        {revision.faq.length ? (
          <section id="preview-faq" className="mt-10 border-t border-line pt-7">
            <h2 className="text-xl font-semibold text-ink">Najczęstsze pytania</h2>
            <div className="mt-4 space-y-4">
              {revision.faq.map((item) => (
                <div key={item.faq_id}>
                  <h3 className="text-sm font-semibold text-ink">{item.question}</h3>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">
                    {item.answer_markdown}
                  </p>
                </div>
              ))}
            </div>
          </section>
        ) : null}
        {revision.cta_blocks
          .filter((cta) => cta.placement === "after_content")
          .map((cta) => <CtaPreview key={cta.cta_id} body={cta.body_markdown} />)}
        <LinkPreview
          links={revision.internal_links.filter((link) => link.placement === "after_content")}
        />
      </div>
      <aside className="border-t border-line bg-surface px-4 py-5 lg:border-l lg:border-t-0" aria-label="Nawigacja po podglądzie strony">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Na tej stronie</p>
        <nav className="mt-3" aria-label="Sekcje podglądu">
          <ol className="space-y-2">
            {revision.sections.map((section, index) => (
              <li key={section.section_id ?? section.heading}>
                <a className="text-sm leading-5 text-action hover:underline" href={`#${previewSectionId(section.section_id, index)}`}>
                  {index + 1}. {section.heading}
                </a>
              </li>
            ))}
            {revision.faq.length ? (
              <li><a className="text-sm leading-5 text-action hover:underline" href="#preview-faq">FAQ</a></li>
            ) : null}
          </ol>
        </nav>
        <p className="mt-5 border-t border-line pt-4 text-xs leading-5 text-slate-600">
          Wybierz sekcję z nawigacji albo wróć do edytora, aby poprawić tylko wybrany fragment.
        </p>
      </aside>
      </div>
      <details className="border-t border-line bg-surface px-4 py-3">
        <summary className="cursor-pointer text-sm font-semibold text-action">
          Dlaczego ten tekst i jak go mierzymy
        </summary>
        <div className="mt-3 grid gap-3 text-xs leading-5 text-slate-600 sm:grid-cols-2">
          <p>
            {queryCount} dokładnie dopasowanych sygnałów zapytań · {revision.sections.length}
            {" "}sekcji · {revision.faq.length} pytań FAQ.
          </p>
          <p>
            Metryki po publikacji: {proposal?.measurement_plan.metrics_to_watch.join(", ") ||
              "brak wymyślonych targetów; obowiązuje istniejący measurement loop"}.
          </p>
          <p className="break-all sm:col-span-2">
            Rewizja {revision.revision_id} · digest {revision.content_digest} · plan {revision.planning_digest}
          </p>
        </div>
      </details>
    </article>
  );
}

function previewSectionId(sectionId: string | null | undefined, index: number) {
  return sectionId ? `preview-${sectionId}` : `preview-section-${index + 1}`;
}

function CtaPreview({ body }: { body: string }) {
  return (
    <aside className="mt-6 rounded-md border border-action/25 bg-action/5 p-4 text-sm leading-6 text-ink">
      {body}
    </aside>
  );
}

function LinkPreview({
  links
}: {
  links: ContentDraftRevision["internal_links"];
}) {
  if (!links.length) return null;
  return (
    <nav className="mt-6 border-t border-line pt-4" aria-label="Linki wewnętrzne szkicu">
      <p className="text-sm font-semibold text-ink">Czytaj dalej</p>
      <ul className="mt-2 space-y-2">
        {links.map((link) => (
          <li key={link.link_id}>
            <a className="text-sm font-semibold text-action" href={link.target_url}>
              {link.anchor_text}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
