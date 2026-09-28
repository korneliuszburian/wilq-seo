import { describe, expect, it } from "vitest";

import {
  ContentIntakeAskRequestSchema,
  ContentIntakeQueueItemSchema,
  type ContentIntakeQueueItem
} from "./content_intake";

const DIGEST = "c47b408cbdf7d42231f3a277e6294e1ea74266dc18718c4b8a14173ec248171b"; // pragma: allowlist secret (fixture digest; not a credential)

function blockedItem(): ContentIntakeQueueItem {
  return ContentIntakeQueueItemSchema.parse({
    schema_version: "wilq_content_intake_v1",
    queue_id: "content_intake_c47b408cbdf7d42231f3a277",
    request_id: "11111111-1111-4111-8111-111111111111",
    input_digest: DIGEST,
    actor_id: "local_operator",
    actor_trust_level: "local_unverified",
    status: "blocked",
    ask: "Odśwież stronę o operacie wodnoprawnym",
    provenance: [
      {
        field: "ask",
        provenance: "user_input",
        detail: "Dosłowna prośba operatora.",
        evidence_ids: []
      }
    ],
    candidate_work_item_ids: [],
    candidate_paths: [],
    candidate_public_urls: [],
    blockers: [
      {
        code: "intake_target_missing",
        owner: "WILQ content workflow",
        detail: "Brak pasującego elementu katalogu."
      }
    ],
    safe_next_step: "Wskaż istniejący adres albo work item z katalogu WILQ.",
    generation_allowed: false,
    created_at: "2026-09-26T22:17:47.362054Z"
  });
}

describe("content intake contract", () => {
  it("accepts a typed blocked queue item with aligned candidates", () => {
    const item = blockedItem();
    expect(item.status).toBe("blocked");
    expect(item.generation_allowed).toBe(false);
  });

  it("rejects a blocked item without a typed blocker", () => {
    const payload = { ...blockedItem(), blockers: [] };
    expect(() => ContentIntakeQueueItemSchema.parse(payload)).toThrow();
  });

  it("rejects misaligned candidate triplets", () => {
    const payload = {
      ...blockedItem(),
      status: "queued",
      blockers: [],
      candidate_work_item_ids: ["wi_1"],
      candidate_paths: ["/a", "/b"],
      candidate_public_urls: ["https://example.test/a"]
    };
    expect(() => ContentIntakeQueueItemSchema.parse(payload)).toThrow();
  });

  it("orders candidate paths by code point, not UTF-16 code unit", () => {
    const payload = {
      ...blockedItem(),
      status: "queued",
      blockers: [],
      candidate_work_item_ids: ["wi_1", "wi_2"],
      candidate_paths: ["\u{10000}", "\uFFFD"],
      candidate_public_urls: ["https://example.test/a", "https://example.test/b"]
    };
    expect(() => ContentIntakeQueueItemSchema.parse(payload)).toThrow();
  });

  it("accepts a persisted item whose request_id is any RFC 4122 shape", () => {
    const item = ContentIntakeQueueItemSchema.parse({
      ...blockedItem(),
      request_id: "11111111-1111-0111-8111-111111111111"
    });
    expect(item.request_id).toBe("11111111-1111-0111-8111-111111111111");
  });

  it("bounds ask by Unicode code points, matching the Python contract", () => {
    const long = ContentIntakeQueueItemSchema.parse({
      ...blockedItem(),
      status: "queued",
      blockers: [],
      ask: "\u{1F600}".repeat(1001)
    });
    expect(Array.from(long.ask)).toHaveLength(1001);
    expect(() =>
      ContentIntakeAskRequestSchema.parse({
        request_id: "11111111-1111-4111-8111-111111111111",
        ask: "\u{1F600}\u{1F600}"
      })
    ).toThrow();
  });
});
