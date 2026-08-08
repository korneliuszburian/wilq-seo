"""Compatibility facade; decomposed — see wilq/content/knowledge/service_profile/."""

import sys
from pathlib import Path
from types import ModuleType

__path__ = [str(Path(__file__).with_suffix(""))]

from wilq.content.knowledge.service_profile import claims as _claims
from wilq.content.knowledge.service_profile import contracts as _contracts
from wilq.content.knowledge.service_profile import core as _core
from wilq.content.knowledge.service_profile import review as _review
from wilq.content.knowledge.service_profile import shared as _shared
from wilq.content.knowledge.service_profile.contracts import (  # noqa: F401
    ContentServiceProfileApprovalReadiness,
    ContentServiceProfileApprovalReadinessItem,
    ContentServiceProfileCoverageGap,
    ContentServiceProfileCoverageSummary,
    ContentServiceProfilePolicySection,
    ContentServiceProfilePrivateReviewQueueItem,
    ContentServiceProfilePrivateReviewValue,
    ContentServiceProfilePrivateSourceProposalSection,
    ContentServiceProfilePrivateSourceProposalSummary,
    ContentServiceProfileResponse,
    ContentServiceProfileReviewAction,
    ContentServiceProfileReviewActionSummary,
    ContentServiceProfileReviewPolicy,
    ContentServiceProfileReviewQueueItem,
    ContentServiceProfileReviewRequirement,
    ContentServiceProfileServiceSection,
    ContentServiceProfileSourceFactCoverageAudit,
    ContentServiceProfileTechnicalTrace,
    ServiceProfileApprovalReadinessStatus,
    ServiceProfileGapSeverity,
    ServiceProfileNeededSourceType,
    ServiceProfilePrivateProposalRiskTier,
    ServiceProfilePrivateProposalSupportLevel,
    ServiceProfileReviewActionMode,
    ServiceProfileReviewActionPriority,
    ServiceProfileReviewActionScope,
    ServiceProfileReviewDecisionOption,
    ServiceProfileReviewRequirementType,
)
from wilq.content.knowledge.service_profile.core import (  # noqa: F401
    content_service_profile_response,
)
from wilq.content.knowledge.service_profile.review import (  # noqa: F401
    _review_action_summary,
)

__all__ = [
    "ContentServiceProfileApprovalReadiness",
    "ContentServiceProfileApprovalReadinessItem",
    "ContentServiceProfileCoverageGap",
    "ContentServiceProfileCoverageSummary",
    "ContentServiceProfilePolicySection",
    "ContentServiceProfilePrivateReviewQueueItem",
    "ContentServiceProfilePrivateReviewValue",
    "ContentServiceProfilePrivateSourceProposalSection",
    "ContentServiceProfilePrivateSourceProposalSummary",
    "ContentServiceProfileResponse",
    "ContentServiceProfileReviewAction",
    "ContentServiceProfileReviewActionSummary",
    "ContentServiceProfileReviewPolicy",
    "ContentServiceProfileReviewQueueItem",
    "ContentServiceProfileReviewRequirement",
    "ContentServiceProfileServiceSection",
    "ContentServiceProfileSourceFactCoverageAudit",
    "ContentServiceProfileTechnicalTrace",
    "ServiceProfileApprovalReadinessStatus",
    "ServiceProfileGapSeverity",
    "ServiceProfileNeededSourceType",
    "ServiceProfilePrivateProposalRiskTier",
    "ServiceProfilePrivateProposalSupportLevel",
    "ServiceProfileReviewActionMode",
    "ServiceProfileReviewActionPriority",
    "ServiceProfileReviewActionScope",
    "ServiceProfileReviewDecisionOption",
    "ServiceProfileReviewRequirementType",
    "content_service_profile_response",
]

_FORWARD_TARGETS = (
    _claims,
    _contracts,
    _core,
    _review,
    _shared,
)


class _Facade(ModuleType):
    """Forward legacy monkeypatch targets to their decomposed owners."""

    def __setattr__(self, name: str, value: object) -> None:
        super().__setattr__(name, value)
        for target in _FORWARD_TARGETS:
            if hasattr(target, name):
                setattr(target, name, value)


sys.modules[__name__].__class__ = _Facade
