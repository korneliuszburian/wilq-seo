import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ActionLifecycleStrip,
  BlockerPanel,
  CompactStatTile,
  DashboardToolbar,
  DenseQueueTable,
  ForbiddenClaimsStrip,
  PriorityBadge,
  RiskPill,
  SourceFreshnessStrip,
  StatusPill
} from "./DashboardMockupPrimitives";

afterEach(() => {
  cleanup();
});

describe("DashboardToolbar", () => {
  it("renders the mockup-style date and refresh controls", () => {
    const refresh = vi.fn();

    render(
      <DashboardToolbar
        title="Dzisiaj"
        description="Dzienne centrum operacyjne."
        dateLabel="Dzisiaj, 15 maj 2025"
        onRefresh={refresh}
      />
    );

    expect(screen.getByRole("heading", { name: "Dzisiaj" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Zakres daty" })).toHaveTextContent(
      "Dzisiaj, 15 maj 2025"
    );
    screen.getByRole("button", { name: "Odśwież" }).click();
    expect(refresh).toHaveBeenCalledTimes(1);
  });
});

describe("CompactStatTile", () => {
  it("keeps stat copy compact and formats Polish decimal values", () => {
    const { container } = render(
      <CompactStatTile value={12.345} label="gotowe do sprawdzenia" actionLabel="Zobacz gotowe" />
    );

    expect(screen.getByText("12,35")).toBeInTheDocument();
    expect(screen.getByText("gotowe do sprawdzenia")).toBeInTheDocument();
    expect(container.textContent).not.toContain("12.345");
  });
});

describe("SourceFreshnessStrip", () => {
  it("shows source labels and freshness states in one dense strip", () => {
    render(
      <SourceFreshnessStrip
        items={[
          { label: "Merchant", detail: "127h temu", tone: "amber" },
          { label: "GA4", detail: "130h temu", tone: "amber" },
          { label: "Ads", detail: "błąd odczytu", tone: "red" }
        ]}
      />
    );

    expect(screen.getByLabelText("Świeżość źródeł")).toHaveTextContent(
      "Merchant127h temuGA4130h temuAdsbłąd odczytu"
    );
  });
});

describe("BlockerPanel", () => {
  it("renders blocker rows as navigable decision items without exposing raw mechanics", () => {
    render(
      <BlockerPanel
        title="Blokady, których nie obchodź"
        badgeLabel="2 krytyczne"
        items={[
          {
            title: "Brak zapisu zmian bez audytu w Ads",
            description: "Zweryfikuj i włącz zapis zmian.",
            href: "/actions/action_ads"
          }
        ]}
      />
    );

    expect(screen.getByRole("heading", { name: "Blokady, których nie obchodź" })).toBeInTheDocument();
    expect(screen.getByText("2 krytyczne")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Brak zapisu zmian/ })).toHaveAttribute(
      "href",
      "/actions/action_ads"
    );
  });
});

describe("ForbiddenClaimsStrip", () => {
  it("keeps blocked marketing claims in a compact strip", () => {
    render(<ForbiddenClaimsStrip claims={["ROAS", "Odzyskany przychód"]} />);

    expect(screen.getByRole("heading", { name: "Nie wolno dziś twierdzić" })).toBeInTheDocument();
    expect(screen.getByText("ROAS")).toBeInTheDocument();
    expect(screen.getByText("Odzyskany przychód")).toBeInTheDocument();
  });
});

describe("DenseQueueTable", () => {
  it("renders dense queue rows with selected row emphasis and reusable cells", () => {
    const rows = [
      { id: "merchant", priority: "P1" as const, title: "Przegląd kanału produktowego" },
      { id: "ga4", priority: "P2" as const, title: "Sprawdź jakość ruchu" }
    ];

    const { container } = render(
      <DenseQueueTable
        title="Kolejka decyzji i akcji"
        rows={rows}
        getRowKey={(row) => row.id}
        selectedRowKey="merchant"
        columns={[
          {
            key: "priority",
            header: "Priorytet",
            render: (row) => <PriorityBadge value={row.priority} />
          },
          { key: "title", header: "Tytuł", render: (row) => row.title },
          {
            key: "status",
            header: "Status",
            render: () => <StatusPill label="Gotowe do sprawdzenia" tone="green" />
          }
        ]}
      />
    );

    expect(screen.getByRole("heading", { name: "Kolejka decyzji i akcji" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Priorytet" })).toBeInTheDocument();
    expect(screen.getByText("Przegląd kanału produktowego")).toBeInTheDocument();
    expect(container.querySelector("tr.bg-blue-50")).not.toBeNull();
  });

  it("shows an operator-readable empty state", () => {
    render(
      <DenseQueueTable
        title="Kolejka"
        rows={[]}
        getRowKey={(_, index) => `${index}`}
        columns={[{ key: "title", header: "Tytuł", render: () => null }]}
        emptyLabel="Brak decyzji na dziś"
      />
    );

    expect(screen.getByText("Brak decyzji na dziś")).toBeInTheDocument();
  });
});

describe("Badges and lifecycle", () => {
  it("renders priority, risk and lifecycle primitives with readable labels", () => {
    render(
      <>
        <PriorityBadge value="P1" />
        <RiskPill risk="medium" label="średnie" />
        <ActionLifecycleStrip
          steps={[
            { label: "validate", state: "done" },
            { label: "preview", state: "current" },
            { label: "audit", state: "waiting" }
          ]}
        />
      </>
    );

    expect(screen.getByText("P1")).toBeInTheDocument();
    expect(screen.getByText("średnie")).toBeInTheDocument();
    expect(screen.getByLabelText("Cykl bezpiecznej akcji")).toHaveTextContent(
      "validate2preview3audit"
    );
  });
});
