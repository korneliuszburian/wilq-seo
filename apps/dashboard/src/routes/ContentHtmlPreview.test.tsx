import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ContentHtmlPreview } from "./ContentHtmlPreview";

describe("ContentHtmlPreview", () => {
  it("renders the isolated preview without enabling scripts, forms, or external sources", () => {
    render(<ContentHtmlPreview contentHtml="<p>Treść do sprawdzenia</p>" title="Podgląd treści" />);

    const preview = screen.getByTitle("Podgląd treści");
    expect(preview).toHaveAttribute("sandbox", "allow-same-origin");
    expect(preview).toHaveAttribute("referrerpolicy", "no-referrer");
    expect(preview.getAttribute("srcdoc")).toContain("default-src 'none'; style-src 'unsafe-inline'; img-src data:");
  });
});
