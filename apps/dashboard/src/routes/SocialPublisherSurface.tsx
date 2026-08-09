import { useQuery } from "@tanstack/react-query";

import {
  getSocialPublisherContextPack,
  getSocialReuseProposals
} from "../lib/api";
import {
  BlockerNotice,
  LoadingBand,
  MetricTile
} from "../components/OperatorPrimitives";
import { ActionFocus } from "./ActionPanels";
import { SocialHistoryBlocker } from "./SocialSections/HistorySection";
import { SocialReuseProposalsPanel } from "./SocialSections/ReuseProposalsSection";
import type { SocialHistoryStatusFormatters } from "./SocialSections/Shared";
import { SocialDecisionSummary } from "./SocialSections/SummarySection";

export function SocialPublisherSurface() {
  const contextPack = useQuery({
    queryKey: ["social-publisher-context-pack"],
    queryFn: getSocialPublisherContextPack
  });
  const proposals = useQuery({
    queryKey: ["social-reuse-proposals"],
    queryFn: () => getSocialReuseProposals()
  });

  if (contextPack.isLoading) return <LoadingBand />;
  if (contextPack.error || !contextPack.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się pobrać social context-packa. WILQ nie może pokazać szkiców ani blokad bez API." />
      </main>
    );
  }

  const socialContext = contextPack.data.social_draft_context;
  const inventory = socialContext.social_history_inventory;
  const actions = contextPack.data.active_action_objects.filter((action) =>
    socialContext.draft_action_ids.includes(action.id)
  );

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Publikacje social</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            WILQ może przygotować tylko kierunki postów do sprawdzenia. Publikacja i
            claim o braku powtórek są zablokowane, dopóki nie ma dostępu oraz historii
            postów LinkedIn/Facebook.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Tryb" value={socialContext.mode === "review_only" ? "review" : socialContext.mode} />
          <MetricTile label="Publikacja" value={socialContext.publish_allowed ? "dostępna" : "zablokowana"} />
          <MetricTile label="Historia" value={inventory.status_label} />
        </div>
      </div>

      <div className="grid gap-6">
        <SocialDecisionSummary socialContext={socialContext} inventory={inventory} />
        <SocialHistoryBlocker
          inventory={inventory}
          socialContext={socialContext}
          statusFormatters={SOCIAL_HISTORY_STATUS_FORMATTERS}
        />
        <SocialReuseProposalsPanel proposals={proposals.data} loading={proposals.isLoading} />
        <ActionFocus actions={actions} />
      </div>
    </main>
  );
}

const SOCIAL_HISTORY_STATUS_FORMATTERS: SocialHistoryStatusFormatters = {
  access: formatAccessStatus,
  inventory: formatInventoryStatus,
  metadataSource: formatMetadataSourceStatus
};

function formatAccessStatus(status: string) {
  if (status === "missing_credentials") return "brakuje dostępu";
  if (status === "configured") return "dostęp skonfigurowany";
  return "niedostępne";
}

function formatInventoryStatus(status: string) {
  if (status === "review_ready") return "gotowy do oceny";
  return "brak";
}

function formatMetadataSourceStatus(status: string) {
  if (status === "review_ready") return "poprawne metadane";
  if (status === "invalid") return "wymaga poprawy";
  return "niepodpięte";
}
