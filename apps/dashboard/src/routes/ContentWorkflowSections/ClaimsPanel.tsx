import type { ContentDraftRevision } from "../../lib/api";

export function ContentClaimLedgerPanel({ revision }: { revision: ContentDraftRevision }) {
  const ledger = revision.claim_ledger;
  if (!ledger) return null;
  const entries = [...ledger.entries].sort((left, right) => {
    return contentClaimStatusPriority(left.status) - contentClaimStatusPriority(right.status);
  });
  return (
    <section className="mt-4 rounded-xl border border-line bg-white p-4" data-testid="content-claim-ledger">
      <h2 className="text-base font-semibold text-ink">Twierdzenia i dowody</h2>
      <ul className="mt-3 space-y-3">
        {entries.map((entry) => (
          <li key={entry.id} className="rounded-lg border border-line p-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <p className="font-medium text-ink">{entry.claim_text}</p>
              <span className="flex flex-wrap items-center gap-1.5">
                {entry.required ? (
                  <span className="rounded-full bg-wait/15 px-2.5 py-1 text-xs font-semibold text-ink">
                    wymagane
                  </span>
                ) : null}
                <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">
                  {contentClaimStatusLabel(entry.status)}
                </span>
              </span>
            </div>
            <p className="mt-2 text-xs leading-5 text-slate-600">
              Źródła: {entry.source_connectors.length > 0 ? entry.source_connectors.join(", ") : "brak"}
              {" · "}Dowody: {entry.evidence_ids.length}
            </p>
            {entry.reason ? (
              <p className="mt-2 text-sm leading-5 text-slate-700">{entry.reason}</p>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}

export type ContentClaimStatus = NonNullable<
  ContentDraftRevision["claim_ledger"]
>["entries"][number]["status"];

export function contentClaimStatusPriority(status: ContentClaimStatus) {
  switch (status) {
    case "blocked":
    case "blocked_until_measurement":
    case "needs_human_review":
      return 0;
    case "allowed_with_evidence":
    case "allowed_general":
      return 1;
    default:
      return status satisfies never;
  }
}

export function contentClaimStatusLabel(status: ContentClaimStatus) {
  switch (status) {
    case "allowed_with_evidence":
      return "z dowodem";
    case "blocked":
    case "blocked_until_measurement":
      return "blokuje";
    case "allowed_general":
      return "brak dowodu";
    case "needs_human_review":
      return "wymaga decyzji człowieka";
    default:
      return status satisfies never;
  }
}
