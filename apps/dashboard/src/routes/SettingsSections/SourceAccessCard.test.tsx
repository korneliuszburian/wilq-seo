import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ConnectorStatus } from "../../lib/api";
import { SourceAccessCard } from "./SourceAccessCard";

function connector(overrides: {
  refreshAllowed?: boolean;
  freshnessState?: string;
} = {}): ConnectorStatus {
  return {
    id: "google_search_console",
    label: "Google Search Console",
    status: "configured",
    status_label: "Skonfigurowane",
    configured: true,
    active_for_daily_work: true,
    product_scope_label: "Widoczność w wyszukiwarce",
    missing_credentials: [],
    freshness: { state: overrides.freshnessState ?? "unknown" },
    refresh_state: {
      state_label: "Nie potwierdzono odczytu",
      safe_next_step: "Uruchom bezpieczny odczyt, aby potwierdzić stan źródła.",
      refresh_allowed: overrides.refreshAllowed ?? true
    }
  } as unknown as ConnectorStatus;
}

function renderCard(onRefresh = vi.fn()) {
  render(
    <SourceAccessCard
      connector={connector()}
      onRefresh={onRefresh}
      refreshing={false}
      refreshError={null}
      refreshResult={null}
    />
  );
  return onRefresh;
}

describe("SourceAccessCard", () => {
  afterEach(() => cleanup());

  it("offers the first read for an unknown freshness the API allows", () => {
    const onRefresh = renderCard();
    const button = screen.getByRole("button", { name: "Odśwież dane" });
    fireEvent.click(button);
    expect(onRefresh).toHaveBeenCalledTimes(1);
  });

  it("does not offer a read the API forbids", () => {
    render(
      <SourceAccessCard
        connector={connector({ refreshAllowed: false })}
        onRefresh={vi.fn()}
        refreshing={false}
        refreshError={null}
        refreshResult={null}
      />
    );
    expect(screen.queryByRole("button", { name: "Odśwież dane" })).not.toBeInTheDocument();
  });

  it("does not call a configured source active without a confirmed read", () => {
    render(
      <SourceAccessCard
        connector={connector({ freshnessState: "unknown" })}
        onRefresh={vi.fn()}
        refreshing={false}
        refreshError={null}
        refreshResult={null}
      />
    );
    expect(screen.getByText("Niepotwierdzone")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Dostęp jest skonfigurowany, ale WILQ nie potwierdził jeszcze udanego odczytu danych."
      )
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Dane dostępne i aktualizowane przez WILQ.")
    ).not.toBeInTheDocument();
  });
});
