/** Browser guard for an exact current-material review decision. */

export function materialReviewApprovalAllowed(
  outcome: string,
  reviewedFullMaterial: boolean,
  materialUrl: string | null
): boolean {
  return outcome !== "approved_for_prepare" || (materialUrl !== null && reviewedFullMaterial);
}

export function materialReviewCheckedItems(reviewedFullMaterial: boolean): string[] {
  return reviewedFullMaterial ? ["reviewed_full_material"] : [];
}

export function materialReviewPageUrl(preview: unknown): string | null {
  if (typeof preview !== "object" || preview === null || !("public_url" in preview)) return null;
  if (typeof preview.public_url !== "string") return null;
  const value = preview.public_url;
  if ([...value].some((character) => {
    const code = character.charCodeAt(0);
    return code <= 0x20 || code === 0x7f || /[<>"'`()[\]{}|\\^]/.test(character);
  })) return null;
  const match = /^https:\/\/([^/]+)(\/.*)$/i.exec(value);
  const authority = match?.[1];
  const rawPath = match?.[2]?.split(/[?#]/, 1)[0] ?? "";
  const finalPathSegment = rawPath.split("/").at(-1) ?? "";
  const paramSeparator = finalPathSegment.indexOf(";");
  if (!authority || (paramSeparator >= 0 && paramSeparator < finalPathSegment.length - 1)) {
    return null;
  }
  try {
    const url = new URL(value);
    return url.protocol === "https:" &&
      ["www.ekologus.pl", "ekologus.pl", "sklep.ekologus.pl"].includes(url.hostname) &&
      authority.toLowerCase() === url.hostname &&
      !url.username && !url.password && !url.search && !url.hash
      ? value
      : null;
  } catch {
    return null;
  }
}
