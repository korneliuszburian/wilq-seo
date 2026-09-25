import { describe, expect, it } from "vitest";

import {
  ResearchPacketV3ActionResponseSchema,
  ResearchPacketV3PreviewRecordSchema,
  ResearchPacketV3PreviewResponseSchema,
  ResearchPacketV3ReviewablePreviewRecordSchema
} from "./content_research_packet_v3_action";

const digest = (character: string) => character.repeat(64);

function record(pageIdentity = true) {
  return {
    schema_version: "wilq_research_packet_v3_preview_record_v1",
    preview_hash: digest("a"),
    work_item_id: "wi_exact",
    snapshot: {
      contract_version: "research_packet_v3_preview",
      status: "ready",
      work_item_id: "wi_exact",
      preview_id: "content_research_packet_v3_aaaaaaaaaaaaaaaaaaaaaaaa",
      preview_hash: digest("a"),
      source_pack_id: `source_pack_v3_${digest("b")}`,
      source_pack_hash: digest("b"),
      page_url: pageIdentity ? "https://www.ekologus.pl/exact/" : undefined,
      canonical_path: pageIdentity ? "/exact" : undefined,
      per_url_delivery_identity_action_id: pageIdentity
        ? "act_per_url_delivery_identity_exact"
        : undefined,
      identity_digest: digest("c"),
      material_meaning_digest: digest("d"),
      planning_input_digest: digest("e"),
      demand_evidence_status: "missing",
      selected_facts: [{
        source_fact_id: "fact_exact",
        fact_digest: digest("f"),
        text: "Zatwierdzony fakt urzędowy.",
        source_reference: "https://eli.gov.pl/acts/synthetic",
        freshness_date: "2026-09-24",
        source_type: "legal_update",
        official_source: true,
        privacy_class: "commit_safe",
        source_connectors: ["official_regulatory_review"],
        evidence_ids: ["ev_official_fact"],
        regulatory_requirement_ids: ["requirement_exact"]
      }],
      planning_context: {
        target_reader: "Przedsiębiorca",
        buyer_problem: "Niejasny obowiązek",
        buyer_trigger: "Zmiana prawa",
        search_intent: null
      },
      content_kind: "editorial",
      service_card_id: null,
      cta_direction: "Kontakt z doradcą",
      minimum_cta_blocks: 1,
      required_cta_patterns: [],
      internal_links: [{
        target_url: "https://www.ekologus.pl/kontakt/",
        anchor_hint: "Kontakt",
        source_connector: "wordpress_ekologus",
        evidence_ids: ["ev_link"]
      }],
      regulatory_profile_id: "profile_exact",
      regulatory_profile_version: "v1",
      legal_requirements: [{
        requirement_id: "requirement_exact",
        label: "Wymaganie prawne",
        source_fact_ids: ["fact_exact"],
        evidence_ids: ["ev_official_fact"]
      }],
      verification_evidence_ids: ["ev_official_fact", "ev_link"],
      verification_evidence_digest: digest("1"),
      blocker: null,
      generation_allowed: false,
      packet_write_allowed: false
    }
  };
}

function recordWithPageIdentity(pageUrl: string, canonicalPath: string) {
  const value = record();
  value.snapshot.page_url = pageUrl;
  value.snapshot.canonical_path = canonicalPath;
  return value;
}

describe("v3 research packet action contracts", () => {
  it("carries the exact planning subject when the preview has one", () => {
    const parsed = ResearchPacketV3PreviewRecordSchema.parse(record());
    expect(parsed.snapshot.content_kind).toBe("editorial");
    expect(parsed.snapshot.service_card_id).toBeNull();
  });

  it("preserves a historical snapshot without page identity but admits only an exact review", () => {
    const historical = record(false);
    expect(ResearchPacketV3PreviewRecordSchema.safeParse(historical).success).toBe(true);
    expect(ResearchPacketV3ReviewablePreviewRecordSchema.safeParse(historical).success).toBe(false);
    expect(ResearchPacketV3ReviewablePreviewRecordSchema.parse(record()).snapshot.page_url)
      .toBe("https://www.ekologus.pl/exact/");
  });

  it("preserves a page snapshot but blocks review when its per-URL identity is absent", () => {
    const historical = record();
    delete historical.snapshot.per_url_delivery_identity_action_id;
    expect(ResearchPacketV3PreviewRecordSchema.safeParse(historical).success).toBe(true);
    expect(ResearchPacketV3ReviewablePreviewRecordSchema.safeParse(historical).success)
      .toBe(false);
  });

  it("accepts raw Unicode paths and keeps percent-encoded paths exact", () => {
    expect(ResearchPacketV3ReviewablePreviewRecordSchema.safeParse(
      recordWithPageIdentity("https://www.ekologus.pl/zażółć/", "/zażółć")
    ).success).toBe(true);
    expect(ResearchPacketV3ReviewablePreviewRecordSchema.safeParse(
      recordWithPageIdentity("https://www.ekologus.pl/%C5%BC/", "/%C5%BC")
    ).success).toBe(true);
    expect(ResearchPacketV3ReviewablePreviewRecordSchema.safeParse(
      recordWithPageIdentity("https://www.ekologus.pl/%C5%BC/", "/ż")
    ).success).toBe(false);
    expect(ResearchPacketV3ReviewablePreviewRecordSchema.safeParse(
      recordWithPageIdentity("https://www.ekologus.pl/zażółć/", "/%C5%BC")
    ).success).toBe(false);
  });

  it("distinguishes a v3 ActionObject preview from its typed blocker", () => {
    const action = {
      id: "act_content_research_packet_v3_exact",
      title: "Zatwierdź dokładny pakiet badawczy v3",
      domain: "content",
      connector: "wordpress_ekologus",
      mode: "apply",
      risk: "low",
      status: "ready_to_apply",
      evidence_ids: ["ev_official_fact"],
      metrics: [],
      human_diagnosis: "Dokładny pakiet.",
      recommended_reason: "Sprawdź fakty.",
      validation_status: "not_validated",
      payload: {},
      audit_events: []
    };
    expect(ResearchPacketV3ActionResponseSchema.parse({
      response_type: "research_packet_v3_action",
      status: "preview_ready",
      action_id: action.id,
      action,
      preview: record().snapshot,
      external_write_attempted: false,
      generation_allowed: false
    }).status).toBe("preview_ready");
    expect(ResearchPacketV3ActionResponseSchema.parse({
      response_type: "research_packet_v3_action",
      status: "blocked",
      work_item_id: "wi_exact",
      blocker_code: "research_packet_v3_page_identity_missing",
      blocker_owner: "WILQ content workflow",
      evidence_ids: ["ev_official_fact"],
      safe_next_step: "Odczytaj dokładny adres strony.",
      external_write_attempted: false,
      generation_allowed: false
    }).status).toBe("blocked");
    expect(ResearchPacketV3PreviewResponseSchema.parse({
      contract_version: "research_packet_v3_preview",
      status: "blocked",
      work_item_id: "wi_exact",
      preview_id: null,
      page_url: null,
      canonical_path: null,
      selected_facts: [],
      blocker: {
        code: "research_packet_v3_page_identity_missing",
        owner: "WILQ content workflow",
        evidence_ids: [],
        safe_next_step: "Odczytaj dokładny adres strony."
      },
      generation_allowed: false,
      packet_write_allowed: false
    }).status).toBe("blocked");
  });
});
