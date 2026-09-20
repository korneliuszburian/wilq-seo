from pathlib import Path


def test_planning_directives_are_claim_free_and_publicly_revalidated() -> None:
    root = Path(__file__).resolve().parents[2]
    prompt = (root / "wilq/codex/prompts.py").read_text(encoding="utf-8")
    model_validation = (
        root / "wilq/content/planning/proposal_lineage.py"
    ).read_text(encoding="utf-8")
    public_validation = (
        root / "wilq/content/planning/generated_proposal_contracts.py"
    ).read_text(encoding="utf-8")

    assert 'id="planning_proposal",\n        version=2' in prompt
    assert "nie kopiuj" in prompt and "kwot" in prompt
    assert "canonicalize_regulatory_section_assertions(planning_input, output)" not in (
        root / "wilq/content/planning/generated_proposal.py"
    ).read_text(encoding="utf-8")
    assert "regulatory_directive_value_errors(" in model_validation
    assert "regulatory_directive_value_errors(" in public_validation
