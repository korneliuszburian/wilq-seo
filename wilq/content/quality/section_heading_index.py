from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class SectionHeadingIndex:
    _section_ids_by_heading: Mapping[str, tuple[str, ...]]

    def resolve(self, heading: str) -> str | None:
        section_ids = self._section_ids_by_heading.get(heading)
        if section_ids is None or len(section_ids) != 1:
            return None
        return next(iter(section_ids))

    def colliding(self, heading: str) -> bool:
        return len(self._section_ids_by_heading.get(heading, ())) > 1


def build_section_heading_index(
    headings: Iterable[tuple[str, str]],
) -> SectionHeadingIndex:
    section_ids_by_heading: dict[str, list[str]] = {}
    for section_id, heading in headings:
        section_ids_by_heading.setdefault(heading, []).append(section_id)
    return SectionHeadingIndex(
        MappingProxyType(
            {
                heading: tuple(section_ids)
                for heading, section_ids in section_ids_by_heading.items()
            }
        )
    )


__all__ = ["SectionHeadingIndex", "build_section_heading_index"]
