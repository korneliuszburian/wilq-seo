import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ContentKnowledgeReadinessNotice } from "./ContentKnowledgeReadinessNotice";

describe("ContentKnowledgeReadinessNotice", () => {
  afterEach(() => cleanup());

  it("links a blocked content workflow to the existing knowledge review queue", () => {
    render(
      <ContentKnowledgeReadinessNotice
        query={{
          data: {
            status: "excerpt_review_required",
            status_label: "wymaga review",
            total_count: 2,
            imported_count: 1,
            import_pending_count: 0,
            excerpt_review_required_count: 1,
            ready_for_generation: false,
            next_step: "Zatwierdź excerpty i ich lineage.",
            pending_materials: [],
            excerpt_review_materials: [],
            imported_materials: []
          },
          isError: false,
          isLoading: false
        } as never}
        materials={{ data: [], isError: false } as never}
      />
    );

    expect(screen.getByRole("link", { name: "Otwórz kolejkę review wiedzy" })).toHaveAttribute(
      "href",
      "/knowledge#knowledge-review-queue"
    );
  });
});
