import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as api from "../../lib/api";
import { CurrentResearchPacketEntry } from "./CurrentResearchPacketEntry";

function renderEntry() {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { mutations: { retry: false } } })}>
      <CurrentResearchPacketEntry workItemId="wi_exact" />
    </QueryClientProvider>
  );
}

describe("current research packet entry", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("links the exact prepared action without claiming generation authority", async () => {
    const prepare = vi.spyOn(api, "prepareContentResearchPacketV2Action").mockResolvedValue({
      response_type: "research_packet_v2_action",
      status: "preview_ready",
      action_id: "act_content_research_packet_v2_exact",
      external_write_attempted: false,
      generation_allowed: false
    });
    renderEntry();
    fireEvent.click(screen.getByRole("button", { name: "Przygotuj przegląd pakietu" }));
    await waitFor(() => expect(prepare).toHaveBeenCalledWith("wi_exact"));
    expect(await screen.findByRole("link", { name: "Otwórz cały pakiet i decyzję" }))
      .toHaveAttribute("href", "/actions/act_content_research_packet_v2_exact");
  });

  it("shows the current typed blocker and owner", async () => {
    vi.spyOn(api, "prepareContentResearchPacketV2Action").mockResolvedValue({
      response_type: "research_packet_v2_action",
      status: "blocked",
      blocker_code: "missing_approved_keep_receipt",
      blocker_owner: "Wilku",
      evidence_ids: ["ev_current"],
      safe_next_step: "Zatwierdź kierunek KEEP.",
      external_write_attempted: false,
      generation_allowed: false
    });
    renderEntry();
    fireEvent.click(screen.getByRole("button", { name: "Przygotuj przegląd pakietu" }));
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Zatwierdź kierunek KEEP. Odpowiedzialny: Wilku."
    );
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});
