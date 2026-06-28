import type { MetricFact } from "../lib/api";

export function MetricFactChips({ facts }: { facts: MetricFact[] }) {
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {facts.map((fact, index) => (
        <span
          key={metricFactKey(fact, index)}
          className="rounded border border-line bg-slate-50 px-2 py-1 text-xs text-slate-700"
        >
          {metricFactLabel(fact)}: {formatMetricFactValue(fact)}
          {Object.keys(fact.dimensions ?? {}).length > 0
            ? ` / ${formatMetricDimensions(fact)}`
            : ""}
          {fact.delta !== null && fact.delta !== undefined
            ? ` (${formatMetricDelta(fact)})`
            : ""}
          {fact.freshness_label ? ` / ${fact.freshness_label}` : ""}
        </span>
      ))}
    </div>
  );
}

function metricFactKey(fact: MetricFact, index: number) {
  const dimensions = Object.entries(fact.dimensions ?? {})
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, value]) => `${key}=${value}`)
    .join("|");
  return [
    fact.source_connector,
    fact.period,
    fact.name,
    fact.evidence_id,
    dimensions,
    index
  ].join("::");
}

function metricFactLabel(fact: MetricFact) {
  return fact.metric_label || "Metryka bez etykiety";
}

function formatMetricFactValue(fact: MetricFact) {
  const suffix = fact.unit ? ` ${fact.unit}` : "";
  return `${fact.value}${suffix}`;
}

function formatMetricDelta(fact: MetricFact) {
  if (fact.delta === null || fact.delta === undefined || !fact.trend || fact.trend === "unknown") {
    return "zmiana: brak";
  }
  const sign = fact.delta > 0 ? "+" : "";
  const percent =
    fact.delta_percent === null || fact.delta_percent === undefined
      ? ""
      : ` (${sign}${fact.delta_percent.toFixed(1)}%)`;
  return `zmiana: ${sign}${fact.delta}${percent}`;
}

function formatMetricDimensions(fact: MetricFact) {
  return Object.entries(fact.dimensions ?? {})
    .map(([key, value]) => {
      const keyLabel = fact.dimension_labels[key] || "Wymiar bez etykiety";
      const valueLabel = fact.dimension_value_labels[key] || "wartość do sprawdzenia";
      return `${keyLabel}: ${valueLabel}`;
    })
    .join(", ");
}
