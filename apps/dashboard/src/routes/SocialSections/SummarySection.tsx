import { ShieldAlert } from "lucide-react";

import type { SocialDraftContext, SocialHistoryInventory } from "../../lib/api";
import { MetricTile } from "../../components/OperatorPrimitives";
import { TraceLine } from "../../components/TraceLine";

export function SocialDecisionSummary({
  socialContext,
  inventory
}: {
  socialContext: SocialDraftContext;
  inventory: SocialHistoryInventory;
}) {
  return (
    <section className="rounded-md border border-wait/30 bg-wait/10 p-4">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 rounded-md border border-wait/30 bg-white p-2 text-wait">
          <ShieldAlert aria-hidden="true" size={18} />
        </div>
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-wait">
            Social jest tylko do review
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-700">
            {socialContext.operator_next_step}
          </p>
        </div>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <MetricTile label="Blokady twierdzeń" value={socialContext.blocked_claims.length} />
        <MetricTile label="Wymagane źródła historii" value={inventory.required_sources.length} />
        <MetricTile label="Akcje review-only" value={socialContext.draft_action_ids.length} />
      </div>
      <div className="mt-4 grid gap-2 text-xs text-slate-600 md:grid-cols-2">
        <TraceLine
          label="Czego nie wolno twierdzić"
          values={socialContext.blocked_claims.slice(0, 6)}
          empty="Brak blokad twierdzeń oznaczałby brak bezpiecznego zakresu social."
        />
        <TraceLine
          label="Brakujące dowody historii"
          values={socialContext.missing_history_evidence}
          empty="Historia social nie wymaga dodatkowych dowodów."
        />
      </div>
    </section>
  );
}
