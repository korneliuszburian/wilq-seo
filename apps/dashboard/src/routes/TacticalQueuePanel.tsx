import type { TacticalQueueResponse } from "../lib/api";

type TacticalQueueItem = TacticalQueueResponse["items"][number];

export function tacticalContextPairs(
  item: TacticalQueueItem
): Array<{ key: string; label: string; valueLabel: string }> {
  const priorityKeys = [
    "query",
    "page",
    "landing_page",
    "source_medium",
    "campaign_name",
    "issue_type",
    "affected_attribute",
    "country",
    "reporting_context",
    "wordpress_match",
    "wordpress_match_confidence",
    "gsc_page_query_count"
  ];
  return priorityKeys
    .filter((key) => item.dimensions[key])
    .slice(0, 6)
    .map((key) => ({
      key,
      label: item.dimension_labels[key] || "kontekst",
      valueLabel: item.dimension_value_labels[key] || "wartość do sprawdzenia"
    }));
}
