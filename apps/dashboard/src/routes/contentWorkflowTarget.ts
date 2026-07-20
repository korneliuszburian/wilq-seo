import type { ContentWorkflowSnapshot } from "./contentWorkflowRuntime";
import type { WordPressAuthoringProfile } from "../lib/api";

export type WordPressAuthoringDevPage = WordPressAuthoringProfile["dev_content"]["pages"][number];

export function selectDevPage(
  profile: WordPressAuthoringProfile | null,
  item: ContentWorkflowSnapshot["preflight"]["item"],
  selectedLink?: string | null
): WordPressAuthoringDevPage | null {
  const pages = profile?.dev_content.pages ?? [];
  if (!pages.length) return null;
  if (selectedLink) {
    const explicitMatch = pages.find((page) => normalizedPath(page.link) === normalizedPath(selectedLink));
    if (explicitMatch) return explicitMatch;
  }
  const candidatePaths = [
    item.preview_url,
    item.source_public_url,
    item.final_canonical_url,
    item.intended_final_url
  ]
    .map((url) => normalizedPath(url ?? ""))
    .filter(Boolean);
  const exactMatch = pages.find((page) => candidatePaths.includes(normalizedPath(page.link)));
  if (exactMatch) return exactMatch;
  if (candidatePaths.includes("/")) {
    const home = pages.find((page) => normalizedPath(page.link) === "/" && page.section_count > 0);
    if (home) return home;
  }
  // Never attach an unrelated dev page to a public work item. A missing exact
  // path is a typed absence of target, not permission to display another
  // page's ACF sections as if they belonged to this workflow.
  return null;
}

export function normalizedPath(value: string) {
  if (!value) return "";
  try {
    const path = new URL(value).pathname.replace(/\/+$/, "");
    return path || "/";
  } catch {
    const path = value.split("?")[0]?.replace(/\/+$/, "") ?? "";
    return path || "/";
  }
}
