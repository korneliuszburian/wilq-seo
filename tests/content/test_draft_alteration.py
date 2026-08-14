from types import SimpleNamespace

import pytest

from wilq.content.drafts import draft_alteration
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.drafts.draft_alteration import alter_draft_towards_persistence
from wilq.content.drafts.draft_assurance import ContentDraftAssuranceReceipt
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftModelOutput,
    ContentInitialDraftSectionOutput,
)
from wilq.content.workflow.documents.revisions import ContentDraftRevisionPageAssets


def _output() -> ContentInitialDraftModelOutput:
    return ContentInitialDraftModelOutput(
        page_assets=ContentDraftRevisionPageAssets(
            wordpress_title="t",
            meta_title="m",
            meta_description="d",
            h1="h",
            lead="l",
        ),
        sections=[
            ContentInitialDraftSectionOutput(
                section_id="section_01",
                heading="Sekcja",
                body_markdown="Treść sekcji.",
            )
        ],
        publish_ready=False,
    )


def _trace() -> ContentCodexRuntimeTrace:
    return ContentCodexRuntimeTrace(status="completed", turn_id="turn")


def _receipt() -> ContentDraftAssuranceReceipt:
    return ContentDraftAssuranceReceipt(
        status="passed",
        profile_id="profile",
        profile_version="1",
        codex_run_id="run",
    )


def test_alteration_skips_regulatory_repair_when_readability_is_clean(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _output()
    trace = _trace()
    calls: list[str] = []
    initial_assurance = _receipt()

    monkeypatch.setattr(
        draft_alteration,
        "repair_initial_output_blocker",
        lambda **kwargs: (kwargs["output"], kwargs["trace"], None),
    )

    def fake_assure_and_repair(**kwargs):
        calls.append("assure")
        return kwargs["output"], kwargs["trace"], initial_assurance, None

    monkeypatch.setattr(draft_alteration, "assure_and_repair_initial_draft", fake_assure_and_repair)

    def fake_readability(**kwargs):
        calls.append("readability")
        return kwargs["output"], kwargs["trace"], None

    monkeypatch.setattr(draft_alteration, "assure_readability_and_repair", fake_readability)
    monkeypatch.setattr(
        draft_alteration,
        "repair_regulatory_assertions",
        lambda **kwargs: pytest.fail("regulatory repair must not run on a clean readability pass"),
    )

    result = alter_draft_towards_persistence(
        planning_input=SimpleNamespace(),
        proposal=SimpleNamespace(),
        output=output,
        trace=trace,
        client=SimpleNamespace(),
        run_store=SimpleNamespace(),
        output_blocker=lambda _candidate: None,
    )

    assert result.status == "ready"
    assert calls == ["assure", "readability"]


def test_alteration_grounds_regulatory_terms_only_after_readability_blocker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _output()
    trace = _trace()
    calls: list[str] = []

    monkeypatch.setattr(
        draft_alteration,
        "repair_initial_output_blocker",
        lambda **kwargs: (kwargs["output"], kwargs["trace"], None),
    )
    monkeypatch.setattr(
        draft_alteration,
        "assure_and_repair_initial_draft",
        lambda **kwargs: (kwargs["output"], kwargs["trace"], _receipt(), None),
    )

    def fake_readability(**kwargs):
        calls.append("readability")
        from wilq.content.drafts.initial_full_draft_contracts import ContentInitialDraftBlocker

        blocker = ContentInitialDraftBlocker(
            code="readability_gate_failed",
            label="Bramka czytelności",
            reason="Sekcja wymaga naprawy.",
            next_step="Popraw.",
            source_codes=["long_sentence"],
        )
        return kwargs["output"], kwargs["trace"], blocker

    monkeypatch.setattr(draft_alteration, "assure_readability_and_repair", fake_readability)

    def fake_regulatory_repair(**kwargs):
        calls.append("regulatory_repair")
        return kwargs["output"], _trace()

    monkeypatch.setattr(draft_alteration, "repair_regulatory_assertions", fake_regulatory_repair)
    monkeypatch.setattr(
        draft_alteration,
        "_ALTERNATION_BUDGET",
        0,
    )

    result = alter_draft_towards_persistence(
        planning_input=SimpleNamespace(),
        proposal=SimpleNamespace(),
        output=output,
        trace=trace,
        client=SimpleNamespace(),
        run_store=SimpleNamespace(),
        output_blocker=lambda _candidate: None,
    )

    assert result.status == "ready"
    assert calls.count("regulatory_repair") >= 1
    assert calls.index("regulatory_repair") > calls.index("readability")


def test_alteration_terminates_on_blocker_without_assurance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _output()
    trace = _trace()
    from wilq.content.drafts.initial_full_draft_contracts import ContentInitialDraftBlocker

    blocker = ContentInitialDraftBlocker(
        code="document_scope_mismatch",
        label="Niezgodność zakresu",
        reason="Plan i dokument są niezgodne.",
        next_step="Wygeneruj ponownie.",
        source_codes=["sections"],
    )
    monkeypatch.setattr(
        draft_alteration,
        "repair_initial_output_blocker",
        lambda **kwargs: (kwargs["output"], kwargs["trace"], blocker),
    )
    monkeypatch.setattr(
        draft_alteration,
        "assure_and_repair_initial_draft",
        lambda **kwargs: pytest.fail("assurance must not run after a terminal scope blocker"),
    )

    result = alter_draft_towards_persistence(
        planning_input=SimpleNamespace(),
        proposal=SimpleNamespace(),
        output=output,
        trace=trace,
        client=SimpleNamespace(),
        run_store=SimpleNamespace(),
        output_blocker=lambda _candidate: None,
    )

    assert result.status == "blocked"
    assert result.blocker is blocker
