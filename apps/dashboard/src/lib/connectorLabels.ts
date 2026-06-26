import type { ConnectorStatus } from "./api";

export function connectorLabelsFromStatuses(
  connectorIds: string[],
  connectorStatuses: ConnectorStatus[]
) {
  const labelsById = new Map(connectorStatuses.map((connector) => [connector.id, connector.label]));
  return Array.from(
    new Set(
      connectorIds.map((connectorId) => labelsById.get(connectorId) ?? "źródło danych bez etykiety w API")
    )
  );
}
