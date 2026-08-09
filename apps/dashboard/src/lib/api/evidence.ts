import { EvidenceSchema, type Evidence } from "@wilq/shared-schemas";
import { z } from "zod";

import { apiGet } from "./common";

export function getEvidence(): Promise<Evidence[]> {
  return apiGet("/api/evidence", z.array(EvidenceSchema));
}

export function getEvidenceById(evidenceId: string): Promise<Evidence> {
  return apiGet(`/api/evidence/${encodeURIComponent(evidenceId)}`, EvidenceSchema);
}
