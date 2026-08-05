import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DevTargetLivePreview } from "./ContentDocumentWorkspaceCanvas";

describe("DevTargetLivePreview", () => {
  it("keeps the live dev page as a clearly labelled reference", () => {
    render(<DevTargetLivePreview url="https://ekologus.dev.proudsite.pl/" />);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Otwórz podgląd strony dev" }));

    expect(
      screen.getByText(/Nie pokazuje niezapisanych zmian z mapowania/)
    ).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Otwórz stronę dev w nowej karcie" }))
      .toHaveAttribute("href", "https://ekologus.dev.proudsite.pl/");
    expect(screen.getByTitle("Referencyjny podgląd strony dev"))
      .toHaveAttribute("src", "https://ekologus.dev.proudsite.pl/");
    expect(screen.getByTitle("Referencyjny podgląd strony dev"))
      .toHaveAttribute("sandbox", "allow-same-origin allow-scripts");

    fireEvent.click(screen.getByRole("button", { name: "Zamknij podgląd strony dev" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
