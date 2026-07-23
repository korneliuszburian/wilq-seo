import { describe, expect, it } from "vitest";

import { normalizedPath, selectDevContentObject } from "./contentWorkflowTarget";

const profile = {
  dev_content: {
    items: [
      { link: "https://ekologus.dev.proudsite.pl/", title: "Strona główna", section_count: 9 },
      { link: "https://ekologus.dev.proudsite.pl/kontakt/", title: "Kontakt", section_count: 3 }
    ]
  }
} as never;

const item = {
  preview_url: "https://ekologus.dev.proudsite.pl/",
  source_public_url: "https://www.ekologus.pl/",
  final_canonical_url: "https://www.ekologus.pl/",
  intended_final_url: "https://www.ekologus.pl/"
} as never;

describe("content workflow dev target", () => {
  it("normalizes public and dev URLs to the same path", () => {
    expect(normalizedPath("https://ekologus.dev.proudsite.pl/kontakt/?preview=1")).toBe("/kontakt");
  });

  it("honours an explicit dev target before inferred matching", () => {
    expect(selectDevContentObject(profile, item, "https://ekologus.dev.proudsite.pl/kontakt/")?.title).toBe("Kontakt");
  });

  it("does not attach unrelated dev content when the public path has no exact target", () => {
    expect(selectDevContentObject(profile, {
      preview_url: "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
      source_public_url: "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
      final_canonical_url: "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
      intended_final_url: "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
    } as never)).toBeNull();
  });
});
