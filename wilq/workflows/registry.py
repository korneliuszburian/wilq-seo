from __future__ import annotations

from wilq.workflows.models import Workflow, WorkflowStep

WORKFLOW_IDS = (
    "daily_command",
    "monthly_review",
    "ads_daily_check",
    "ads_monthly_review",
    "ads_changes_review",
    "ads_search_terms_ngram",
    "ads_custom_segments",
    "demand_gen_readiness",
    "gsc_content_doctor",
    "ahrefs_gap_finder",
    "localo_visibility_review",
    "merchant_feed_review",
    "ga4_data_analyst",
    "content_calendar_builder",
    "social_publishing_queue",
)


def list_workflows() -> list[Workflow]:
    return [
        Workflow(
            id=workflow_id,
            label=workflow_id.replace("_", " ").title(),
            description=(
                "Workflow definition runs against WILQ API and records evidence/action IDs."
            ),
            steps=[
                WorkflowStep(
                    id=f"{workflow_id}_context",
                    label="Fetch WILQ API context",
                    required_connectors=[],
                    output_contract="Connector status, evidence IDs, action IDs and errors.",
                )
            ],
        )
        for workflow_id in WORKFLOW_IDS
    ]
