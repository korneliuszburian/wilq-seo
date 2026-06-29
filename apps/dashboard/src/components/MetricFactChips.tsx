import type { MetricFact } from "../lib/api";

export function MetricFactChips({ facts }: { facts: MetricFact[] }) {
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {facts.map((fact, index) => {
        const dimensionChips = metricDimensionChips(fact);
        return (
          <span
            key={metricFactKey(fact, index)}
            className="inline-flex max-w-full flex-wrap items-center gap-1.5 rounded border border-line bg-slate-50 px-2 py-1 text-xs text-slate-700"
          >
            <span className="font-medium text-slate-800">
              {metricFactLabel(fact)}: {formatMetricFactValue(fact)}
            </span>
            {" "}
            {dimensionChips.map(({ label, value }) => (
              <span key={`${metricFactKey(fact, index)}-${label}`}>
                <span className="rounded bg-white px-1.5 py-0.5 text-slate-600">
                  {label}: {value}
                </span>{" "}
              </span>
            ))}
            {fact.delta !== null && fact.delta !== undefined ? (
              <span>
                <span className="rounded bg-white px-1.5 py-0.5 text-slate-600">
                  {formatMetricDelta(fact)}
                </span>{" "}
              </span>
            ) : null}
            {fact.freshness_label ? (
              <span>
                <span className="rounded bg-white px-1.5 py-0.5 text-slate-600">
                  Dane: {fact.freshness_label}
                </span>{" "}
              </span>
            ) : null}
          </span>
        );
      })}
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
  const value =
    typeof fact.value === "number"
      ? new Intl.NumberFormat("pl-PL", { maximumFractionDigits: 2 }).format(fact.value)
      : fact.value;
  return `${value}${suffix}`;
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

function metricDimensionChips(fact: MetricFact) {
  return Object.entries(fact.dimensions ?? {})
    .map(([key]) => {
      const keyLabel = fact.dimension_labels[key] || "Wymiar bez etykiety";
      const valueLabel = fact.dimension_value_labels[key] || "wartość do sprawdzenia";
      return { label: keyLabel, value: valueLabel };
    });
}
