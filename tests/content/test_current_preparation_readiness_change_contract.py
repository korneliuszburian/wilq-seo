"""Parent-safe source observer for exact current refresh preparation."""

from pathlib import Path


def _source(root: Path, relative: str) -> str:
    path = root / relative
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def test_current_preparation_source_contract() -> None:
    root = Path(__file__).resolve().parents[2]
    sources = {
        relative: _source(root, relative)
        for relative in (
            "wilq/content/workflow/current_preparation_readiness.py",
            "wilq/content/workflow/current_preparation_readiness_contracts.py",
            "wilq/content/workflow/current_preparation_readiness_support.py",
            "wilq/content/workflow/refresh_preparation_resolution.py",
            "wilq/content/workflow/research_packet_preparation.py",
            "wilq/content/workflow/workspace/production_decision.py",
            "wilq/content/workflow/workspace/selected_workspace.py",
            "apps/api/wilq_api/routers/content_selected_workspace.py",
        )
    }

    assert (
        "ready_for_refresh_authorization"
        in sources["wilq/content/workflow/current_preparation_readiness_contracts.py"]
    )
    assert (
        "current_content_binding_missing"
        in sources["wilq/content/workflow/current_preparation_readiness.py"]
    )
    assert (
        "resolve_current_preparation_readiness"
        in sources["wilq/content/workflow/refresh_preparation_resolution.py"]
    )
    assert (
        "latest_source_pack_for_work_item"
        in sources["wilq/content/workflow/research_packet_preparation.py"]
    )
    assert (
        "source_packet_row_digest"
        in sources["wilq/content/workflow/workspace/production_decision.py"]
    )
    assert (
        "_validate_ready_refresh_state"
        in sources["wilq/content/workflow/workspace/selected_workspace.py"]
    )
    assert (
        "Autoryzuj bieżący refresh"
        in sources["wilq/content/workflow/workspace/selected_workspace.py"]
    )
    assert (
        "current_preparation_readiness"
        in sources["apps/api/wilq_api/routers/content_selected_workspace.py"]
    )
