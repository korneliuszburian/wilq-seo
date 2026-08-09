import { AlertTriangle } from "lucide-react";
import type { ComponentType } from "react";

import { PlainChipRow } from "../../components/OperatorPrimitives";
import type { ContentServiceProfileResponse } from "../../lib/api";
import {
  humanizeEnum,
  operatorText,
  priorityLabel,
  reviewScopeLabel,
  type CoverageGap,
  type PrivateProposal
} from "./Shared";

type ReviewAction = ContentServiceProfileResponse["review_actions"][number];
type ReviewActionSummary = ContentServiceProfileResponse["review_action_summary"];
type ListComponent = ComponentType<{ label: string; values: string[] }>;

const SOURCE_TYPE_LABELS: Record<string, string> = {
  reviewed_internal: "źródło wewnętrzne do review",
  private_candidate: "prywatna propozycja wiedzy",
  public_site: "publiczna strona",
  connector_metric: "metryka z connectora",
  legal_update: "aktualizacja prawna",
  uat_feedback: "feedback UAT"
};

const PRIVACY_CLASS_LABELS: Record<string, string> = {
  commit_safe: "bezpieczne w repo",
  private_local: "prywatne lokalnie",
  redacted_only: "tylko po redakcji"
};

const FACT_SCOPE_LABELS: Record<string, string> = {
  service: "zakres: usługa",
  buyer_problem: "zakres: problem kupującego",
  cta: "zakres: CTA",
  claim_policy: "zakres: polityka twierdzeń",
  evidence_requirement: "zakres: wymaganie dowodowe",
  metric_signal: "zakres: sygnał metryczny"
};

const FRESHNESS_LABELS: Record<string, string> = {
  current: "aktualne",
  stale: "nieaktualne",
  unknown: "aktualność niepewna"
};

const AUDIENCE_LABELS: Record<string, string> = {
  company_wide: "dla całej firmy",
  role_restricted: "dla wybranej roli",
  unknown: "odbiorca niepewny"
};

const SUPPORT_LEVEL_LABELS: Record<string, string> = {
  direct: "wsparcie bezpośrednie",
  partial: "częściowe wsparcie",
  inferred: "wniosek pośredni",
  weak: "słabe wsparcie"
};

const RISK_TIER_LABELS: Record<string, string> = {
  high: "wysokie ryzyko",
  medium: "średnie ryzyko",
  low: "niskie ryzyko"
};

export function PrivateProposalCards({
  proposals,
  List
}: {
  proposals: PrivateProposal[];
  List: ListComponent;
}) {
  if (proposals.length === 0) return null;
  return (
    <div className="mt-4 grid gap-3 lg:grid-cols-2">
      {proposals.map((proposal) => (
        <article key={proposal.proposal_id} className="rounded-md border border-line p-3">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h3 className="text-sm font-semibold">{proposal.target_card_title}</h3>
              <p className="mt-1 text-xs leading-5 text-slate-500">
                {proposal.source_locator_label}
              </p>
            </div>
            <span className="rounded-md border border-line px-2 py-0.5 text-xs text-slate-600">
              {reviewStatusLabel(proposal.review_status)}
            </span>
          </div>
          <PlainChipRow
            className="mt-3"
            values={[
              sourceTypeLabel(proposal.source_type),
              privacyClassLabel(proposal.privacy_class),
              factScopeLabel(proposal.scope),
              sourceClassLabel(proposal.source_class_label),
              `aktualność: ${freshnessLabel(proposal.freshness_status)}`,
              `odbiorcy: ${audienceLabel(proposal.audience)}`,
              supportLevelLabel(proposal.support_level),
              riskTierLabel(proposal.risk_tier),
              proposal.confidence_label,
              proposal.promotion_allowed ? "promocja dozwolona" : "bez promocji"
            ]}
          />
          <p className="mt-2 text-sm leading-6 text-slate-600">{proposal.safe_next_step}</p>
          <p className="mt-2 text-xs leading-5 text-slate-500">
            {operatorText(proposal.blocked_write_claim)}
          </p>
          <List label="Klasy danych" values={proposal.data_classes} />
          <List label="Bloki źródła" values={proposal.source_block_refs} />
          <p className="mt-2 text-xs leading-5 text-slate-500">
            Retencja: {retentionLabel(proposal.retention_decision)}
          </p>
          <List label="Ścieżka usunięcia" values={proposal.deletion_path.map(operatorText)} />
          <List label="Bramki ewaluacji" values={proposal.eval_case_ids} />
          <List label="Twierdzenia zablokowane" values={proposal.blocked_claims} />
          <p className="mt-2 text-xs leading-5 text-slate-500">
            Rola oceny: {operatorText(proposal.owner_role)}
          </p>
        </article>
      ))}
    </div>
  );
}

export function CoverageGaps({ gaps }: { gaps: CoverageGap[] }) {
  if (gaps.length === 0) return null;
  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-normal text-slate-700">
        <AlertTriangle aria-hidden="true" size={16} />
        Luki do review
      </div>
      <div className="mt-4 grid gap-3">
        {gaps.map((gap) => (
          <div key={gap.gap_id} className="rounded-md border border-wait/30 bg-wait/10 p-3">
            <h3 className="text-sm font-semibold text-wait">{gap.label}</h3>
            <p className="mt-1 text-sm leading-6 text-slate-700">{gap.reason}</p>
            <p className="mt-1 text-sm leading-6 text-slate-600">{gap.safe_next_step}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export function ReviewActions({
  actions,
  summary,
  reviewDecisionLabel
}: {
  actions: ReviewAction[];
  summary: ReviewActionSummary;
  reviewDecisionLabel: (value: string) => string;
}) {
  if (actions.length === 0) return null;
  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
        Akcje review
      </h2>
      <PlainChipRow
        className="mt-3"
        values={[
          `${summary.total_count} razem`,
          `${summary.public_service_review_count} publicznych usług`,
          `${summary.private_service_review_count} prywatne usługi`,
          `${summary.private_policy_review_count} prywatne polityki twierdzeń`,
          `${summary.review_request_count} prośby o review`,
          summary.prepare_count > 0 ? `${summary.prepare_count} przygotowań` : null
        ]}
      />
      <p className="mt-2 text-sm leading-6 text-slate-600">{summary.safe_next_step}</p>
      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        {actions.map((action) => (
          <div key={action.action_id} className="rounded-md border border-line p-3">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-sm font-semibold">{action.label}</h3>
              <span className="rounded-md border border-line px-2 py-0.5 text-xs text-slate-600">
                {actionModeLabel(action.mode)}
              </span>
              <span className="rounded-md border border-line px-2 py-0.5 text-xs text-slate-600">
                {reviewScopeLabel(action.review_scope)}
              </span>
              <span className="rounded-md border border-line px-2 py-0.5 text-xs text-slate-600">
                {priorityLabel(action.priority)}
              </span>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-600">{action.reason}</p>
            {action.decision_options.length > 0 ? (
              <p className="mt-2 text-xs leading-5 text-slate-500">
                Decyzje: {action.decision_options.map(reviewDecisionLabel).join(", ")}
              </p>
            ) : null}
            {action.review_requirements.length > 0 ? (
              <p className="mt-2 text-xs leading-5 text-slate-500">
                Wymagane pola:{" "}
                {action.review_requirements
                  .filter((requirement) => requirement.required)
                  .map((requirement) => requirement.label)
                  .join(", ")}
                {action.review_requirements.some(
                  (requirement) => requirement.field === "follow_up_beads"
                )
                  ? "; follow_up_beads przy blokadzie"
                  : ""}
                .
              </p>
            ) : null}
            <p className="mt-2 text-xs leading-5 text-slate-500">
              {action.blocked_write_claim}
            </p>
            <p className="mt-1 text-xs leading-5 text-slate-500">
              Rola: {action.required_human_role}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

function reviewStatusLabel(value: string) {
  if (value === "review_required") return "wymaga review";
  if (value === "approved") return "zatwierdzone";
  if (value === "rejected") return "odrzucone";
  if (value === "stale") return "nieaktualne";
  return humanizeEnum(value);
}

function actionModeLabel(value: string) {
  if (value === "prepare") return "przygotowanie";
  if (value === "review") return "review";
  if (value === "apply") return "zapis";
  return humanizeEnum(value);
}

function sourceTypeLabel(value: string) {
  return SOURCE_TYPE_LABELS[value] ?? humanizeEnum(value);
}

function privacyClassLabel(value: string) {
  return PRIVACY_CLASS_LABELS[value] ?? humanizeEnum(value);
}

function factScopeLabel(value: string) {
  return FACT_SCOPE_LABELS[value] ?? `zakres: ${humanizeEnum(value)}`;
}

function freshnessLabel(value: string) {
  return FRESHNESS_LABELS[value] ?? humanizeEnum(value);
}

function audienceLabel(value: string) {
  return AUDIENCE_LABELS[value] ?? humanizeEnum(value);
}

function supportLevelLabel(value: string) {
  return SUPPORT_LEVEL_LABELS[value] ?? humanizeEnum(value);
}

function riskTierLabel(value: string) {
  return RISK_TIER_LABELS[value] ?? humanizeEnum(value);
}

function retentionLabel(value: string) {
  if (value === "pending_owner_decision") return "decyzja właściciela wymagana";
  if (value === "retain_while_source_approved") {
    return "utrzymuj tylko dopóki źródło jest zatwierdzone";
  }
  if (value === "short_window_only") return "krótkie okno retencji";
  if (value === "do_not_retain") return "nie utrzymuj";
  return humanizeEnum(value);
}

function sourceClassLabel(value: string) {
  return value
    .replace("review-required", "wymaga oceny")
    .replace("claim-policy", "polityka twierdzeń")
    .replace("evidence-policy", "wymaganie dowodowe")
    .replace("internal service context", "wewnętrzny kontekst usługi")
    .replace("source fact", "fakt źródłowy");
}
