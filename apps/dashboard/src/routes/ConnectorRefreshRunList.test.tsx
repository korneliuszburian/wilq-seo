import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ConnectorRefreshRunList } from "./RegistryPanels";
import { connectorRefreshRun as run } from "./connectorRefreshRun.fixture";

describe("Connector refresh run evidence boundary", () => {
  it("summarizes evidence and metrics without raw IDs or payloads", () => {
    render(<ConnectorRefreshRunList runs={[run]} />);

    expect(screen.getByText("Dowody: 2 dowody źródłowe")).toBeInTheDocument();
    expect(screen.getByText("Metryki: 3 wartości")).toBeInTheDocument();
    expect(screen.queryByText("ev_connector_google_ads_status")).not.toBeInTheDocument();
    expect(screen.queryByText("ev_refresh_refresh_google_ads_test")).not.toBeInTheDocument();
    expect(screen.queryByText("vendor_read")).not.toBeInTheDocument();
    expect(screen.queryByText(/"clicks"/)).not.toBeInTheDocument();
  });
});
