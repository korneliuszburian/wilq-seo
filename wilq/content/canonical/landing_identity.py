from __future__ import annotations

from collections.abc import Iterable
from typing import Literal, cast
from urllib.parse import parse_qsl, urlencode, urlparse

from pydantic import BaseModel, ConfigDict, Field

LandingIdentityStatus = Literal["resolved", "missing", "invalid"]
LandingMatchTier = Literal[
    "exact",
    "tracking_only",
    "host_alias",
    "path_only",
    "functional_query",
    "ambiguous",
    "missing",
    "no_match",
]

_MISSING_VALUES = {"", "(not set)", "(not provided)", "not set", "not provided"}
_TRACKING_PARAMETER_NAMES = {
    "_ga",
    "_gl",
    "dclid",
    "fbclid",
    "gbraid",
    "gclid",
    "msclkid",
    "wbraid",
}
_HOST_ALIASES = {
    "ekologus.pl": "www.ekologus.pl",
    "www.ekologus.pl": "www.ekologus.pl",
}
_CANONICAL_HOST_LOOKUP_ALIASES = {
    "www.ekologus.pl": ["www.ekologus.pl", "ekologus.pl"],
}


class LandingPageIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: LandingIdentityStatus
    canonical_url: str | None = None
    normalized_scheme: Literal["http", "https"] | None = None
    normalized_host: str | None = None
    normalized_port: int | None = None
    normalized_path: str | None = None
    functional_query: str | None = None
    removed_tracking_parameters: list[str] = Field(default_factory=list)
    host_alias_applied: bool = False
    path_only: bool = False


class LandingPageCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: str = Field(min_length=1)
    url: str | None = None


class LandingPageCandidateMatch(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: str = Field(min_length=1)
    tier: LandingMatchTier
    matched: bool
    review_required: bool
    identity: LandingPageIdentity


class LandingPageResolution(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    expected_identity: LandingPageIdentity
    tier: LandingMatchTier
    selected_candidate_id: str | None = None
    matched_candidate_ids: list[str] = Field(default_factory=list)
    review_required: bool
    candidates: list[LandingPageCandidateMatch] = Field(default_factory=list)


def build_landing_page_identity(
    value: str | None,
    *,
    reference_url: str | None = None,
) -> LandingPageIdentity:
    normalized_value = (value or "").strip()
    if normalized_value.casefold() in _MISSING_VALUES:
        return LandingPageIdentity(status="missing")

    try:
        parsed = urlparse(normalized_value)
        reference = urlparse(reference_url or "")
        parsed_host = parsed.hostname
        parsed_port = parsed.port
        reference_host = reference.hostname
        reference_port = reference.port
    except ValueError:
        return LandingPageIdentity(status="invalid")
    if parsed.scheme and parsed.scheme.casefold() not in {"http", "https"}:
        return LandingPageIdentity(status="invalid")
    if parsed.username or parsed.password:
        return LandingPageIdentity(status="invalid")

    path_only = not bool(parsed.netloc)
    normalized_scheme_value = (parsed.scheme or reference.scheme).casefold() or None
    if normalized_scheme_value not in {"http", "https", None}:
        return LandingPageIdentity(status="invalid")
    normalized_scheme = cast(
        Literal["http", "https"] | None,
        normalized_scheme_value,
    )
    raw_host = parsed_host.casefold().rstrip(".") if parsed_host else None
    if raw_host is None and reference_host:
        raw_host = reference_host.casefold().rstrip(".")
    if raw_host is None and not parsed.path.startswith("/"):
        return LandingPageIdentity(status="invalid")
    if raw_host and normalized_scheme is None:
        return LandingPageIdentity(status="invalid")

    normalized_host = _HOST_ALIASES.get(raw_host, raw_host) if raw_host else None
    explicit_port = parsed_port if parsed.netloc else reference_port
    normalized_port = explicit_port or _default_port(normalized_scheme)
    host_alias_applied = bool(raw_host and normalized_host != raw_host)
    normalized_path = parsed.path.rstrip("/") or "/"
    if not normalized_path.startswith("/"):
        return LandingPageIdentity(status="invalid")

    functional_pairs: list[tuple[str, str]] = []
    removed_tracking_parameters: list[str] = []
    for name, parameter_value in parse_qsl(parsed.query, keep_blank_values=True):
        if _is_tracking_parameter(name):
            removed_tracking_parameters.append(name)
        else:
            functional_pairs.append((name, parameter_value))
    functional_query = urlencode(functional_pairs, doseq=True) or None
    removed_tracking_parameters = list(
        dict.fromkeys(sorted(name.casefold() for name in removed_tracking_parameters))
    )

    if normalized_host:
        default_port = _default_port(normalized_scheme)
        port_suffix = (
            f":{normalized_port}"
            if normalized_port is not None and normalized_port != default_port
            else ""
        )
        canonical_url = (
            f"{normalized_scheme}://{normalized_host}{port_suffix}{normalized_path}"
        )
    else:
        canonical_url = normalized_path
    if functional_query:
        canonical_url = f"{canonical_url}?{functional_query}"

    return LandingPageIdentity(
        status="resolved",
        canonical_url=canonical_url,
        normalized_scheme=normalized_scheme,
        normalized_host=normalized_host,
        normalized_port=normalized_port,
        normalized_path=normalized_path,
        functional_query=functional_query,
        removed_tracking_parameters=removed_tracking_parameters,
        host_alias_applied=host_alias_applied,
        path_only=path_only,
    )


def match_landing_page(
    expected_url: str | None,
    candidate: LandingPageCandidate,
) -> LandingPageCandidateMatch:
    expected = build_landing_page_identity(expected_url)
    identity = build_landing_page_identity(candidate.url, reference_url=expected_url)
    if expected.status != "resolved" or identity.status == "missing":
        return _candidate_match(candidate.candidate_id, "missing", False, True, identity)
    if identity.status != "resolved":
        return _candidate_match(candidate.candidate_id, "no_match", False, True, identity)
    if (
        expected.normalized_scheme != identity.normalized_scheme
        or expected.normalized_host != identity.normalized_host
        or expected.normalized_port != identity.normalized_port
        or expected.normalized_path != identity.normalized_path
    ):
        return _candidate_match(candidate.candidate_id, "no_match", False, False, identity)
    if expected.functional_query != identity.functional_query:
        return _candidate_match(
            candidate.candidate_id,
            "functional_query",
            False,
            True,
            identity,
        )
    if identity.path_only:
        return _candidate_match(candidate.candidate_id, "path_only", False, True, identity)
    if expected.host_alias_applied or identity.host_alias_applied:
        return _candidate_match(candidate.candidate_id, "host_alias", True, False, identity)
    if (
        expected.removed_tracking_parameters
        or identity.removed_tracking_parameters
    ):
        return _candidate_match(
            candidate.candidate_id,
            "tracking_only",
            True,
            False,
            identity,
        )
    return _candidate_match(candidate.candidate_id, "exact", True, False, identity)


def resolve_landing_page_candidates(
    expected_url: str | None,
    candidates: Iterable[LandingPageCandidate],
) -> LandingPageResolution:
    expected = build_landing_page_identity(expected_url)
    matches = [match_landing_page(expected_url, candidate) for candidate in candidates]
    matched_ids = [match.candidate_id for match in matches if match.matched]
    if expected.status != "resolved" or not matches:
        return LandingPageResolution(
            expected_identity=expected,
            tier="missing",
            matched_candidate_ids=matched_ids,
            review_required=True,
            candidates=matches,
        )
    if len(matched_ids) > 1:
        return LandingPageResolution(
            expected_identity=expected,
            tier="ambiguous",
            matched_candidate_ids=matched_ids,
            review_required=True,
            candidates=matches,
        )
    if len(matched_ids) == 1:
        selected = next(match for match in matches if match.matched)
        return LandingPageResolution(
            expected_identity=expected,
            tier=selected.tier,
            selected_candidate_id=selected.candidate_id,
            matched_candidate_ids=matched_ids,
            review_required=selected.review_required,
            candidates=matches,
        )
    if matches and all(match.tier == "missing" for match in matches):
        return LandingPageResolution(
            expected_identity=expected,
            tier="missing",
            matched_candidate_ids=[],
            review_required=True,
            candidates=matches,
        )
    functional_query_match = next(
        (match for match in matches if match.tier == "functional_query"),
        None,
    )
    tier: LandingMatchTier = "functional_query" if functional_query_match else "no_match"
    return LandingPageResolution(
        expected_identity=expected,
        tier=tier,
        matched_candidate_ids=[],
        review_required=bool(functional_query_match),
        candidates=matches,
    )


def landing_page_metric_lookup_urls(value: str | None) -> list[str]:
    identity = build_landing_page_identity(value)
    if (
        identity.status != "resolved"
        or not identity.normalized_scheme
        or not identity.normalized_host
        or not identity.normalized_path
    ):
        return []
    hosts = _CANONICAL_HOST_LOOKUP_ALIASES.get(
        identity.normalized_host,
        [identity.normalized_host],
    )
    default_port = _default_port(identity.normalized_scheme)
    port_suffix = (
        f":{identity.normalized_port}"
        if identity.normalized_port is not None
        and identity.normalized_port != default_port
        else ""
    )
    return [
        f"{identity.normalized_scheme}://{host}{port_suffix}{identity.normalized_path}"
        for host in hosts
    ]


def _candidate_match(
    candidate_id: str,
    tier: LandingMatchTier,
    matched: bool,
    review_required: bool,
    identity: LandingPageIdentity,
) -> LandingPageCandidateMatch:
    return LandingPageCandidateMatch(
        candidate_id=candidate_id,
        tier=tier,
        matched=matched,
        review_required=review_required,
        identity=identity,
    )


def _is_tracking_parameter(name: str) -> bool:
    normalized = name.casefold()
    return normalized.startswith("utm_") or normalized in _TRACKING_PARAMETER_NAMES


def _default_port(scheme: str | None) -> int | None:
    if scheme is None:
        return None
    return {"http": 80, "https": 443}.get(scheme)
