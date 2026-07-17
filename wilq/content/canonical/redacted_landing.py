from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Literal
from urllib.parse import parse_qsl

from wilq.content.canonical.landing_identity import build_landing_page_identity

RedactedLandingStatus = Literal["resolved", "missing", "invalid", "sensitive"]
_SENSITIVE_QUERY_NAMES = {
    "accesskey",
    "accesskeyid",
    "accesstoken",
    "apikey",
    "authcode",
    "assertion",
    "authorization",
    "authorizationcode",
    "authtoken",
    "clientsecret",
    "code",
    "credential",
    "credentials",
    "email",
    "jwt",
    "nonce",
    "password",
    "oauthcode",
    "phone",
    "samlresponse",
    "secret",
    "session",
    "sessionid",
    "sid",
    "signature",
    "sso",
    "state",
    "ticket",
    "token",
    "xamzcredential",
    "xamzsecuritytoken",
    "xamzsignature",
}
_SENSITIVE_QUERY_SUFFIXES = (
    "apikey",
    "credential",
    "email",
    "password",
    "phone",
    "secret",
    "sessionid",
    "signature",
    "token",
)


@dataclass(frozen=True)
class RedactedLandingReference:
    status: RedactedLandingStatus
    identity_sha256: str | None = None
    tracking_parameters_removed: bool = False
    has_functional_query: bool = False


def build_redacted_landing_reference(value: str | None) -> RedactedLandingReference:
    identity = build_landing_page_identity(value)
    if identity.status == "missing":
        return RedactedLandingReference(status="missing")
    if identity.status != "resolved" or not identity.canonical_url:
        return RedactedLandingReference(status="invalid")
    functional_names = [
        name for name, _ in parse_qsl(identity.functional_query or "", keep_blank_values=True)
    ]
    if any(_query_name_is_sensitive(name) for name in functional_names):
        return RedactedLandingReference(status="sensitive")
    return RedactedLandingReference(
        status="resolved",
        identity_sha256=hashlib.sha256(identity.canonical_url.encode("utf-8")).hexdigest(),
        tracking_parameters_removed=bool(identity.removed_tracking_parameters),
        has_functional_query=bool(identity.functional_query),
    )


def _query_name_is_sensitive(name: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", name.casefold())
    return normalized in _SENSITIVE_QUERY_NAMES or normalized.endswith(
        _SENSITIVE_QUERY_SUFFIXES
    )
