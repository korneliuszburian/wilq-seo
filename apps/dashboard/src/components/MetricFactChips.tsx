import type { MetricFact } from "../lib/api";

export function MetricFactChips({ facts }: { facts: MetricFact[] }) {
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {facts.map((fact, index) => (
        <span
          key={metricFactKey(fact, index)}
          className="rounded border border-line bg-slate-50 px-2 py-1 text-xs text-slate-700"
        >
          {metricFactLabel(fact.name)}: {formatMetricFactValue(fact)}
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

function metricFactLabel(metricName: string) {
  const labels: Record<string, string> = {
    active_products: "Produkty aktywne",
    active_users: "Aktywni użytkownicy",
    ahrefs_content_gap_count: "Luki treści Ahrefs",
    ahrefs_rank: "Ahrefs Rank",
    ahrefs_referring_domain_gap_count: "Luki domen linkujących",
    average_position: "Pozycja",
    clicks: "Kliknięcia",
    content_object_count: "Obiekty treści",
    ctr: "CTR",
    disapproved_products: "Produkty odrzucone",
    domain_rating: "Domain Rating",
    engagement_rate: "Zaangażowanie",
    event_count: "Zdarzenia",
    impressions: "Wyświetlenia",
    issue_product_count: "Zgłoszenia problemów",
    localo_active_place_count: "Miejsca aktywne",
    localo_avg_latest_grid_position: "Średnia pozycja lokalna",
    localo_avg_rating: "Średnia ocena",
    localo_avg_visibility_change: "Zmiana widoczności lokalnej",
    localo_avg_visibility_current: "Widoczność lokalna",
    localo_competitor_change_count: "Zmiany konkurencji",
    localo_competitor_count: "Konkurenci lokalni",
    localo_favorite_competitor_count: "Wyróżnieni konkurenci",
    localo_gbp_actions_total: "Akcje w profilu firmy",
    localo_gbp_impressions_total: "Wyświetlenia profilu firmy",
    localo_gbp_metric_point_count: "Punkty danych profilu firmy",
    localo_keyword_volume_count: "Frazy z wolumenem",
    localo_latest_grid_position_count: "Pomiary pozycji lokalnej",
    localo_place_detail_count: "Miejsca ze szczegółami",
    localo_review_reply_rate: "Odpowiedzi na opinie",
    localo_reviews_count: "Opinie",
    localo_reviews_removed_count: "Usunięte opinie",
    localo_reviews_replied_count: "Opinie z odpowiedzią",
    localo_snapshot_reviews_count: "Opinie w odczycie",
    localo_total_keyword_volume: "Łączny wolumen fraz",
    localo_tracked_keyword_count: "Monitorowane frazy",
    localo_visibility_score_count: "Pomiary widoczności",
    pages_total: "Strony",
    posts_total: "Wpisy",
    screen_page_views: "Wyświetlenia stron",
    sessions: "Sesje",
    total_products: "Produkty w feedzie"
  };
  return labels[metricName] ?? "metryka WILQ";
}

function formatMetricFactValue(fact: MetricFact) {
  const suffix = fact.unit ? ` ${fact.unit}` : "";
  return `${fact.value}${suffix}`;
}

function formatMetricDelta(fact: MetricFact) {
  if (fact.delta === null || fact.delta === undefined || !fact.trend || fact.trend === "unknown") {
    return "delta: brak";
  }
  const sign = fact.delta > 0 ? "+" : "";
  const percent =
    fact.delta_percent === null || fact.delta_percent === undefined
      ? ""
      : ` (${sign}${fact.delta_percent.toFixed(1)}%)`;
  return `delta: ${sign}${fact.delta}${percent}`;
}

function formatMetricDimensions(fact: MetricFact) {
  return Object.entries(fact.dimensions ?? {})
    .map(([key, value]) => `${metricDimensionLabel(key)}=${metricDimensionValueLabel(value)}`)
    .join(", ");
}

function metricDimensionLabel(dimensionName: string) {
  const labels: Record<string, string> = {
    affected_attribute: "atrybut",
    campaign_name: "kampania",
    competitor_domain: "konkurent",
    contract: "obszar",
    country: "kraj",
    gap_type: "typ luki",
    issue_type: "problem",
    keyword: "fraza",
    landing_page: "landing",
    metric_bucket: "zakres",
    page: "strona",
    query: "zapytanie",
    scope: "zakres",
    source_medium: "źródło",
    source_url: "URL źródłowy",
    target_domain: "domena docelowa"
  };
  return labels[dimensionName] ?? "wymiar";
}

function metricDimensionValueLabel(value: string) {
  const labels: Record<string, string> = {
    active_places: "aktywne miejsca",
    competitor_visibility: "widoczność konkurencji",
    gbp_visibility: "profil firmy w Google",
    local_rankings: "lokalne pozycje",
    place_inventory: "spis miejsc",
    reviews: "opinie"
  };
  return labels[value] ?? value;
}
