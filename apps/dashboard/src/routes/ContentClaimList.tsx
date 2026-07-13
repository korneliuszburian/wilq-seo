import type { ContentWorkflowSnapshot } from "./contentWorkflowRuntime";

export function ContentClaimList({
  title,
  empty,
  claims
}: {
  title: string;
  empty: string;
  claims: ContentWorkflowSnapshot["claimLedger"]["entries"];
}) {
  return (
    <div className="rounded-md border border-line bg-surface p-3">
      <h3 className="text-sm font-semibold text-ink">{title}</h3>
      {claims.length ? (
        <ul className="mt-2 space-y-3">
          {claims.slice(0, 3).map((claim) => (
            <li key={claim.id} className="text-sm leading-6 text-slate-700">
              <div className="font-medium text-ink">{claim.claim_text}</div>
              <div className="mt-1 text-xs leading-5 text-slate-500">{claim.reason}</div>
              <div className="mt-1 text-xs leading-5 text-slate-500">
                Dowody: {claim.evidence_ids.length ? claim.evidence_ids.join(", ") : "brak"}
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm leading-6 text-slate-600">{empty}</p>
      )}
    </div>
  );
}
