import { describe, expect, it } from "vitest";

import { ContentDraftRevisionSchema } from "./contentWorkflow";

describe("ContentDraftRevision lineage contract", () => {
  it("accepts the fully populated v2 payload emitted by the API", () => {
    const revision = ContentDraftRevisionSchema.parse({
      schema_version: "wilq_content_draft_revision_v2",
      revision_id: "content_revision_lineage",
      work_item_id: "content_work_item_lineage",
      revision_number: 1,
      base_revision_id: null,
      content_digest: "a".repeat(64),
      draft_package_id: "draft_package_lineage",
      draft_package_digest: "b".repeat(64),
      planning_digest: "c".repeat(64),
      planning_input_digest: "d".repeat(64),
      service_card_id: "ekologus_service_lineage",
      service_digest: "e".repeat(64),
      inventory_digest: "f".repeat(64),
      source_material_ids: ["ekologus_material_approved"],
      knowledge_card_ids: ["ekologus_card_lineage"],
      final_canonical_url: "https://www.ekologus.pl/lineage",
      title: "Treść oparta na źródłach",
      page_assets: {
        wordpress_title: "Treść oparta na źródłach",
        meta_title: "Treść oparta na źródłach — Ekologus",
        meta_description: "Opis oparty na zatwierdzonych faktach.",
        h1: "Treść oparta na źródłach",
        lead: "Lead oparty na zatwierdzonych faktach."
      },
      sections: [{
        section_id: "section_lineage",
        heading: "Najważniejsze fakty",
        body_markdown: "Treść oparta na dowodzie.",
        query_terms: ["fakty"],
        evidence_ids: ["ev_lineage"],
        claim_ids: [],
        source_material_ids: ["ekologus_material_approved"],
        knowledge_card_ids: ["ekologus_card_lineage"]
      }],
      faq: [],
      cta_blocks: [],
      internal_links: [],
      proposal_metadata: null,
      publish_ready: false,
      created_by: "codex",
      created_at: "2026-07-18T07:00:00Z"
    });

    expect(revision.source_material_ids).toEqual(["ekologus_material_approved"]);
    expect(revision.sections[0]?.knowledge_card_ids).toEqual(["ekologus_card_lineage"]);
  });
});
