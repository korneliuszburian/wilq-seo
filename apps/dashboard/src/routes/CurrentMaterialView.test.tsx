import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { CurrentMaterialTextResponse } from "@wilq/shared-schemas";

import { CurrentMaterialView } from "./CurrentMaterialView";

describe("CurrentMaterialView", () => {
  afterEach(cleanup);

  it("shows the full current source and no marketer approval controls", () => {
    const material = {
      response_type: "current_material_text_v1",
      status: "exact",
      is_generated: false,
      action_id: "act_exact",
      preview_id: "preview_exact",
      preview_digest: "a".repeat(64),
      source_url: "https://www.ekologus.pl/pozwolenie-ippc/",
      title: "Pozwolenie IPPC",
      text: "Pełny obecny tekst o IPPC.",
      body_digest: "b".repeat(64),
      read_at: "2026-09-24T05:00:00Z",
      evidence_ids: ["ev_exact"]
    } satisfies CurrentMaterialTextResponse;
    render(<CurrentMaterialView material={material} loading={false} unavailable={false} />);
    expect(screen.getByRole("heading", { name: "Aktualna treść strony: Pozwolenie IPPC" }))
      .toBeInTheDocument();
    expect(screen.getByText("Pełny obecny tekst o IPPC.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: material.source_url })).toHaveAttribute(
      "href", material.source_url
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
