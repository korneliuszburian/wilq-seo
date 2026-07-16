import type { ContentDraftRevision, ContentPlanningProposal } from "../lib/api";

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
        <p className="font-semibold text-ink">Podgląd całej strony</p>
        <p className="mt-1">Meta: {assets.meta_title}</p>
        <p className="mt-1">{assets.meta_description}</p>
      </div>
      <div className="px-5 py-7 sm:px-8 sm:py-9">
        <h1 className="text-3xl font-semibold leading-tight text-ink">{assets.h1}</h1>
        <p className="mt-4 text-base leading-7 text-slate-700">{assets.lead}</p>
        {revision.cta_blocks
          .filter((cta) => cta.placement === "after_lead")
          .map((cta) => <CtaPreview key={cta.cta_id} body={cta.body_markdown} />)}
        <LinkPreview
          links={revision.internal_links.filter((link) => link.placement === "after_lead")}
        />
        <div className="mt-8 space-y-8">
          {revision.sections.map((section) => (
            <section key={section.section_id ?? section.heading}>
              <h2 className="text-xl font-semibold leading-7 text-ink">{section.heading}</h2>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-700">
                {section.body_markdown}
              </p>
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
          <section className="mt-10 border-t border-line pt-7">
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
