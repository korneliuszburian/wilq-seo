type DraftPackageSection = {
  purpose: string;
  draft_notes: string[];
};

export function sectionOverrideKey(value: string) {
  return value.trim().toLocaleLowerCase("pl-PL").replace(/\s+/g, " ");
}

export function defaultSectionBody(section: DraftPackageSection) {
  const notes = section.draft_notes.map((note) => `- ${note}`);
  return [section.purpose, ...notes].filter(Boolean).join("\n\n");
}

export function shortSectionTabLabel(value: string) {
  const cleaned = value.trim();
  if (!cleaned) return "Sekcja";
  const firstWord = cleaned.split(/\s+/)[0] ?? cleaned;
  if (cleaned.length <= 14) return cleaned;
  return firstWord.length >= 4 && firstWord.length <= 12 ? firstWord : `${cleaned.slice(0, 12)}...`;
}
