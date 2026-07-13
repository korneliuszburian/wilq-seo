import { ShieldCheck } from "lucide-react";

import type { ContentWorkflowSnapshot } from "./contentWorkflowRuntime";
import { ContentWorkflowFactTile as FactTile } from "./ContentWorkflowFactTile";
import { ContentClaimList as ClaimList } from "./ContentClaimList";

export function ClaimLedgerGatePanel({ data }: { data: ContentWorkflowSnapshot }) {
  const ledger = data.claimLedger;
  const allowedClaims = ledger.entries.filter((entry) => entry.status.startsWith("allowed"));
  const reviewClaims = ledger.entries.filter((entry) => entry.status === "needs_human_review" || entry.strength === "weak");
  const blockedClaims = ledger.entries.filter((entry) => entry.status === "blocked" || entry.status === "blocked_until_measurement");
  const requiredClaims = ledger.entries.filter((entry) => entry.required);

  return (
    <section id="content-workflow-claim-ledger" className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2"><ShieldCheck aria-hidden="true" size={18} className="text-action" /><h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">Claim Ledger: co wolno powiedzieć</h2></div>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">To jest bramka między briefem a szkicem. WILQ pokazuje, które twierdzenia mają dowód, które wymagają decyzji człowieka i których nie wolno użyć w gotowym języku.</p>
        </div>
        <div className="grid w-full gap-2 text-sm sm:w-auto sm:min-w-80 sm:grid-cols-4"><FactTile label="Do szkicu" value={`${allowedClaims.length}`} /><FactTile label="Review" value={`${reviewClaims.length}`} /><FactTile label="Zablokowane" value={`${blockedClaims.length}`} /><FactTile label="Wymagane" value={`${requiredClaims.length}`} /></div>
      </div>
      <div className="mt-4 grid gap-3 lg:grid-cols-3">
        <ClaimList title="Do szkicu" empty="Brak twierdzeń gotowych do szkicu." claims={allowedClaims} />
        <ClaimList title="Wymaga review" empty="Brak twierdzeń wymagających dodatkowego review." claims={reviewClaims} />
        <ClaimList title="Zablokowane" empty="Brak twierdzeń zablokowanych w ledgerze." claims={blockedClaims} />
      </div>
    </section>
  );
}
