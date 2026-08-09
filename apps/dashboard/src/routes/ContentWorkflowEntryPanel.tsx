import { useQueryClient } from "@tanstack/react-query";

import type {
  ContentDiagnosticsResponse,
  ContentInventoryCatalogResponse,
  ContentWorkflowEntryResponse
} from "../lib/api";
import { ContentWorkflowInventoryBrowse } from "./ContentWorkflowEntryPanelSections/Flows";
import { ContentWorkflowIntentStart } from "./ContentWorkflowEntryPanelSections/IntentCards";
import { ContentWorkflowNewPageBrief } from "./ContentWorkflowEntryPanelSections/NewPageBrief";

export function ContentWorkflowEntryPanel({
  entry,
  inventory,
  diagnostics,
  browseInventory,
  newPageOpen,
  newPageId,
  onBrowseInventory,
  onCloseSecondaryView,
  onOpenNewPage,
  onNewPageBriefSaved,
  onSelectWorkItem
}: {
  entry: ContentWorkflowEntryResponse | null;
  inventory: ContentInventoryCatalogResponse | null;
  diagnostics: ContentDiagnosticsResponse | null;
  browseInventory: boolean;
  newPageOpen: boolean;
  newPageId: string | null;
  onBrowseInventory: () => void;
  onCloseSecondaryView: () => void;
  onOpenNewPage: () => void;
  onNewPageBriefSaved: (briefId: string) => void;
  onSelectWorkItem: (workItemId: string) => void;
}) {
  const queryClient = useQueryClient();
  const refreshEntry = () => {
    void queryClient.invalidateQueries({ queryKey: ["content-workflow", "entry"] });
    void queryClient.invalidateQueries({ queryKey: ["content-workflow", "diagnostics"] });
  };
  if (newPageOpen) {
    return <ContentWorkflowNewPageBrief briefId={newPageId === "1" ? null : newPageId} onReturn={onCloseSecondaryView} onSaved={onNewPageBriefSaved} />;
  }
  if (browseInventory) {
    return <ContentWorkflowInventoryBrowse inventory={inventory} onReturn={onCloseSecondaryView} onSelectWorkItem={onSelectWorkItem} />;
  }
  if (!entry) return null;
  return <ContentWorkflowIntentStart entry={entry} diagnostics={diagnostics} onBrowseInventory={onBrowseInventory} onOpenNewPage={onOpenNewPage} onSelectWorkItem={onSelectWorkItem} onSourcesRefreshed={refreshEntry} />;
}
