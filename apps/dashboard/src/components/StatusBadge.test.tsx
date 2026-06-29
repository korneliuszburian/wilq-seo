import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusBadge } from "./StatusBadge";

describe("StatusBadge", () => {
  it("uses API-owned label text when present", () => {
    render(<StatusBadge value="validated_prepare_only" label="sprawdzone bez zapisu zmian" />);

    expect(screen.getByText("sprawdzone bez zapisu zmian")).toBeInTheDocument();
    expect(screen.queryByText("validated_prepare_only")).not.toBeInTheDocument();
  });

  it("does not expose raw status values when the label is missing", () => {
    render(<StatusBadge value="validated_prepare_only" />);

    expect(screen.getByText("brak etykiety z WILQ")).toBeInTheDocument();
    expect(screen.queryByText("validated_prepare_only")).not.toBeInTheDocument();
  });
});
