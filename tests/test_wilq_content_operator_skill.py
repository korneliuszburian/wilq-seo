from __future__ import annotations

from pathlib import Path

CONTENT_OPERATOR_SKILL_PATH = Path(".agents/skills/wilq-content-operator/SKILL.md")
CONTENT_OPERATOR_OUTPUT_CONTRACT_PATH = Path(
    ".agents/skills/wilq-content-operator/references/output-contract.md"
)
CONTENT_OPERATOR_SMOKE_PATH = Path(
    ".agents/skills/wilq-content-operator/scripts/smoke_skill_contract.py"
)
CONTENT_OPERATOR_UAT_PATH = Path(
    ".agents/skills/wilq-content-operator/scripts/build_uat_packet.py"
)


def test_wilq_content_operator_skill_is_api_orchestrator_not_writer() -> None:
    skill_doc = CONTENT_OPERATOR_SKILL_PATH.read_text(encoding="utf-8")
    output_contract = CONTENT_OPERATOR_OUTPUT_CONTRACT_PATH.read_text(encoding="utf-8")
    smoke_script = CONTENT_OPERATOR_SMOKE_PATH.read_text(encoding="utf-8")
    uat_script = CONTENT_OPERATOR_UAT_PATH.read_text(encoding="utf-8")

    for endpoint in (
        "GET /api/content/work-items/queue",
        "GET /api/content/work-items/{work_item_id}/snapshot",
        "GET /api/content/work-items/{work_item_id}/enrichment",
        "GET /api/content/knowledge-cards",
        "POST /api/content/work-items/structured-draft-runtime",
        "POST /api/content/work-items/quality-review",
        "POST /api/content/work-items/revision-apply",
        "POST /api/content/work-items/wordpress-draft-execution",
        "POST /api/content/work-items/measurement-outcome",
    ):
        assert endpoint in skill_doc

    for phrase in (
        "nie jako autora tekstu",
        "Nie wywołuj OpenAI SDK bezpośrednio",
        "Nie wywołuj WordPress bezpośrednio",
        "Nie ustawiaj ani nie akceptuj `publish_ready=true`",
        "Brak preflightu oznacza brak pisania",
        "Brak measurement window oznacza brak wniosku o sukcesie albo porażce",
    ):
        assert phrase in skill_doc or phrase in output_contract

    for marker in (
        "/api/content/work-items/queue",
        "/api/content/work-items/{work_item_id}/snapshot",
        "/api/content/work-items/{work_item_id}/enrichment",
        "/api/content/knowledge-cards",
        "/api/content/work-items/wordpress-draft-execution",
        "/api/content/work-items/measurement-outcome",
        "publish_ready",
        "publish_allowed",
        "destructive_update_allowed",
        "external_write_attempted",
        "ekologus.dev.proudsite.pl",
        "measured_success",
    ):
        assert marker in smoke_script

    for marker in (
        "uat_tasks",
        "3-5",
        "/api/content/service-profile",
        "Service Profile",
        "private_review_actions",
        "Service Profile nie jest production-depth",
        "promotion_checklist",
        "warunki przed reviewed source fact",
        "Private proposal review action nie promuje faktu ani karty wiedzy.",
        "Dev URL nie jest canonical",
        "WordPress pozostaje draft-only",
        "/api/content/work-items/queue",
        "/api/content/work-items/{work_item_id}/enrichment",
    ):
        assert marker in uat_script
