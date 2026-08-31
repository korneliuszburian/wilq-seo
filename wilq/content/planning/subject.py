from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PlanningContentKind = Literal["service", "editorial"]


class ContentPlanningSubject(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content_kind: PlanningContentKind = "service"
    service_card_id: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def require_exact_identity(self) -> ContentPlanningSubject:
        planning_subject_key(self.content_kind, self.service_card_id)
        return self

    @property
    def subject_key(self) -> str:
        return planning_subject_key(self.content_kind, self.service_card_id)


def planning_subject_key(
    content_kind: PlanningContentKind,
    service_card_id: str | None,
) -> str:
    """Return one stable persistence identity without inventing an editorial service."""

    if content_kind == "service":
        if service_card_id is None or not service_card_id.strip():
            raise ValueError("Service planning requires an exact service identity.")
        return service_card_id.strip()
    if service_card_id is not None:
        raise ValueError("Editorial planning cannot carry a service identity.")
    return "editorial"


__all__ = ["ContentPlanningSubject", "PlanningContentKind", "planning_subject_key"]
