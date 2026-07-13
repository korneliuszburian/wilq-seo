import { ContentWorkflowFactTile as FactTile } from "./ContentWorkflowFactTile";
import type { ContentWorkflowSnapshot } from "./contentWorkflowRuntime";

type ServiceProfileContext = ContentWorkflowSnapshot["serviceProfileContext"];

export function ServiceProfileDecisionStrip({ context }: { context: ServiceProfileContext }) {
  const statusChips = compactServiceProfileText([
    context.source_summary_label,
    prefixedServiceProfileText("Stan wiedzy", context.freshness_label)
  ]);
  const blocker = context.missing_contracts[0] ?? null;

  return (
    <section aria-label="Decyzja usługi i zasad twierdzeń" className="mt-4 border-t border-line pt-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">Usługa i zasady twierdzeń</div>
          <h3 className="mt-1 text-base font-semibold text-ink">{context.service_label ?? "Nie ustalono usługi dla tego work itemu"}</h3>
          <p className="mt-1 max-w-4xl text-sm leading-6 text-slate-700">{context.reason}</p>
        </div>
        <span className="rounded-md border border-wait/30 bg-wait/10 px-2 py-1 text-xs font-semibold text-wait">{context.status_label}</span>
      </div>
      <ServiceProfileStatusChips chips={statusChips} />
      <ServiceProfileBlocker blocker={blocker} />
      <p className="mt-3 text-xs leading-5 text-slate-600">{context.claim_policy_scope_label}</p>
      <p className="mt-3 text-sm font-medium leading-6 text-ink">{context.safe_next_step}</p>
      <div className="mt-3 grid gap-2 sm:grid-cols-3">
        <FactTile label="Dopuszczalne dla usługi" value={`${context.allowed_claims.length}`} />
        <FactTile label="Review dla usługi" value={`${context.claims_needing_review.length}`} />
        <FactTile label="Nie używaj dla usługi" value={`${context.blocked_claims.length}`} />
      </div>
      <ServiceProfileTechnicalDetails context={context} />
    </section>
  );
}

function ServiceProfileStatusChips({ chips }: { chips: string[] }) {
  if (!chips.length) return null;
  return <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-600">{chips.map((chip) => <span key={chip} className="rounded-md border border-line bg-surface px-2 py-1">{chip}</span>)}</div>;
}

function ServiceProfileBlocker({ blocker }: { blocker: string | null }) {
  if (blocker === null) return null;
  return <p className="mt-3 rounded-md border border-wait/30 bg-wait/10 px-3 py-2 text-sm leading-6 text-wait"><span className="font-semibold">Bloker:</span> {blocker}</p>;
}

function ServiceProfileTechnicalDetails({ context }: { context: ServiceProfileContext }) {
  const details = compactServiceProfileText([
    ...context.evidence_requirements.slice(0, 3),
    ...context.missing_contracts.slice(1).map((contract) => `Brakuje: ${contract}`),
    ...serviceProfileClaimDetails(context),
    ...serviceProfileTechnicalTrace(context)
  ]);
  if (!details.length) return null;
  return <details className="mt-3 rounded-md border border-line bg-surface px-3 py-2 text-sm text-slate-700"><summary className="cursor-pointer font-semibold text-ink">Dowody i warunki</summary><div className="mt-3 space-y-2 leading-6">{details.map((detail) => <p key={detail}>{detail}</p>)}</div></details>;
}

function serviceProfileClaimDetails(context: ServiceProfileContext): string[] {
  return [
    ...serviceProfileClaimLines("Dopuszczalne dla tej usługi", context.allowed_claims),
    ...serviceProfileClaimLines("Wymaga review dla tej usługi", context.claims_needing_review),
    ...serviceProfileClaimLines("Nie używaj dla tej usługi", context.blocked_claims)
  ];
}

function serviceProfileClaimLines(label: string, claims: string[]) {
  return claims.map((claim) => `${label}: ${claim}`);
}

function serviceProfileTechnicalTrace(context: ServiceProfileContext): Array<string | null> {
  return [
    serviceProfileTraceLine("Źródła techniczne", context.source_connectors),
    serviceProfileTraceLine("Dowody", context.evidence_ids),
    serviceProfileTraceLine("Karty wiedzy", context.knowledge_card_ids),
    serviceProfileReviewTrace(context)
  ];
}

function serviceProfileTraceLine(label: string, values: string[]) {
  return values.length ? `${label}: ${values.join(", ")}` : null;
}

function serviceProfileReviewTrace(context: ServiceProfileContext) {
  if (!context.review_action_id) return null;
  const label = context.review_action_label ? ` — ${context.review_action_label}` : "";
  return `Akcja review: ${context.review_action_id}${label}`;
}

function prefixedServiceProfileText(prefix: string, value: string) {
  return value ? `${prefix}: ${value}` : null;
}

function compactServiceProfileText(values: Array<string | null>) {
  return values.filter((value): value is string => Boolean(value));
}
