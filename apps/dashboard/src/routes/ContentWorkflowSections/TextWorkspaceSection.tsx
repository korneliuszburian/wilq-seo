import { ContentDocumentWorkspaceCanvas } from "../ContentDocumentWorkspaceCanvas";
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
  requestedBy: string;
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
  return <ContentDocumentWorkspaceCanvas
    workspace={workspace}
    operatorJourney={selectedWorkspace.data.operator_journey}
    requestedBy={requestedBy}
    onOpenReview={() => onOpenReview(workItemId)}
  />;
}

export function DocumentWorkspacePending() {
  return <main className="mx-auto max-w-7xl px-4 py-5 lg:px-8" data-testid="content-document-workspace-pending"><ContentWorkflowWorkspaceHeader /><section className="mt-4 rounded-2xl border border-line bg-white p-5 shadow-sm"><p className="mt-2 text-lg font-semibold text-ink">Wczytuję aktualną stronę…</p><p className="mt-2 text-sm text-slate-700">Pobieram materiał źródłowy i stan dokumentu. To nie jest błąd.</p></section></main>;
}

export function DocumentWorkspaceError({ onRetry }: { onRetry: () => void }) {
  return <main className="mx-auto max-w-7xl px-4 py-5 lg:px-8" data-testid="content-document-workspace-error"><ContentWorkflowWorkspaceHeader /><section className="mt-4 rounded-2xl border border-wait/30 bg-white p-5 shadow-sm"><p className="mt-2 text-lg font-semibold text-ink">Nie udało się odczytać workspace’u strony.</p><button type="button" className="mt-3 rounded-md bg-action px-3 py-2 text-sm font-semibold text-white" onClick={onRetry}>Spróbuj ponownie</button></section></main>;
}
