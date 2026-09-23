import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as api from "../../lib/api";
import { CurrentMaterialReviewEntry } from "./CurrentMaterialReviewEntry";

function renderEntry() {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <CurrentMaterialReviewEntry workItemId="content_work_item_bdo" />
    </QueryClientProvider>
  );
}

describe("current material review entry", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("prepares one local action and links to its exact review", async () => {
    const prepare = vi.spyOn(api, "prepareContentMaterialReviewAction").mockResolvedValue({
      response_type: "content_material_review_action_v2",
      status: "preview_ready",
      action_id: "act_content_material_review_exact",
      external_write_attempted: false,
      generation_allowed: false
    });
    renderEntry();
    fireEvent.click(screen.getByRole("button", { name: "Przygotuj przegląd materiału" }));
    await waitFor(() => expect(prepare).toHaveBeenCalledWith("content_work_item_bdo"));
    expect(await screen.findByRole("link", { name: "Otwórz dokładny przegląd i decyzję" }))
      .toHaveAttribute("href", "/actions/act_content_material_review_exact");
  });

  it("shows the typed blocker owner and next step without an approval link", async () => {
    vi.spyOn(api, "prepareContentMaterialReviewAction").mockResolvedValue({
      response_type: "content_material_review_action_v2",
      status: "blocked",
      blocker_code: "material_review_source_stale",
      blocker_owner: "WILQ WordPress connector",
      safe_next_step: "Odśwież odczyt WordPress.",
      external_write_attempted: false,
      generation_allowed: false
    });
    renderEntry();
    fireEvent.click(screen.getByRole("button", { name: "Przygotuj przegląd materiału" }));
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Odśwież odczyt WordPress. Odpowiedzialny: WILQ WordPress connector."
    );
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});
