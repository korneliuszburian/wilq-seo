import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LabelChipRow, PlainChipRow } from "./OperatorPrimitives";

describe("LabelChipRow", () => {
  it("separates adjacent labelled chips in readable text", () => {
    render(
      <LabelChipRow
        chips={[
          { label: "Źródło", value: "Localo" },
          { label: "Typ", value: "przejrzyj widoczność" },
          { label: "Priorytet", value: "wysoki priorytet" }
        ]}
      />
    );

    const text = screen.getByText("Źródło: Localo").parentElement?.parentElement
      ?.textContent;

    expect(text).toContain("Źródło: Localo Typ: przejrzyj widoczność");
    expect(text).not.toContain("LocaloTyp");
    expect(text).not.toContain("widocznośćPriorytet");
  });

  it("omits empty chips without leaving broken separators", () => {
    const { container } = render(
      <LabelChipRow
        chips={[
          { label: "Typ", value: "decyzja" },
          { label: "Źródło", value: "" },
          { label: "Priorytet", value: "pilne" }
        ]}
      />
    );

    expect(container.textContent).toBe("Typ: decyzja Priorytet: pilne");
  });
});

describe("PlainChipRow", () => {
  it("renders status chips without hidden punctuation separators", () => {
    const { container } = render(
      <PlainChipRow
        values={[
          "dostęp skonfigurowany",
          null,
          "dane świeże",
          "ostatni odczyt: zakończony"
        ]}
      />
    );

    expect(container.textContent).toBe(
      "dostęp skonfigurowany dane świeże ostatni odczyt: zakończony"
    );
    expect(container.querySelector(".sr-only")).toBeNull();
    expect(container.textContent).not.toContain(";");
  });
});
