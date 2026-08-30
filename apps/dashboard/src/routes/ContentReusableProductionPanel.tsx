import type { ContentInitialDraftResponse, ContentSelectedWorkspace } from "../lib/api";
import { ContentRetainedRevisionPreview, ReuseFailClosedState } from "./ContentRetainedRevisionPreview";
import { useContentReusableInitialDraft } from "./contentWorkflowQueries";
import {
  hasExactReusedInitialDraft,
  type ReusableDocumentReady,
  type ReuseProductionDecision
} from "./contentReuseValidation";

export function ContentReusableProductionPanel({
  selected,
  productionDecision,
  reusableDocument,
  requestedBy
}: {
  selected: ContentSelectedWorkspace;
  productionDecision: ReuseProductionDecision;
  reusableDocument: ReusableDocumentReady;
  requestedBy: string;
}) {
  const revalidation = useContentReusableInitialDraft(
    selected.requested_work_item_id,
    productionDecision.run_digest,
    requestedBy
  );

  return (
    <article
      className="rounded-2xl border border-action/25 bg-white p-5 shadow-sm lg:p-6"
      data-testid="content-reusable-production-panel"
    >
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line pb-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-action">
            Decyzja produkcyjna: użyj ponownie
          </p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink">
            Zachowana zatwierdzona wersja
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-ink/75">
            WILQ ponownie sprawdza dokładną zachowaną rewizję przed jej pokazaniem. Nie
            uruchamia planowania ani generowania.
          </p>
        </div>
        <span className="rounded-full border border-signal/25 bg-signal/10 px-2.5 py-1 text-xs font-semibold text-signal">
          tylko odczyt
        </span>
      </div>
      <ReusableInitialDraftResult
        revalidation={revalidation}
        selected={selected}
        productionDecision={productionDecision}
        reusableDocument={reusableDocument}
      />
    </article>
  );
}

export function ContentClassifiedProductionBlockerPanel({
  reason,
  safeNextStep
}: {
  reason: string;
  safeNextStep: string;
}) {
  return (
    <article
      className="rounded-2xl border border-wait/30 bg-white p-5 shadow-sm lg:p-6"
      data-testid="content-classified-production-blocker"
    >
      <p className="text-xs font-semibold uppercase tracking-widest text-wait">
        Klasyfikacja produkcyjna zatrzymała przygotowanie tekstu
      </p>
      <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink">
        Nie uruchamiam planowania ani generowania
      </h2>
      <p className="mt-3 max-w-3xl text-sm leading-6 text-ink/75">{reason}</p>
      <div className="mt-4 rounded-xl border border-wait/25 bg-wait/5 p-4">
        <p className="text-sm font-semibold text-ink">Bezpieczny następny krok</p>
        <p className="mt-1 text-sm leading-6 text-ink/75">{safeNextStep}</p>
      </div>
    </article>
  );
}

export function ContentReusableRequesterPendingPanel() {
  return (
    <article
      className="rounded-2xl border border-line bg-white p-5 shadow-sm lg:p-6"
      data-testid="content-reuse-requester-pending"
      role="status"
    >
      <p className="text-xs font-semibold uppercase tracking-widest text-action">
        Zachowana zatwierdzona wersja
      </p>
      <p className="mt-2 text-sm leading-6 text-ink/75">
        Wczytuję tożsamość operatora przed jednorazowym potwierdzeniem zachowanej rewizji.
      </p>
    </article>
  );
}

function ReusableInitialDraftResult({
  revalidation,
  selected,
  productionDecision,
  reusableDocument
}: {
  revalidation: ReturnType<typeof useContentReusableInitialDraft>;
  selected: ContentSelectedWorkspace;
  productionDecision: ReuseProductionDecision;
  reusableDocument: ReusableDocumentReady;
}) {
  if (revalidation.isPending) {
    return (
      <p className="mt-5 text-sm leading-6 text-ink/75" role="status">
        Potwierdzam zachowaną rewizję i jej zatwierdzenie…
      </p>
    );
  }
  if (revalidation.isError || !revalidation.data) {
    return <ReuseFailClosedState
      reason="Nie udało się bezpiecznie potwierdzić zachowanej wersji."
      safeNextStep="Odśwież wybrany workspace i sprawdź klasyfikację przed ponowną próbą."
    />;
  }

  return renderReusableInitialDraft(
    revalidation.data,
    selected,
    productionDecision,
    reusableDocument
  );
}

function renderReusableInitialDraft(
  response: ContentInitialDraftResponse,
  selected: ContentSelectedWorkspace,
  productionDecision: ReuseProductionDecision,
  reusableDocument: ReusableDocumentReady
) {
  switch (response.status) {
    case "reused":
      if (!hasExactReusedInitialDraft(response, selected, productionDecision, reusableDocument)) {
        return <ReuseFailClosedState
          reason="WILQ zatrzymał wyświetlanie, bo odpowiedź nie pasuje do wybranej klasyfikacji i zachowanej rewizji."
          safeNextStep="Odśwież wybrany workspace i sprawdź przypisanie zachowanej rewizji."
        />;
      }
      return <ContentRetainedRevisionPreview
        revision={response.revision}
        review={response.reuse_binding.approved_review}
      />;
    case "blocked":
    case "failed":
    case "conflict":
      return <ReuseFailClosedState
        reason={response.blockers.map((blocker) => blocker.reason).join(" ")}
        safeNextStep={response.safe_next_step}
      />;
    case "created":
    case "generating":
      return <ReuseFailClosedState
        reason="Resolver zwrócił stan przygotowania nowej treści zamiast zachowanej zatwierdzonej wersji."
        safeNextStep="Przerwij ten przebieg i sprawdź klasyfikację oraz powiązanie rewizji."
      />;
    default:
      return response satisfies never;
  }
}
