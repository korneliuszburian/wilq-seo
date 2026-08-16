from __future__ import annotations

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WILKU_UAT_PACKET = (
    REPOSITORY_ROOT
    / "docs"
    / "review-packets"
    / "2026-08-15-wilku-content-uat"
    / "PACZKA-DO-OCENY-2026-08-15.md"
)
CONTENT_REVIEW_PACKET = (
    REPOSITORY_ROOT
    / "docs"
    / "agents"
    / "reports"
    / "content-review"
    / "paczka-tresci-5-stron-2026-08-12.md"
)


def test_wilku_uat_packet_has_required_decision_surface() -> None:
    packet = WILKU_UAT_PACKET.read_text(encoding="utf-8")

    for marker in (
        "Rekomendacja WILQ na dziś",
        "Blokery",
        "Pytania do Wilku",
        "Wynik sesji",
        "approved",
        "needs_changes",
        "rejected",
        "human_review_required",
        "publish_ready=false",
        "content_revision_f4c23cfcd5b6449c83281545b4883e2c",
        "fixed point",
        "manifest",
    ):
        assert marker in packet, f"Brak wymaganego elementu pakietu: {marker}"


def test_wilku_uat_packet_matches_content_review_packet_revisions() -> None:
    packet = WILKU_UAT_PACKET.read_text(encoding="utf-8")
    review = CONTENT_REVIEW_PACKET.read_text(encoding="utf-8")

    for revision_id in (
        "content_revision_f4c23cfcd5b6449c83281545b4883e2c",
        "content_revision_66f7eec3ec9646a5a8ed5327a44e3da8",
        "content_revision_62ef7b61f6fd4a399a41d3ab33094fc9",
        "content_revision_b14c7fc23fcc4907aadf24c431cc656a",
        "content_revision_787c4e52b3f941f3a048a63355e8cf45",
    ):
        assert revision_id in review, f"Rewizja {revision_id} brakuje w paczce treści"
        assert revision_id in packet, f"Rewizja {revision_id} brakuje w pakiecie UAT"


def test_wilku_uat_packet_contains_no_secret_looking_literals() -> None:
    content = WILKU_UAT_PACKET.read_text(encoding="utf-8").casefold()

    for marker in ("sk-", "akia", "password=", "token=", "client_secret", "refresh_token"):
        assert marker not in content, f"Wykryto podejrzany literał: {marker}"


DAILY_CHECK_PACKET = (
    REPOSITORY_ROOT
    / "docs"
    / "review-packets"
    / "2026-08-16-wilku-daily-check"
    / "PACZKA-DO-OCENY-2026-08-16.md"
)


def test_wilku_daily_check_packet_records_the_live_fail_closed_state() -> None:
    packet = DAILY_CHECK_PACKET.read_text(encoding="utf-8")

    for marker in (
        "Werdykt dnia",
        "4 zablokowane rekomendacje",
        "blocked",
        "Brak świeżego odczytu vendorów",
        "Pytania do Wilku",
        "vendor_read",
        "NIE jest UAT",
        "safe_next_actions=[]",
    ):
        assert marker in packet, f"Brak wymaganego elementu pakietu daily-check: {marker}"
