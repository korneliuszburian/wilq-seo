# WILQ Read-Only Service Profile Review Surface

Date: 2026-07-01
Status: implemented for read-only public cards and redacted private proposal summary
Related Beads task: `wilq-seo-94k`
Related protocol: `docs/architecture/private-source-proposal-protocol.md`

## Purpose

Wilku needs one place to inspect what WILQ thinks Ekologus can safely say
before the system generates or recommends content. The Service Profile is that
place.

The first version is read-only. It shows knowledge-card coverage, source
lineage, freshness, lifecycle status, claim rules, evidence requirements and
coverage gaps. It does not let the operator edit cards or promote private
knowledge directly.

## Product Rule

Service Profile is a review surface, not a knowledge editor.

```text
WILQ source facts/cards
-> API-owned Service Profile view model
-> dashboard read-only review
-> flag/review request
-> future reviewed promotion path
```

No React-only card logic. No skill-only corrections. No direct writes to
`source_facts.json` or compiled cards from the dashboard.

## Proposed Endpoint

```text
GET /api/content/service-profile
```

Response model:
`ContentServiceProfileResponse`.

The endpoint should be built from existing WILQ contracts:

- `content_knowledge_cards_response()`;
- `ekologus_source_fact_registry()`;
- redacted private source proposal registry for reviewed handoff candidates;
- optional content queue coverage summary.

It should not call external connectors directly. Freshness and evidence state
come from existing source-fact/card contracts.

## Response Shape

```text
workspace_id
workspace_label
generated_at
read_only
review_policy
production_depth_readiness
coverage_summary
service_sections[]
claim_policy_sections[]
evidence_policy_sections[]
private_source_proposal_summary
coverage_gaps[]
review_actions[]
technical_trace
```

### `review_policy`

Fields:

- `can_edit_cards`: always `false` in v1;
- `can_promote_facts`: always `false` in v1;
- `can_request_review`: `true`;
- `review_required_label`: Polish explanation that source-backed/review-required
  knowledge can support analysis/UAT, not final production-depth output;
- `blocked_write_reason`: direct card edits require a future human-review/audit
  ActionObject path.

### `coverage_summary`

Fields:

- `card_count`;
- `service_card_count`;
- `seeded_contract_proof_count`;
- `source_backed_review_required_count`;
- `approved_current_count`;
- `stale_count`;
- `rejected_count`;
- `private_candidate_count`;
- `missing_required_area_count`;
- `ready_for_daily_content`;
- `status_label`;
- `safe_next_step`.

### `service_sections[]`

Each section should be a marketer-readable grouping over one service card:

- `card_id`;
- `title`;
- `status`;
- `status_label`;
- `summary`;
- `source_fact_ids`;
- `source_connector_labels`;
- `source_lineage_labels`;
- `freshness_label`;
- `confidence_label`;
- `service_fit_terms`;
- `buyer_problem_terms`;
- `buyer_triggers`;
- `cta_patterns`;
- `allowed_claims`;
- `claims_needing_review`;
- `forbidden_claims`;
- `evidence_requirements`;
- `usage_notes`;
- `safe_next_step`;
- `review_request_hint`.

Do not show raw private facts. For private proposals, show only sanitized
source IDs/classes and review status.

### `coverage_gaps[]`

Coverage gap fields:

- `gap_id`;
- `area`;
- `severity`: `blocker`, `review_required`, `thin`, `stale`;
- `label`;
- `reason`;
- `needed_source_type`;
- `safe_next_step`;
- `example_work_item_ids`;

Known initial gaps from Goal 005:

- water permit / `operat wodnoprawny` has no direct service source card;
- source-backed public cards are still review-required, not production-depth;
- private/internal proposals are visible only as redacted review-required
  proposal summaries until a reviewed promotion path exists;
- Service Profile write/promotion path is intentionally absent.

### `review_actions[]`

These are not write actions. They are suggested review requests:

- `request_source_review`;
- `request_private_source_proposal`;
- `mark_source_stale_for_owner_review`;
- `request_claim_policy_review`;
- `request_service_gap_source`;

Each action should include:

- `action_id`;
- `mode`: always `prepare` or `review_request`;
- `label`;
- `reason`;
- `blocked_write_claim`;
- `required_human_role`;
- `target_card_id` or `gap_id`.

If future versions make any review action persistent, it must use a validated
ActionObject and audit event. V1 can stay non-persistent.

## Dashboard Layout

Route candidate:

```text
/service-profile
```

Navigation label:
`Profil usług`

First screen:

1. status band: "Wiedza nie jest jeszcze production-depth" or equivalent;
2. counts: approved, review-required, seeded, stale, gaps;
3. safe next step;
4. service coverage list.

Secondary panels:

- "Usługi i dopasowanie";
- "Claimy i blokady";
- "Wymagane dowody";
- "Luki do review";
- "Źródła prywatne/review-required" if proposal protocol is implemented.

Technical IDs should stay in expandable detail. Wilku-facing labels must be
Polish and explain why a state matters.

## Flag-For-Review Semantics

V1 may expose only a non-persistent review request preview. It should not mutate
knowledge state.

Allowed:

- generate a proposed review request object in the API response;
- show why the request matters;
- point to missing source/freshness/claim review;
- let Codex produce ordinary handoff markdown for Wilku.

Forbidden:

- direct dashboard edits to source facts/cards;
- setting `approved_current` from the UI;
- changing lifecycle or freshness without a review/audit path;
- storing raw private source detail in review requests;
- treating a review request or private proposal summary as approval.

## Test Plan

API tests:

- endpoint returns `read_only=true`;
- `can_edit_cards=false` and `can_promote_facts=false`;
- seeded cards appear as `seeded_contract_proof`;
- source-backed public cards appear as `source_backed_review_required`;
- no `approved_current` or `production_depth` readiness is claimed unless the
  source facts are approved;
- water-permit gap appears while no direct service card exists;
- private proposal coverage displays redacted labels only and keeps
  `approved_count=0` unless a future review/audit path approves a proposal.

Shared schema tests:

- `ContentServiceProfileResponseSchema` parses a fixture with seeded,
  review-required, stale and gap states.

Dashboard tests:

- route renders Polish status, safe next step and coverage gaps;
- no edit/promote button is visible in v1;
- technical IDs are behind detail;
- long status text does not overlap in the first screen.

Skill/non-interactive eval:

- content/operator skill can mention Service Profile gaps without inventing
  missing knowledge;
- output stays in Polish and cites evidence/source limitations.

## Implementation Sequence

1. Add backend view-model builder over existing knowledge cards.
2. Add shared Zod schema.
3. Add `getContentServiceProfile()` dashboard API helper.
4. Add dashboard route and Polish panels.
5. Add focused API/shared/dashboard tests.
6. Only after that consider persistent review-request ActionObjects.

This keeps the product useful for Wilku now while preserving the source-review
discipline needed for BDOS-class WILQ.
