export const FIELD_LABELS: Record<string, string> = {
  channel: "Kanał",
  published_at: "Data publikacji",
  topic: "Temat",
  service: "Usługa",
  claim: "Claim",
  cta: "CTA",
  format: "Format",
  post_url_or_id: "URL albo ID posta",
  source_evidence_id: "Dowód źródłowy"
};

export type SocialHistoryStatusFormatters = {
  access: (status: string) => string;
  inventory: (status: string) => string;
  metadataSource: (status: string) => string;
};
