"""A protected concept must not keep an editorial working note in reader text.

Live BDO: deterministic regulatory grounding appended an approved fact whose
sentence carried both the protected concept and a human-review working note, so
the readability gate blocked the draft with ``working_note``. Keep the concept
and strip only the note.
"""

from __future__ import annotations

from wilq.content.drafts.document_facts import safe_document_ready_fact_text
from wilq.content.quality.working_note import contains_working_note

_TERM = "przed transportem"
_FACT = (
    "Kartę Przekazania Odpadów sporządza się przed transportem i wymaga "
    "weryfikacji przez człowieka przed dalszym użyciem."
)


def test_protected_term_does_not_keep_a_working_note() -> None:
    result = safe_document_ready_fact_text(_FACT, protected_terms=[_TERM])

    assert result is not None
    assert _TERM in result
    assert contains_working_note(result) is False
