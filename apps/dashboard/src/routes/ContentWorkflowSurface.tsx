import { useNavigate, useParams, useRouterState } from "@tanstack/react-router";

import { ContentReviewRoute } from "./ContentWorkflowSections/ReviewWorkspaceSection";
import type {
  ContentInventoryCatalogQuery,
  ContentSelectedWorkspaceQuery,
  ContentWorkflowEntryQuery
} from "./ContentWorkflowSections/Shared";
import { ContentTextWorkspace } from "./ContentWorkflowSections/TextWorkspaceSection";
import { ContentWorkflowEntryPanel } from "./ContentWorkflowEntryPanel";
import { useContentWorkflowQueries } from "./contentWorkflowQueries";

export function ContentWorkflowSurface() {
  const navigate = useNavigate();
  const routeSearch = useRouterState({ select: (state) => state.location.searchStr });
  const routeParams = useParams({ strict: false }) as { workItemId?: string };
  const selectedWorkItemId = routeParams.workItemId ?? stringFromSearch(routeSearch, "work_item_id");
  const contentView = useRouterState({
    select: (state) => Reflect.get(state.location.search, "view")
  });
  const reviewOpen = useRouterState({
    select: (state) => Reflect.get(state.location.search, "view") === "review" || Reflect.get(state.location.search, "review") === 1
  });
  const browseInventory = useRouterState({
    select: (state) => Reflect.get(state.location.search, "view") === "browse" || Reflect.get(state.location.search, "browse") === 1
  });
  const newPageId = useRouterState({
    select: (state) => {
      const value = Reflect.get(state.location.search, "new_page");
      return typeof value === "string" && value ? value : null;
    }
  });
  const newPageOpen = contentView === "new" || Boolean(newPageId);
  const selectWorkItem = (workItemId: string) => {
    void navigate({
      to: "/content-workflow/$workItemId",
      params: { workItemId },
      search: (previous) => ({
        ...contentWorkflowSearch(previous),
        work_item_id: undefined,
        section_heading: undefined,
        planning_digest: undefined,
        workspace: undefined,
        text: undefined,
        review: undefined,
        browse: undefined,
        new_page: undefined
      })
    });
  };
  const {
    selectedWorkspace,
    entry,
    inventory,
    diagnostics,
    operatorContext
  } = useContentWorkflowQueries(
    selectedWorkItemId,
    browseInventory,
    !selectedWorkItemId && !newPageOpen && !browseInventory
  );

  return (
    <ContentWorkflowRouteState
      selectedWorkItemId={selectedWorkItemId}
      selectedWorkspace={selectedWorkspace}
      entry={entry}
      inventory={inventory}
      diagnostics={diagnostics}
      reviewOpen={reviewOpen}
      browseInventory={browseInventory}
      newPageOpen={newPageOpen}
      newPageId={newPageId}
      operatorLabel={operatorContext.data?.request_label ?? null}
      onSelectWorkItem={selectWorkItem}
      onBrowseInventory={() => {
        void navigate({
          to: "/content-workflow",
          search: (previous) => ({ ...contentWorkflowSearch(previous), browse: undefined, new_page: undefined, view: "browse" })
        });
      }}
      onOpenNewPage={() => {
        void navigate({
          to: "/content-workflow",
          search: (previous) => ({ ...contentWorkflowSearch(previous), browse: undefined, new_page: undefined, view: "new" })
        });
      }}
      onNewPageBriefSaved={(briefId) => {
        void navigate({
          to: "/content-workflow",
          search: (previous) => ({ ...contentWorkflowSearch(previous), browse: undefined, new_page: briefId, view: "new" })
        });
      }}
      onCloseEntrySecondaryView={() => {
        void navigate({
          to: "/content-workflow",
          search: (previous) => ({ ...contentWorkflowSearch(previous), browse: undefined, new_page: undefined, view: undefined })
        });
      }}
      onOpenReview={(workItemId) => {
        void navigate({
          to: "/content-workflow/$workItemId",
          params: { workItemId },
          search: (previous) => ({
            work_item_id: undefined,
            section_heading: previous.section_heading,
            planning_digest: previous.planning_digest,
            workspace: undefined,
            text: undefined,
            review: undefined,
            browse: undefined,
            new_page: undefined,
            view: "review"
          })
        });
      }}
      onReturnToText={(workItemId) => {
        void navigate({
          to: "/content-workflow/$workItemId",
          params: { workItemId },
          search: (previous) => ({
            work_item_id: undefined,
            section_heading: previous.section_heading,
            planning_digest: previous.planning_digest,
            workspace: undefined,
            text: undefined,
            review: undefined,
            browse: undefined,
            new_page: undefined,
            view: undefined
          })
        });
      }}
    />
  );
}

function stringFromSearch(search: string, key: string) {
  const value = new URLSearchParams(search).get(key);
  return value || null;
}

function contentWorkflowSearch(previous: {
  work_item_id?: string;
  section_heading?: string;
  planning_digest?: string;
  workspace?: string;
  text?: 1;
  review?: 1;
  browse?: 1;
  new_page?: string;
  view?: "review" | "browse" | "new";
}) {
  return {
    work_item_id: previous.work_item_id,
    section_heading: previous.section_heading,
    planning_digest: previous.planning_digest,
    workspace: previous.workspace,
    text: previous.text,
    review: previous.review,
    browse: previous.browse,
    new_page: previous.new_page,
    view: previous.view
  };
}

function ContentWorkflowRouteState({
  selectedWorkItemId,
  selectedWorkspace,
  entry,
  inventory,
  diagnostics,
  reviewOpen,
  browseInventory,
  newPageOpen,
  newPageId,
  operatorLabel,
  onSelectWorkItem,
  onBrowseInventory,
  onOpenNewPage,
  onNewPageBriefSaved,
  onCloseEntrySecondaryView,
  onOpenReview,
  onReturnToText
}: {
  selectedWorkItemId: string | null;
  selectedWorkspace: ContentSelectedWorkspaceQuery;
  entry: ContentWorkflowEntryQuery;
  inventory: ContentInventoryCatalogQuery;
  diagnostics: ReturnType<typeof useContentWorkflowQueries>["diagnostics"];
  reviewOpen: boolean;
  browseInventory: boolean;
  newPageOpen: boolean;
  newPageId: string | null;
  operatorLabel: string | null;
  onSelectWorkItem: (workItemId: string) => void;
  onBrowseInventory: () => void;
  onOpenNewPage: () => void;
  onNewPageBriefSaved: (briefId: string) => void;
  onCloseEntrySecondaryView: () => void;
  onOpenReview: (workItemId: string) => void;
  onReturnToText: (workItemId: string) => void;
}) {
  if (!selectedWorkItemId) {
    if (newPageOpen) {
      return (
        <ContentWorkflowEntryPanel
          entry={entry.data ?? null}
          inventory={inventory.data ?? null}
          diagnostics={null}
          browseInventory={browseInventory}
          newPageOpen={newPageOpen}
          newPageId={newPageId}
          onBrowseInventory={onBrowseInventory}
          onCloseSecondaryView={onCloseEntrySecondaryView}
          onOpenNewPage={onOpenNewPage}
          onNewPageBriefSaved={onNewPageBriefSaved}
          onSelectWorkItem={onSelectWorkItem}
        />
      );
    }
    if (entry.isLoading) return <ContentWorkflowEntryPending />;
    if (entry.error || !entry.data) {
      return <ContentWorkflowEntryFailure onRetry={() => void entry.refetch()} />;
    }
    return (
      <ContentWorkflowEntryPanel
        entry={entry.data}
        inventory={inventory.data ?? null}
        diagnostics={diagnostics.data ?? null}
        browseInventory={browseInventory}
        newPageOpen={newPageOpen}
        newPageId={newPageId}
        onBrowseInventory={onBrowseInventory}
        onCloseSecondaryView={onCloseEntrySecondaryView}
        onOpenNewPage={onOpenNewPage}
        onNewPageBriefSaved={onNewPageBriefSaved}
        onSelectWorkItem={onSelectWorkItem}
      />
    );
  }
  if (!reviewOpen) {
    return (
      <ContentTextWorkspace
        workItemId={selectedWorkItemId}
        selectedWorkspace={selectedWorkspace}
        requestedBy={operatorLabel ?? "operator_local_dashboard"}
        onOpenReview={onOpenReview}
      />
    );
  }
  return <ContentReviewRoute
    selectedWorkspace={selectedWorkspace}
    operatorLabel={operatorLabel}
    onReturnToText={onReturnToText}
  />;
}

function ContentWorkflowEntryPending() {
  return <main className="mx-auto min-h-screen max-w-7xl px-4 py-5 lg:px-8"><section className="rounded-2xl border border-line bg-white p-5 shadow-sm"><p className="text-lg font-semibold text-ink">Wczytuję wybór pracy…</p><p className="mt-2 text-sm text-slate-700">Pobieram dostępne tryby i sprawy do pracy. To nie jest błąd.</p></section></main>;
}

function ContentWorkflowEntryFailure({ onRetry }: { onRetry: () => void }) {
  return <main className="mx-auto min-h-screen max-w-7xl px-4 py-5 lg:px-8"><section className="rounded-2xl border border-wait/30 bg-white p-5 shadow-sm"><p className="text-lg font-semibold text-ink">Nie udało się wczytać wyboru pracy.</p><button type="button" className="mt-3 rounded-md bg-action px-3 py-2 text-sm font-semibold text-white" onClick={onRetry}>Spróbuj ponownie</button></section></main>;
}
