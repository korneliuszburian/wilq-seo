import type { ReactNode } from "react";

import type { ContentDocumentWorkspace, ContentSelectedWorkspace } from "../../lib/api";
import { ContentDocumentWorkspaceCanvas } from "../ContentDocumentWorkspaceCanvas";
import {
  ContentClassifiedProductionBlockerPanel,
  ContentReusableProductionPanel,
  ContentReusableRequesterPendingPanel
} from "../ContentReusableProductionPanel";
import { ContentWorkflowWorkspaceHeader } from "../ContentWorkflowWorkspaceHeader";
import type { ContentSelectedWorkspaceQuery } from "./Shared";

export function ContentTextWorkspace({
  workItemId,
  selectedWorkspace,
  requestedBy,
  onOpenReview
}: {
  workItemId: string;
  selectedWorkspace: ContentSelectedWorkspaceQuery;
  requestedBy: string | null;
  onOpenReview: (workItemId: string) => void;
}) {
  if (selectedWorkspace.isLoading) {
    return <DocumentWorkspacePending />;
  }
  if (selectedWorkspace.error || !selectedWorkspace.data || selectedWorkspace.data.status === "missing") {
    return <DocumentWorkspaceError onRetry={() => void selectedWorkspace.refetch()} />;
  }
  const workspace = selectedWorkspace.data.workspace;
  if (!workspace) return <DocumentWorkspaceError onRetry={() => void selectedWorkspace.refetch()} />;
  return <ProductionAwareDocumentWorkspace
    selected={selectedWorkspace.data}
    workspace={workspace}
    requestedBy={requestedBy}
    onOpenReview={() => onOpenReview(workItemId)}
  />;
}

function ProductionAwareDocumentWorkspace({
  selected,
  workspace,
  requestedBy,
  onOpenReview
}: {
  selected: ContentSelectedWorkspace;
  workspace: ContentDocumentWorkspace;
  requestedBy: string | null;
  onOpenReview: () => void;
}) {
  const productionDecision = selected.production_decision;
  const canvasRequestedBy = requestedBy ?? "operator_local_dashboard";

  switch (productionDecision.status) {
    case "missing":
      return <CurrentWorkspaceCanvas
        workspace={workspace}
        operatorJourney={selected.operator_journey}
        requestedBy={canvasRequestedBy}
        onOpenReview={onOpenReview}
      />;
    case "available":
      switch (productionDecision.decision) {
        case "reuse":
          switch (productionDecision.reusable_document.status) {
            case "ready":
              return <CurrentWorkspaceCanvas
                workspace={workspace}
                operatorJourney={selected.operator_journey}
                requestedBy={canvasRequestedBy}
                onOpenReview={onOpenReview}
                leadingPanel={requestedBy ? <ContentReusableProductionPanel
                  selected={selected}
                  productionDecision={productionDecision}
                  reusableDocument={productionDecision.reusable_document}
                  requestedBy={requestedBy}
                /> : <ContentReusableRequesterPendingPanel />}
              />;
            case "blocked":
              return <CurrentWorkspaceCanvas
                workspace={workspace}
                operatorJourney={selected.operator_journey}
                requestedBy={canvasRequestedBy}
                onOpenReview={onOpenReview}
                leadingPanel={<ContentClassifiedProductionBlockerPanel
                  reason={productionDecision.reusable_document.reason_pl}
                  safeNextStep={productionDecision.reusable_document.safe_next_step_pl}
                />}
              />;
            default:
              return productionDecision.reusable_document satisfies never;
          }
        case "refresh":
        case "write":
        case "blocked":
          return <CurrentWorkspaceCanvas
            workspace={workspace}
            operatorJourney={selected.operator_journey}
            requestedBy={canvasRequestedBy}
            onOpenReview={onOpenReview}
            leadingPanel={<ContentClassifiedProductionBlockerPanel
              reason={productionDecision.reason_pl}
              safeNextStep={productionDecision.safe_next_step_pl}
            />}
          />;
        default:
          return productionDecision satisfies never;
      }
    default:
      return productionDecision satisfies never;
  }
}

function CurrentWorkspaceCanvas({
  workspace,
  operatorJourney,
  requestedBy,
  onOpenReview,
  leadingPanel
}: {
  workspace: ContentDocumentWorkspace;
  operatorJourney: ContentSelectedWorkspace["operator_journey"];
  requestedBy: string;
  onOpenReview: () => void;
  leadingPanel?: ReactNode;
}) {
  return <ContentDocumentWorkspaceCanvas
    workspace={workspace}
    operatorJourney={operatorJourney}
    requestedBy={requestedBy}
    onOpenReview={onOpenReview}
    leadingPanel={leadingPanel}
  />;
}

export function DocumentWorkspacePending() {
  return <main className="mx-auto max-w-7xl px-4 py-5 lg:px-8" data-testid="content-document-workspace-pending"><ContentWorkflowWorkspaceHeader /><section className="mt-4 rounded-2xl border border-line bg-white p-5 shadow-sm"><p className="mt-2 text-lg font-semibold text-ink">Wczytuję aktualną stronę…</p><p className="mt-2 text-sm text-slate-700">Pobieram materiał źródłowy i stan dokumentu. To nie jest błąd.</p></section></main>;
}

export function DocumentWorkspaceError({ onRetry }: { onRetry: () => void }) {
  return <main className="mx-auto max-w-7xl px-4 py-5 lg:px-8" data-testid="content-document-workspace-error"><ContentWorkflowWorkspaceHeader /><section className="mt-4 rounded-2xl border border-wait/30 bg-white p-5 shadow-sm"><p className="mt-2 text-lg font-semibold text-ink">Nie udało się odczytać workspace’u strony.</p><button type="button" className="mt-3 rounded-md bg-action px-3 py-2 text-sm font-semibold text-white" onClick={onRetry}>Spróbuj ponownie</button></section></main>;
}
