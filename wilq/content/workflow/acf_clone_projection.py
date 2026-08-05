from __future__ import annotations

from copy import deepcopy
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.connectors.wordpress.acf_source_snapshot import WordPressAcfFlexibleSnapshot


class ContentAcfCloneReplacement(BaseModel):
    """One approved scalar replacement in an observed Flexible Content row."""

    model_config = ConfigDict(extra="forbid")

    section_index: int = Field(ge=1)
    layout_name: str = Field(min_length=1)
    field_name: str = Field(min_length=1)
    value: str
    value_kind: Literal["plain_text", "html", "url"]


class ContentAcfClonePlan(BaseModel):
    """Persistable identity of an ACF clone without retaining raw vendor data."""

    model_config = ConfigDict(extra="forbid")

    source_object_id: str = Field(min_length=1)
    root_field: str = Field(min_length=1)
    source_acf_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    replacements: list[ContentAcfCloneReplacement] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_leaf_replacements(self) -> ContentAcfClonePlan:
        keys = [
            (replacement.section_index, replacement.field_name)
            for replacement in self.replacements
        ]
        if len(keys) != len(set(keys)):
            raise ValueError("Plan ACF nie może podmienić jednego pola dwa razy.")
        return self


def compile_acf_clone_payload(
    plan: ContentAcfClonePlan,
    snapshot: WordPressAcfFlexibleSnapshot,
) -> dict[str, list[dict[str, object]]]:
    """Clone the exact current ACF root and apply approved direct-string leaves.

    The full source value is deliberately short-lived.  It is read immediately
    before the WordPress create call, deep-copied in memory, and never persisted
    in WILQ.  Any source drift, missing row, changed layout or non-string leaf
    blocks the create before a vendor mutation is attempted.
    """

    if snapshot.object_id != plan.source_object_id:
        raise ValueError("Odczyt ACF wskazuje inny obiekt niż zatwierdzony target.")
    if snapshot.root_field != plan.root_field:
        raise ValueError("Odczyt ACF wskazuje inne pole niż zatwierdzony target.")
    if snapshot.root_digest != plan.source_acf_digest:
        raise ValueError(
            "Źródłowy układ ACF zmienił się od potwierdzenia; utwórz nowe mapowanie."
        )

    rows: list[dict[str, object]] = deepcopy(snapshot.rows)
    for replacement in plan.replacements:
        row_index = replacement.section_index - 1
        if row_index >= len(rows):
            raise ValueError("Zatwierdzona sekcja ACF nie istnieje już w źródłowym układzie.")
        row = rows[row_index]
        if row.get("acf_fc_layout") != replacement.layout_name:
            raise ValueError("Układ zatwierdzonej sekcji ACF zmienił się przed zapisem.")
        source_value = row.get(replacement.field_name)
        if not isinstance(source_value, str):
            raise ValueError(
                "Zatwierdzone pole ACF nie jest bezpośrednią wartością tekstową."
            )
        row[replacement.field_name] = replacement.value
    return {plan.root_field: rows}


__all__ = [
    "ContentAcfClonePlan",
    "ContentAcfCloneReplacement",
    "compile_acf_clone_payload",
]
