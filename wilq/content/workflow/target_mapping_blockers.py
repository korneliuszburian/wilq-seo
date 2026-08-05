from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.workflow.target_discovery import (
    ContentTargetAuthoringSurface,
    ContentTargetDiscovery,
)


class ContentTargetMappingBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: Literal[
        "revision_not_approved",
        "target_unavailable",
        "target_ambiguous",
        "authoring_surface_unknown",
        "acf_write_profile_unavailable",
    ]
    label: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    next_step: str = Field(min_length=1)


def discovery_blocker(
    discovery: ContentTargetDiscovery,
) -> ContentTargetMappingBlocker | None:
    if discovery.relation_status == "ambiguous":
        return ContentTargetMappingBlocker(
            code="target_ambiguous",
            label="Wymagany jest wybór obiektu dev",
            reason=(
                "WILQ odczytał kilka obiektów dev o tym samym adresie i nie "
                "wybiera jednego samodzielnie."
            ),
            next_step="Potwierdź właściwy obiekt dev, zanim powstanie mapowanie.",
        )
    if discovery.relation_status != "partial" or discovery.target is None:
        return ContentTargetMappingBlocker(
            code="target_unavailable",
            label="Brakuje potwierdzonego odczytu obiektu dev",
            reason=discovery.reason,
            next_step=(
                "Otwórz odczyt dev ponownie, gdy inventory będzie dostępne i wskaże "
                "jeden obiekt."
            ),
        )
    return None


def authoring_surface_blocker(
    surface: ContentTargetAuthoringSurface | None,
) -> ContentTargetMappingBlocker | None:
    if surface is None or not surface.layouts:
        reason = (
            "WILQ zna dokładny obiekt dev, ale nie odczytał pola ani układu, "
            "do którego można przypisać dokument."
            if surface is None
            else "WILQ odczytał pole układu treści, ale nie odczytał żadnego layoutu."
        )
        return ContentTargetMappingBlocker(
            code="authoring_surface_unknown",
            label="Nie rozpoznano układu treści na dev",
            reason=reason,
            next_step=(
                "Odczytaj potwierdzoną powierzchnię authoringu tego obiektu bez "
                "zgadywania pola lub layoutu."
            ),
        )
    if surface.kind == "acf_flexible_content" and surface.write_profile_status != "ready":
        return ContentTargetMappingBlocker(
            code="acf_write_profile_unavailable",
            label="ACF wymaga dokładnego profilu pól",
            reason=(
                surface.write_profile_reason
                or "Odczyt REST nie potwierdza typów, wymaganych pól ani "
                "bezpiecznych wartości layoutu ACF."
            ),
            next_step=(
                "Dodaj dokładny profil ACF tego pola i layoutu; "
                "dopiero potem potwierdź przypisanie."
            ),
        )
    return None
