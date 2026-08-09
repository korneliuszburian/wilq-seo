import type { AdsDiagnosticsResponse, DemandGenReadinessContract } from "../../lib/api";

type AdsDecision = AdsDiagnosticsResponse["decision_queue"][number];

export function pickPrimaryDecision(data: AdsDiagnosticsResponse) {
  const topIds = data.operator_summary.top_decision_ids;
  return (
    topIds.map((id) => data.decision_queue.find((decision) => decision.id === id)).find(Boolean) ??
    data.decision_queue[0]
  );
}

export function priorityFromDecision(decision: AdsDecision): "P1" | "P2" | "P3" | "-" {
  if (decision.status === "blocked" || decision.priority <= 20) return "P1";
  if (decision.priority <= 40) return "P2";
  if (decision.priority <= 70) return "P3";
  return "-";
}

export function riskFromDecision(risk: AdsDecision["risk"]): "low" | "medium" | "high" | "blocked" {
  if (risk === "critical") return "high";
  return risk;
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
  if (!value) return "Dzisiaj";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Dzisiaj";
  return new Intl.DateTimeFormat("pl-PL", {
    day: "numeric",
    month: "long",
    year: "numeric"
  }).format(date);
}
