import type { AdsDiagnosticsResponse, DemandGenReadinessContract } from "../../lib/api";
import { adsMissingDateLabel } from "../../lib/adsLabels";

type AdsDecision = AdsDiagnosticsResponse["decision_queue"][number];

export function pickPrimaryDecision(data: AdsDiagnosticsResponse) {
  const topIds = data.operator_summary.top_decision_ids;
  return (
    topIds.map((id) => data.decision_queue.find((decision) => decision.id === id)).find(Boolean) ??
    data.decision_queue[0]
  );
}

export function adsPriorityLabel(decision: AdsDecision): string {
  return decision.priority_label.trim() || "brak priorytetu";
}

export function adsRisk(decision: AdsDecision): AdsDecision["risk"] | "blocked" {
  return decision.status === "blocked" ? "blocked" : decision.risk;
}

export function adsRiskLabel(decision: AdsDecision): string {
  return decision.risk_label.trim() || decision.status_label.trim() || "status do sprawdzenia";
}

export function uniqueLabels(values: string[]) {
  return Array.from(new Set(values.filter((value) => value.trim().length > 0)));
}

export function metricTileValue(data: DemandGenReadinessContract | null, key: string) {
  const value = data?.metric_tiles[key];
  if (value === undefined) return `${key}: brak`;
  return `${key}: ${value}`;
}

export function formatCost(totalCostMicros: number, currencyCode?: string | null) {
  const value = totalCostMicros / 1_000_000;
  const formatted = new Intl.NumberFormat("pl-PL", {
    maximumFractionDigits: 2,
    style: currencyCode ? "currency" : "decimal",
    currency: currencyCode ?? undefined
  }).format(value);
  return `koszt ${formatted}`;
}

export function dateLabel(value?: string | null) {
  if (!value) return adsMissingDateLabel;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return adsMissingDateLabel;
  return new Intl.DateTimeFormat("pl-PL", {
    day: "numeric",
    month: "long",
    year: "numeric"
  }).format(date);
}
