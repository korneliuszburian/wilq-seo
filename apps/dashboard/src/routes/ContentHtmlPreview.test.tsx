import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ContentHtmlPreview } from "./ContentHtmlPreview";

describe("ContentHtmlPreview", () => {
  afterEach(cleanup);

  it("renders the isolated preview without enabling scripts, forms, or external sources", () => {
    render(<ContentHtmlPreview contentHtml="<p>Treść do sprawdzenia</p>" title="Podgląd treści" />);

    const preview = screen.getByTitle("Podgląd treści");
    expect(preview).toHaveAttribute("sandbox", "allow-same-origin");
    expect(preview).toHaveAttribute("referrerpolicy", "no-referrer");
    expect(preview.getAttribute("srcdoc")).toContain("default-src 'none'; style-src 'unsafe-inline'; img-src data:");
  });

  it("grows to the loaded document instead of trapping the article in an inner scrollbar", () => {
    render(<ContentHtmlPreview contentHtml="<p>Treść do sprawdzenia</p>" title="Podgląd treści" />);

    const preview = screen.getByTitle("Podgląd treści");
    Object.defineProperty(preview, "contentDocument", {
      configurable: true,
      value: {
        body: { scrollHeight: 620, offsetHeight: 600 },
        documentElement: { scrollHeight: 610, offsetHeight: 590 }
      }
    });
    fireEvent.load(preview);

    expect(preview).toHaveStyle({ height: "622px" });
  });
});
