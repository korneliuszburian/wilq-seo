import type { ContentWorkflowSnapshot } from "./contentWorkflowRuntime";
import type { WordPressAuthoringProfile } from "../lib/api";

export type WordPressAuthoringDevContentObject = WordPressAuthoringProfile["dev_content"]["items"][number];

export function selectDevContentObject(
  profile: WordPressAuthoringProfile | null,
  item: ContentWorkflowSnapshot["preflight"]["item"],
  selectedLink?: string | null
): WordPressAuthoringDevContentObject | null {
  const items = profile?.dev_content.items ?? [];
  if (!items.length) return null;
  if (selectedLink) {
    const explicitMatch = items.find((item) => normalizedPath(item.link) === normalizedPath(selectedLink));
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
  const exactMatch = items.find((item) => candidatePaths.includes(normalizedPath(item.link)));
  if (exactMatch) return exactMatch;
  if (candidatePaths.includes("/")) {
    const home = items.find((item) => normalizedPath(item.link) === "/" && item.section_count > 0);
    if (home) return home;
  }
  // Never attach unrelated dev content to a public work item. A missing exact
  // path is a typed absence of target, not permission to display another
  // object's ACF sections as if they belonged to this workflow.
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
