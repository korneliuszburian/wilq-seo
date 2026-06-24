from __future__ import annotations

from scripts.export_content_mapping_review_packet import (
    build_mapping_review_packet,
    render_markdown,
)


def test_content_mapping_review_packet_preserves_review_only_boundaries() -> None:
    diagnostics = {
        "generated_at": "2026-06-24T20:00:00Z",
        "language": "pl-PL",
        "operator_summary": {
            "target_site_host": "ekologus.dev.proudsite.pl",
            "target_site_mapping_status": "target_site_mapping_review_needed",
            "target_site_migration_map": [
                {
                    "candidate_id": "content_brief_gsc_bdo",
                    "status_summary": (
                        "Dokładny kandydat old-to-new nie istnieje w inventory."
                    ),
                }
            ],
            "target_site_mapping_review_inputs": [
                {
                    "decision_id": "content_decision_bdo",
                    "candidate_id": "content_brief_gsc_bdo",
                    "title": "SEO: odśwież BDO",
                    "source_url": "https://www.ekologus.pl/bdo/",
                    "current_migration_candidate_url": (
                        "https://ekologus.dev.proudsite.pl/bdo/"
                    ),
                    "candidate_target_urls": [
                        "https://ekologus.dev.proudsite.pl/uslugi/bdo/"
                    ],
                    "mapping_review_status": "review_alternative_candidates",
                    "allowed_outcomes": [
                        "confirm_alternative_candidate",
                        "manual_mapping_required",
                    ],
                    "review_endpoint": (
                        "/api/actions/act_prepare_content_refresh_queue/review"
                    ),
                    "review_payload_template": {
                        "outcome": "approved_for_prepare",
                        "reviewed_by": "<operator>",
                        "checked_items": [
                            "candidate:content_brief_gsc_bdo",
                            "mapping_outcome:<wybierz allowed_outcome>",
                            "selected_target_url:https://ekologus.dev.proudsite.pl/uslugi/bdo/",
                            "mapping_notes:<krótka decyzja marketera>",
                        ],
                        "blockers": [
                            "payload_apply_allowed_false",
                            "wordpress_write_not_requested",
                        ],
                    },
                    "blocked_outputs": [
                        "wordpress_staging_write",
                        "wordpress_publish",
                        "ranking_or_lead_uplift_claim",
                    ],
                }
            ],
        },
    }

    packet = build_mapping_review_packet(diagnostics)

    assert packet["packet_type"] == "content_target_site_mapping_review_packet_v1"
    assert packet["mapping_status"] == "target_site_mapping_review_needed"
    assert packet["review_endpoint"] == (
        "/api/actions/act_prepare_content_refresh_queue/review"
    )
    assert packet["items"][0]["fill_before_post"] == {
        "reviewed_by": "<operator>",
        "mapping_outcome": "<wybierz allowed_outcome>",
        "selected_target_url": "<wybierz target URL albo wpisz ręczny URL>",
        "mapping_notes": "<krótka decyzja marketera>",
    }
    assert "wordpress_publish" in packet["blocked_outputs"]
    assert "ranking_or_lead_uplift_claim" in packet["blocked_outputs"]
    assert "Nie potwierdza migracji" in packet["safety_note"]


def test_content_mapping_review_packet_markdown_is_operator_readable() -> None:
    packet = {
        "packet_type": "content_target_site_mapping_review_packet_v1",
        "generated_at": "2026-06-24T20:00:00Z",
        "target_site_host": "ekologus.dev.proudsite.pl",
        "mapping_status": "target_site_mapping_review_needed",
        "review_endpoint": "/api/actions/act_prepare_content_refresh_queue/review",
        "review_count": 1,
        "safety_note": "Ten pakiet tylko zbiera ręczne review mapowania.",
        "items": [
            {
                "candidate_id": "content_brief_gsc_bdo",
                "title": "SEO: odśwież BDO",
                "source_url": "https://www.ekologus.pl/bdo/",
                "current_migration_candidate_url": (
                    "https://ekologus.dev.proudsite.pl/bdo/"
                ),
                "candidate_target_urls": [
                    "https://ekologus.dev.proudsite.pl/uslugi/bdo/"
                ],
                "mapping_review_status": "review_alternative_candidates",
                "status_summary": "Przejrzyj alternatywny URL.",
                "allowed_outcomes": ["confirm_alternative_candidate"],
                "review_payload_template": {"outcome": "approved_for_prepare"},
                "fill_before_post": {
                    "mapping_outcome": "<wybierz allowed_outcome>",
                },
                "blocked_outputs": ["wordpress_publish"],
            }
        ],
    }

    markdown = render_markdown(packet)

    assert "# Content Mapping Review Packet" in markdown
    assert "Payload template to post after human review" in markdown
    assert "Fill before POST" in markdown
    assert "`wordpress_publish`" in markdown
