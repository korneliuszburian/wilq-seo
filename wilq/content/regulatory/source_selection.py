"""Deterministic bounded-source selection for regulatory source proposals."""

from __future__ import annotations

import re

from wilq.content.regulatory.policy import (
    ContentRegulatorySourceCandidate,
    ContentRegulatorySourceExcludedRange,
)


class RegulatorySourceSelectionError(ValueError):
    """Typed fail-closed error for a server-owned bounded source selector."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(f"{code}: {detail}")


def select_bounded_source_text(
    candidate: ContentRegulatorySourceCandidate,
    source_text: str,
) -> str:
    selector = candidate.selector
    if selector is None:
        return source_text
    if selector.kind == "provision_range":
        assert selector.start_anchor is not None
        assert selector.end_anchor is not None
        start = _require_unique_anchor(source_text, selector.start_anchor, "start")
        end_anchor_end = _require_unique_anchor_span(source_text, selector.end_anchor, "end")[1]
        next_provision = re.search(
            r"(?im)^\s*Art\.\s*\d+[a-z]?\.",
            source_text[end_anchor_end:],
        )
        end = (
            end_anchor_end + next_provision.start()
            if next_provision is not None
            else min(len(source_text), end_anchor_end + selector.context_chars)
        )
        if start >= end:
            raise RegulatorySourceSelectionError(
                "invalid_range", "the provision range has reversed anchors"
            )
        selected = source_text[start:end]
    elif selector.kind == "bounded_document":
        selected = source_text
    else:
        spans = [
            _require_unique_anchor_span(source_text, anchor, "required")
            for anchor in selector.required_anchors
        ]
        selected = _merge_heading_contexts(source_text, spans, selector.context_chars)

    if selector.kind == "bounded_document":
        required_anchor_spans = [
            _require_present_anchor(selected, anchor, "required")
            for anchor in selector.required_anchors
        ]
    else:
        required_anchor_spans = [
            _require_unique_anchor_span(selected, anchor, "required")
            for anchor in selector.required_anchors
        ]

    selected, removed_spans = _remove_excluded_ranges(selected, selector.excluded_ranges)
    if any(
        required_start < removed_end and removed_start < required_end
        for required_start, required_end in required_anchor_spans
        for removed_start, removed_end in removed_spans
    ):
        raise RegulatorySourceSelectionError(
            "required_anchor_removed",
            "a required anchor overlaps an excluded source range",
        )
    # ``excluded_anchors`` is retained only for legacy selectors. New legal
    # scopes use typed exact ranges so neighboring provisions remain intact.
    if selector.excluded_anchors:
        selected = _remove_excluded_anchor_lines(selected, selector.excluded_anchors)
    try:
        if selector.kind == "bounded_document":
            for anchor in selector.required_anchors:
                _require_present_anchor(selected, anchor, "required")
        else:
            for anchor in selector.required_anchors:
                _require_unique_anchor(selected, anchor, "required")
    except RegulatorySourceSelectionError as error:
        if error.code != "missing_anchor":
            raise
        raise RegulatorySourceSelectionError(
            "required_anchor_removed",
            f"required anchor was removed by exclusions ({error})",
        ) from error
    for anchor in selector.residual_forbidden_anchors:
        if _selector_anchor_spans(selected, anchor):
            raise RegulatorySourceSelectionError(
                "future_marker_present",
                f"residual forbidden anchor {anchor!r} remains in the selected source scope",
            )
    if len(selected) > selector.max_chars:
        raise RegulatorySourceSelectionError(
            "selection_too_large",
            f"selected source scope exceeds {selector.max_chars} characters",
        )
    selected = selected.strip()
    if not selected:
        raise RegulatorySourceSelectionError(
            "selection_empty", "the bounded source scope contains no current text"
        )
    return selected


def _require_unique_anchor(text: str, anchor: str, role: str) -> int:
    return _require_unique_anchor_span(text, anchor, role)[0]


def _require_unique_anchor_span(text: str, anchor: str, role: str) -> tuple[int, int]:
    spans = _selector_anchor_spans(text, anchor)
    if not spans:
        raise RegulatorySourceSelectionError(
            "missing_anchor", f"{role} anchor {anchor!r} is missing"
        )
    if len(spans) != 1:
        raise RegulatorySourceSelectionError(
            "ambiguous_anchor", f"{role} anchor {anchor!r} occurs {len(spans)} times"
        )
    return spans[0]


def _require_present_anchor(text: str, anchor: str, role: str) -> tuple[int, int]:
    spans = _selector_anchor_spans(text, anchor)
    if not spans:
        raise RegulatorySourceSelectionError(
            "missing_anchor", f"{role} anchor {anchor!r} is missing"
        )
    return spans[0]


def _selector_anchor_spans(text: str, anchor: str) -> list[tuple[int, int]]:
    parts = [part for part in re.split(r"\s+", anchor.strip()) if part]
    if not parts:
        return []
    first_char_is_word = re.match(r"\w", parts[0][0]) is not None
    last_char_is_word = re.match(r"\w", parts[-1][-1]) is not None
    left_boundary = r"(?<!\w)" if first_char_is_word else ""
    right_boundary = r"(?!\w)" if last_char_is_word else ""
    pattern = (
        left_boundary
        + r"\s+".join(re.escape(part) for part in parts)
        + right_boundary
    )
    flags = re.IGNORECASE
    if anchor.strip().casefold().startswith("art."):
        heading_pattern = r"(?im)^\s*" + pattern
        heading_spans = [match.span() for match in re.finditer(heading_pattern, text)]
        if heading_spans:
            return heading_spans
    return [match.span() for match in re.finditer(pattern, text, flags=flags)]


def _merge_heading_contexts(
    source_text: str,
    spans: list[tuple[int, int]],
    context_chars: int,
) -> str:
    half_context = context_chars // 4
    ranges = sorted(
        (
            max(0, start - half_context),
            min(len(source_text), max(anchor_end, start + context_chars)),
        )
        for start, anchor_end in spans
    )
    merged: list[tuple[int, int]] = []
    for start, end in ranges:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return "\n\n[...fragmenty źródła poza zakresem... ]\n\n".join(
        source_text[start:end] for start, end in merged
    )


def _remove_excluded_ranges(
    text: str,
    ranges: list[ContentRegulatorySourceExcludedRange],
) -> tuple[str, list[tuple[int, int]]]:
    spans: list[tuple[int, int]] = []
    for excluded in ranges:
        start, start_end = _require_unique_anchor_span(
            text, excluded.start_anchor, "excluded range start"
        )
        end_candidates = [
            span
            for span in _selector_anchor_spans(text, excluded.end_anchor)
            if span[0] >= start_end
        ]
        if not end_candidates:
            raise RegulatorySourceSelectionError(
                "missing_excluded_range_end",
                f"end anchor {excluded.end_anchor!r} does not follow {excluded.start_anchor!r}",
            )
        spans.append((start, end_candidates[0][1]))
    ordered = sorted(spans)
    if any(
        previous_end > start
        for (_, previous_end), (start, _) in zip(ordered, ordered[1:], strict=False)
    ):
        raise RegulatorySourceSelectionError(
            "overlapping_excluded_ranges", "excluded source ranges overlap"
        )
    for start, end in reversed(ordered):
        text = text[:start] + text[end:]
    return text, ordered


def _remove_excluded_anchor_lines(text: str, anchors: list[str]) -> str:
    selected = text
    for anchor in anchors:
        while True:
            spans = _selector_anchor_spans(selected, anchor)
            if not spans:
                break
            start, end = spans[0]
            line_start = selected.rfind("\n", 0, start) + 1
            line_end = selected.find("\n", end)
            if line_end == -1:
                line_end = len(selected)
            remove_end = line_end
            continuation_start = line_end + 1
            while continuation_start < len(selected):
                continuation_end = selected.find("\n", continuation_start)
                if continuation_end == -1:
                    continuation_end = len(selected)
                continuation = selected[continuation_start:continuation_end]
                if re.match(r"\s*Art\.\s*\d+[a-z]?\.", continuation, flags=re.IGNORECASE):
                    break
                remove_end = continuation_end
                continuation_start = continuation_end + 1
            prefix = selected[line_start:start]
            if prefix.strip():
                replacement = selected[:start] + selected[remove_end:]
                selected = replacement
            else:
                selected = selected[:line_start] + selected[remove_end:]
    if any(_selector_anchor_spans(selected, anchor) for anchor in anchors):
        raise RegulatorySourceSelectionError(
            "excluded_anchor_present", "an excluded future provision remains in scope"
        )
    return selected


__all__ = ["RegulatorySourceSelectionError", "select_bounded_source_text"]
