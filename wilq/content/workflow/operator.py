from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class ContentOperatorContext(BaseModel):
    """API-owned local-pilot label; it is not an authentication claim."""

    model_config = ConfigDict(extra="forbid")

    display_label: Literal["Wilku (lokalny pilot)"] = "Wilku (lokalny pilot)"
    request_label: Literal["operator_local_dashboard"] = "operator_local_dashboard"
    principal_id: Literal["local_operator"] = "local_operator"
    trust_level: Literal["local_unverified"] = "local_unverified"
    authentication_status: Literal["not_configured"] = "not_configured"


def content_operator_context() -> ContentOperatorContext:
    return ContentOperatorContext()
