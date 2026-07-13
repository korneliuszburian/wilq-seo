import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

describe("CustomSegmentsDiagnosticSurface", () => {
  it("custom segments route renders dedicated validation contract", async () => {
    const customSegmentsRouteContract = [
      "src/routes/CustomSegmentsDiagnosticSurface.tsx",
      "src/components/AdsCustomSegmentPanels.tsx"
    ]
      .map((sourcePath) => readFileSync(sourcePath, "utf8"))
      .join("\n");
    expect(customSegmentsRouteContract).toContain("Segmenty z haseł");
    expect(customSegmentsRouteContract).toContain("missing_read_contract_labels");
    expect(customSegmentsRouteContract).toContain("blocked_claim_labels");
    expect(customSegmentsRouteContract).toContain("validation_status_label");
    expect(customSegmentsRouteContract).toContain("candidate.evidence_summary_label");
    expect(customSegmentsRouteContract).toContain("row.evidence_summary_label");
    expect(customSegmentsRouteContract).toContain("contract.evidence_summary_label");
    expect(customSegmentsRouteContract).toContain("contract.action_summary_label");
    expect(customSegmentsRouteContract).toContain("candidate.preview_card");
    expect(customSegmentsRouteContract).not.toContain('empty="brak"');
    expect(customSegmentsRouteContract).not.toContain("candidate.payload_preview");
    expect(customSegmentsRouteContract).not.toContain("formatCustomSegmentsEvidenceCount");
    expect(customSegmentsRouteContract).not.toContain("formatCustomSegmentsActionCount");
  });
});
