from wilq.connectors.wordpress.acf_source_snapshot import WordPressAcfFlexibleSnapshot
from wilq.content.workflow.acf_clone_projection import (
    ContentAcfClonePlan,
    ContentAcfCloneReplacement,
    compile_acf_clone_payload,
)


def _snapshot(*, digest: str = "a" * 64) -> WordPressAcfFlexibleSnapshot:
    return WordPressAcfFlexibleSnapshot(
        object_id="2",
        content_type="pages",
        root_field="flexible-home",
        root_digest=digest,
        rows=[
            {
                "acf_fc_layout": "cta",
                "content": "Pierwsze CTA",
                "image": 101,
                "settings": {"theme": "dark"},
            },
            {
                "acf_fc_layout": "cta",
                "content": "Drugie CTA",
                "image": 202,
                "settings": {"theme": "light"},
            },
        ],
    )


def test_acf_clone_projection_replaces_exact_row_and_preserves_other_values() -> None:
    snapshot = _snapshot()
    plan = ContentAcfClonePlan(
        source_object_id="2",
        root_field="flexible-home",
        source_acf_digest=snapshot.root_digest,
        replacements=[
            ContentAcfCloneReplacement(
                section_index=2,
                layout_name="cta",
                field_name="content",
                value="Nowe CTA",
                value_kind="html",
            )
        ],
    )

    payload = compile_acf_clone_payload(plan, snapshot)

    assert payload == {
        "flexible-home": [
            {
                "acf_fc_layout": "cta",
                "content": "Pierwsze CTA",
                "image": 101,
                "settings": {"theme": "dark"},
            },
            {
                "acf_fc_layout": "cta",
                "content": "Nowe CTA",
                "image": 202,
                "settings": {"theme": "light"},
            },
        ]
    }
    assert snapshot.rows[1]["content"] == "Drugie CTA"


def test_acf_clone_projection_fails_closed_on_source_drift_or_layout_change() -> None:
    snapshot = _snapshot()
    plan = ContentAcfClonePlan(
        source_object_id="2",
        root_field="flexible-home",
        source_acf_digest="b" * 64,
        replacements=[
            ContentAcfCloneReplacement(
                section_index=2,
                layout_name="cta",
                field_name="content",
                value="Nowe CTA",
                value_kind="html",
            )
        ],
    )

    try:
        compile_acf_clone_payload(plan, snapshot)
    except ValueError as error:
        assert "zmienił się" in str(error)
    else:
        raise AssertionError("Drift ACF nie może utworzyć payloadu.")

    mismatched_layout = _snapshot()
    mismatched_layout.rows[1]["acf_fc_layout"] = "hero"
    exact_plan = plan.model_copy(update={"source_acf_digest": mismatched_layout.root_digest})
    try:
        compile_acf_clone_payload(exact_plan, mismatched_layout)
    except ValueError as error:
        assert "Układ zatwierdzonej sekcji" in str(error)
    else:
        raise AssertionError("Zmiana layoutu nie może utworzyć payloadu.")
