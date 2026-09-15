"""Source observer consumed only by the current-disposition change gate."""

from pathlib import Path


def test_current_disposition_card_source_contract() -> None:
    detail_panels = (
        Path(__file__).resolve().parents[2]
        / "apps/dashboard/src/routes/DetailPanels.tsx"
    )
    source = detail_panels.read_text(encoding="utf-8")
    required_fragments = (
        'proposedFinalDisposition !== "keep"',
        '<article className="current-disposition-card" data-state={receipt.proposedFinalDisposition}>',
        "Czy zachowujemy tę stronę do dalszej aktualizacji?",
        "event.action_id !== action.id",
        "!event.id.trim()",
        "approveCurrentDisposition",
        '<button',
        'className="current-disposition-card__primary-action"',
        "Zatwierdź kierunek",
        "Kierunek zapisany",
    )

    assert all(fragment in source for fragment in required_fragments)
    assert 'href="#action-review"' not in source
    assert "Przejdź do zatwierdzenia" not in source
