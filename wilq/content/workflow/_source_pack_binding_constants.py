"""Private constants shared by source-pack implementation modules."""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Literal

from wilq.evidence.registry import (
    APPROVED_SOURCE_MATERIALS_EVIDENCE_ID,
    SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID,
)

SOURCE_FACT_REGISTRY_ID = "ekologus_source_fact_registry"
SOURCE_PACK_BINDING_RECORDED_EVENT = "content_source_pack_binding_recorded"
SOURCE_PACK_BINDING_ADAPTER = "content_source_pack_binding_store"

HEX64 = r"^[0-9a-f]{64}$"
SAFE_IDENTIFIER = r"^[a-z][a-z0-9_-]{0,239}$"
SECRET_LIKE_IDENTIFIER = re.compile(
    r"(?:^|[^A-Za-z0-9])(?:sk-[A-Za-z0-9_-]{20,}|gho_[A-Za-z0-9_]{20,}|ya29\.[A-Za-z0-9._-]{20,})",
    re.IGNORECASE,
)
MAX_RECEIPT_AGE = timedelta(days=30)
MAX_RECORDED_AT_AGE = timedelta(days=1)

# Compatibility names kept private to the split implementation modules.
_HEX64 = HEX64
_SAFE_IDENTIFIER = SAFE_IDENTIFIER
_SECRET_LIKE_IDENTIFIER = SECRET_LIKE_IDENTIFIER
_MAX_RECEIPT_AGE = MAX_RECEIPT_AGE
_MAX_RECORDED_AT_AGE = MAX_RECORDED_AT_AGE

ContentSourcePackBindingSeam = Literal[
    "source_pack_identity",
    "delivery_identity",
    "work_item_identity",
    "classification",
    "source_fact_whitelist",
    "evidence_whitelist",
    "fresh_context",
]
ContentSourcePackBindingReason = Literal[
    "source_pack_identity_missing",
    "source_pack_hash_mismatch",
    "delivery_identity_missing",
    "delivery_identity_digest_mismatch",
    "delivery_identity_blocked",
    "work_item_mismatch",
    "source_facts_missing",
    "evidence_missing",
    "evidence_not_bound",
    "evidence_set_mismatch",
    "fresh_context_missing",
    "fresh_context_mismatch",
    "fresh_context_stale",
    "source_fact_registry_mismatch",
    "source_fact_registry_stale",
    "source_fact_not_registered",
    "source_fact_not_approved",
    "source_fact_row_binding_missing",
    "source_fact_authority_invalid",
    "source_fact_authority_ambiguous",
    "source_fact_authority_mismatch",
    "source_fact_authority_stale",
    "source_fact_authority_drift",
    "source_facts_mismatch",
    "classification_current_missing",
    "classification_stale",
    "classification_identity_drift",
]

__all__ = [
    "APPROVED_SOURCE_MATERIALS_EVIDENCE_ID",
    "SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID",
    "SOURCE_FACT_REGISTRY_ID",
    "SOURCE_PACK_BINDING_RECORDED_EVENT",
    "SOURCE_PACK_BINDING_ADAPTER",
    "ContentSourcePackBindingSeam",
    "ContentSourcePackBindingReason",
    "HEX64",
    "SAFE_IDENTIFIER",
    "SECRET_LIKE_IDENTIFIER",
    "MAX_RECEIPT_AGE",
    "MAX_RECORDED_AT_AGE",
    "_HEX64",
    "_SAFE_IDENTIFIER",
    "_SECRET_LIKE_IDENTIFIER",
    "_MAX_RECEIPT_AGE",
    "_MAX_RECORDED_AT_AGE",
]
