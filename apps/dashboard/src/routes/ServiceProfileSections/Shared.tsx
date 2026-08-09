import type { ContentServiceProfileResponse } from "../../lib/api";

export type ApprovalReadiness = ContentServiceProfileResponse["approval_readiness"];
export type CoverageGap = ContentServiceProfileResponse["coverage_gaps"][number];
export type PrivateProposal =
  ContentServiceProfileResponse["private_source_proposals"][number];
export type ServiceSection = ContentServiceProfileResponse["service_sections"][number];

const REVIEW_SCOPE_LABELS: Record<string, string> = {
  public_service_card: "publiczna karta usługi",
  private_service_proposal: "prywatna propozycja usługi",
  private_claim_policy_proposal: "prywatna propozycja polityki twierdzeń",
  private_evidence_policy_proposal: "prywatna propozycja wymagań dowodowych"
};

const PRIORITY_LABELS: Record<string, string> = {
  high: "wysoki priorytet",
  medium: "średni priorytet",
  low: "niski priorytet"
};

export function reviewScopeLabel(value: string) {
  return REVIEW_SCOPE_LABELS[value] ?? humanizeEnum(value);
}

export function priorityLabel(value: string) {
  return PRIORITY_LABELS[value] ?? humanizeEnum(value);
}

export function operatorText(value: string) {
  return value
    .replace("reviewer prawny", "osoba oceniająca prawnie")
    .replace("reviewerowi", "osobie oceniającej")
    .replace("To jest redacted proposal", "To jest zredagowana propozycja")
    .replace("redacted proposal", "zredagowaną propozycję")
    .replace("redacted", "zredagowane")
    .replace("do review", "do oceny")
    .replace("source fact", "faktu źródłowego")
    .replace("knowledge card", "karty wiedzy")
    .replace("owner", "właściciela");
}

export function humanizeEnum(value: string) {
  return value.replace(/[_-]+/g, " ");
}
