import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TraceLine } from "./TraceLine";

describe("TraceLine", () => {
  it("explains missing values as a decision limit", () => {
    render(<TraceLine label="Dowody" values={[]} />);

    expect(
      screen.getByText(
        "Dowody: WILQ nie podał pozycji; sprawdź źródło danych przed decyzją"
      )
    ).toBeInTheDocument();
  });
});
