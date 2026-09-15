import { describe, expect, it } from "vitest";

import {
  ContentCurrentDispositionApprovalCurrentResponseSchema,
  ContentCurrentDispositionApprovalRequestSchema,
  ContentCurrentDispositionApprovalResponseSchema
} from "./content_current_disposition";

const request = {
  expected_snapshot_digest: "a".repeat(64),
  expected_action_payload_digest: "b".repeat(64),
  expected_preview_audit_id: "preview_current",
  confirm: true,
  notes: "Potwierdzam lokalny kierunek; WILQ nie zmienia WordPressa."
};

describe("current disposition approval contract", () => {
  it("accepts only the exact approval request", () => {
    expect(ContentCurrentDispositionApprovalRequestSchema.parse(request)).toEqual(request);
    expect(() =>
      ContentCurrentDispositionApprovalRequestSchema.parse({ ...request, confirm: false })
    ).toThrow();
    expect(() =>
      ContentCurrentDispositionApprovalRequestSchema.parse({ ...request, unexpected: true })
    ).toThrow();
  });

  it("does not accept a current response without a receipt", () => {
    expect(() =>
      ContentCurrentDispositionApprovalCurrentResponseSchema.parse({
        status: "current",
        projection: {
          status: "preview_ready",
          action: null,
          receipt: null,
          blockers: [],
          safe_next_step: "Odśwież preview."
        },
        action: null,
        receipt: null,
        blockers: [],
        safe_next_step: "Odśwież preview.",
        audit_ids: {},
        external_write_attempted: false
      })
    ).toThrow();
  });

  it("discriminates a typed blocked response", () => {
    const blocked = ContentCurrentDispositionApprovalResponseSchema.parse({
      status: "blocked",
      projection: {
        status: "blocked",
        action: null,
        receipt: null,
        blockers: [
          {
            seam: "receipt",
            reason: "current_disposition_preview_mismatch",
            evidence_ids: [],
            next_step: "Odśwież preview."
          }
        ],
        safe_next_step: "Odśwież preview."
      },
      action: null,
      receipt: null,
      blockers: [
        {
          seam: "receipt",
          reason: "current_disposition_preview_mismatch",
          evidence_ids: [],
          next_step: "Odśwież preview."
        }
      ],
      safe_next_step: "Odśwież preview.",
      audit_ids: {},
      external_write_attempted: false
    });

    expect(blocked.status).toBe("blocked");
  });
});
