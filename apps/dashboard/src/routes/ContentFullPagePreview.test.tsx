import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { ContentDraftRevision } from "../lib/api";
import { ContentFullPagePreview } from "./ContentFullPagePreview";

describe("ContentFullPagePreview", () => {
  afterEach(() => cleanup());

  it("renders the nullable editor-owned byline with the saved revision", () => {
    const revision = {
      revision_id: "revision_bdo",
      content_digest: "a".repeat(64),
      page_assets: {
        wordpress_title: "BDO dla firm",
        meta_title: "BDO dla firm — Ekologus",
        meta_description: "Opis strony.",
        h1: "BDO dla firm",
        lead: "Sprawdź obowiązki.",
        byline: "Ekspert Ekologus"
      },
      sections: [{
        section_id: "scope",
        heading: "Zakres",
        body_markdown: "Treść sekcji.",
        content_html: null
      }],
      faq: [],
      cta_blocks: [],
      internal_links: []
    } as unknown as ContentDraftRevision;

    render(<ContentFullPagePreview revision={revision} />);

    expect(screen.getByTestId("content-byline")).toHaveTextContent(
      "Autor: Ekspert Ekologus"
    );
  });
});
