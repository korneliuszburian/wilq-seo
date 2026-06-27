export function formatContentMetricValue(
  metricName: string,
  value: string | number | boolean | null
) {
  if (typeof value === "boolean") return value ? "tak" : "nie";
  if (value === null) return "brak";
  const numericValue = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numericValue)) return value;
  if (metricName === "ctr" || metricName === "engagement_rate") {
    return `${formatNumber(numericValue * 100, 2)}%`;
  }
  if (metricName === "average_position") {
    return formatNumber(numericValue, 2);
  }
  if (Number.isInteger(numericValue)) return numericValue.toLocaleString("pl-PL");
  return formatNumber(numericValue, 2);
}

function formatNumber(value: number, fractionDigits: number) {
  return value.toLocaleString("pl-PL", {
    maximumFractionDigits: fractionDigits,
    minimumFractionDigits: 0
  });
}
