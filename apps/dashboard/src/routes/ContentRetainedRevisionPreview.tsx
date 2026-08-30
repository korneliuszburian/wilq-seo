import type { ContentDraftRevision } from "../lib/api";
import { ContentFullPagePreview } from "./ContentFullPagePreview";
import type { ApprovedReuseReview } from "./contentReuseValidation";

export function ContentRetainedRevisionPreview({
  revision,
  review
}: {
  revision: ContentDraftRevision;
  review: ApprovedReuseReview;
}) {
  return (
    <div className="mt-5" data-testid="content-retained-approved-document">
      {revision.page_assets ? (
        <ContentFullPagePreview revision={revision} />
      ) : (
        <LegacyRetainedRevisionPreview revision={revision} />
      )}
      <details className="mt-4 rounded-xl border border-line bg-surface p-4 text-xs text-ink/75">
        <summary className="cursor-pointer font-semibold text-ink">
          Dokładne identyfikatory rewizji i review
        </summary>
        <div className="mt-3 space-y-2 leading-5">
          <p className="break-all">Właściciel rewizji: {revision.work_item_id}</p>
          <p className="break-all">Rewizja: {revision.revision_id}</p>
          <p className="break-all">Digest rewizji: {revision.content_digest}</p>
          <p className="break-all">Review: {review.decision_id}</p>
          <p>Zatwierdził(a): {review.reviewed_by}</p>
          <p>Decyzja: {review.decision}</p>
        </div>
      </details>
    </div>
  );
}

function LegacyRetainedRevisionPreview({ revision }: { revision: ContentDraftRevision }) {
  return (
    <article
      className="overflow-hidden rounded-xl border border-line bg-white shadow-sm"
      data-testid="content-retained-v1-preview"
    >
      <div className="border-b border-line bg-surface px-4 py-3">
        <p className="text-xs font-semibold uppercase tracking-widest text-action">
          Zachowany dokument v1
        </p>
        <h3 className="mt-2 text-2xl font-semibold text-ink">{revision.title}</h3>
      </div>
      <div className="space-y-7 px-5 py-6 sm:px-8">
        <div>
          <h4 className="text-lg font-semibold text-ink">Sekcje</h4>
          <div className="mt-4 space-y-5">
            {revision.sections.map((section, index) => (
              <div
                key={section.section_id ?? `${section.heading}-${index}`}
                className="border-t border-line pt-4"
              >
                <h5 className="text-base font-semibold text-ink">{section.heading}</h5>
                <p className="mt-2 whitespace-pre-wrap text-sm leading-7 text-ink/75">
                  {section.body_markdown}
                </p>
              </div>
            ))}
          </div>
        </div>
        <RetainedFaq revision={revision} />
        <RetainedCtas revision={revision} />
        <RetainedInternalLinks revision={revision} />
      </div>
    </article>
  );
}

function RetainedFaq({ revision }: { revision: ContentDraftRevision }) {
  return (
    <div className="border-t border-line pt-5">
      <h4 className="text-lg font-semibold text-ink">FAQ</h4>
      {revision.faq.length === 0 ? (
        <p className="mt-2 text-sm text-ink/70">Ta rewizja nie zawiera zapisanych pytań FAQ.</p>
      ) : (
        <div className="mt-4 space-y-4">
          {revision.faq.map((item) => (
            <div key={item.faq_id}>
              <h5 className="text-sm font-semibold text-ink">{item.question}</h5>
              <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-ink/75">
                {item.answer_markdown}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function RetainedCtas({ revision }: { revision: ContentDraftRevision }) {
  return (
    <div className="border-t border-line pt-5">
      <h4 className="text-lg font-semibold text-ink">Wezwania do działania</h4>
      {revision.cta_blocks.length === 0 ? (
        <p className="mt-2 text-sm text-ink/70">Ta rewizja nie zawiera zapisanych CTA.</p>
      ) : (
        <div className="mt-4 space-y-3">
          {revision.cta_blocks.map((cta) => (
            <div key={cta.cta_id} className="rounded-xl border border-action/25 bg-action/5 p-4">
              <p className="text-sm leading-6 text-ink">{cta.body_markdown}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function RetainedInternalLinks({ revision }: { revision: ContentDraftRevision }) {
  return (
    <div className="border-t border-line pt-5">
      <h4 className="text-lg font-semibold text-ink">Linki wewnętrzne</h4>
      {revision.internal_links.length === 0 ? (
        <p className="mt-2 text-sm text-ink/70">Ta rewizja nie zawiera zapisanych linków wewnętrznych.</p>
      ) : (
        <ul className="mt-4 space-y-3">
          {revision.internal_links.map((link) => (
            <li key={link.link_id} className="rounded-xl border border-line bg-surface p-3">
              <p className="text-sm font-semibold text-action">{link.anchor_text}</p>
              <p className="mt-1 break-all text-xs text-ink/70">{link.target_url}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function ReuseFailClosedState({
  reason,
  safeNextStep
}: {
  reason: string;
  safeNextStep: string;
}) {
  return (
    <div
      className="mt-5 rounded-xl border border-risk/30 bg-risk/10 p-4"
      data-testid="content-reuse-fail-closed"
      role="alert"
    >
      <p className="font-semibold text-risk">Nie pokazuję zachowanej wersji</p>
      {reason ? <p className="mt-2 text-sm leading-6 text-ink">{reason}</p> : null}
      <p className="mt-3 text-sm font-semibold text-ink">Bezpieczny następny krok</p>
      <p className="mt-1 text-sm leading-6 text-ink">{safeNextStep}</p>
    </div>
  );
}
