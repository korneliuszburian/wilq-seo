# WILQ Private Source Proposal Protocol

Date: 2026-07-01
Status: design, not implemented
Related Beads task: `wilq-seo-wtf`
Input audit:
`docs/audits/005-2026-07-01-ekologus-brain-source-catalog-audit.md`

## Purpose

Private Ekologus materials can help WILQ become less generic, but only if they
enter the system as reviewed source proposals. This protocol defines the safe
path from a private source catalog to WILQ source facts without committing raw
client content, full paths, filenames, emails, phone numbers or protected
snippets.

This is not a RAG bridge. WILQ API remains the product brain. Private source
proposals are local/redacted review artifacts that may later be promoted into
typed source facts.

## Pipeline

```text
metadata-only catalog
-> owner/audience/risk decision
-> local-only extraction for approved candidates
-> schema-gated condensation
-> private source proposal
-> owner/Wilku review
-> reviewed source fact
-> compiled knowledge card when lifecycle allows it
-> Service Profile display / content workflow use
```

Every step is fail-closed. A proposal can support review and UAT, but it must
not unlock `approved_current`, production-depth cards or daily content readiness
until a WILQ review path promotes it.

## Proposal Shape

Recommended local schema name:
`PrivateSourceProposal`.

Required fields:

| Field | Meaning |
| --- | --- |
| `proposal_id` | Stable local ID for the proposal artifact. |
| `source_id` | Sanitized source class or reviewed source ID. |
| `source_type` | `private_candidate` until approved; `reviewed_internal` after review. |
| `privacy_class` | Default `redacted_only`; use `private_local` for local-only artifacts. |
| `source_locator_label` | Redacted label, never full path or filename. |
| `derived_fact` | Sanitized fact candidate, no raw excerpts. |
| `scope` | Existing WILQ scope: `service`, `buyer_problem`, `cta`, `claim_policy`, `evidence_requirement` or `metric_signal`. |
| `freshness_date` | Date the private proposal was reviewed or extracted. |
| `freshness_status` | `current`, `historical`, `stale` or `unknown`. |
| `confidence` | 0-1 confidence in the sanitized derived fact. |
| `review_status` | Default `review_required`; later `approved`, `rejected` or `stale`. |
| `reviewer` | Required only for `approved`. |
| `owner_role` | Role that can approve the source class. |
| `audience` | `company_wide`, `department_only`, `role_restricted`, `owner_only` or `unknown`. |
| `risk_tier` | `low`, `medium`, `high` or `unknown`. |
| `data_classes` | Classes such as internal operational, training, technical domain, client/project, legal/expert opinion. |
| `source_block_refs` | Sanitized block IDs, not paths or excerpts. |
| `support_level` | `direct`, `partial`, `background` or `conflicting`. |
| `target_card_id` | Existing or proposed WILQ knowledge card ID. |
| `target_card_type` | Existing WILQ card type. |
| `service_fit_terms` | Sanitized matching terms, if scope supports them. |
| `buyer_problem_terms` | Sanitized buyer-problem terms, if applicable. |
| `buyer_triggers` | Sanitized triggers, if applicable. |
| `cta_patterns` | Safe CTA patterns, if reviewed. |
| `allowed_claims` | Claims allowed only with evidence and review status. |
| `blocked_claims` | Claims that must be blocked or human-reviewed. |
| `evidence_requirements` | Required live connector/evidence conditions. |
| `retention_decision` | `pending_owner_decision`, `retain_while_source_approved`, `short_window_only` or `do_not_retain`. |
| `deletion_path` | Operator actions to delete proposal/local derived artifacts. |
| `eval_case_ids` | Eval cases that must pass before promotion. |

Forbidden fields:

- raw document text;
- direct quotes from private documents;
- full local or remote paths;
- filenames;
- email addresses;
- phone numbers;
- credential names or credential paths;
- client names from protected case files unless owner-approved and redacted;
- raw spreadsheets, rows or cell values;
- OCR text;
- model prompts/responses containing protected data.

## Mapping To `ContentSourceFact`

Promotion to `ContentSourceFact` is only allowed after review.

Default mapping before approval:

```text
source_type      = private_candidate
privacy_class    = redacted_only or private_local
review_status    = review_required
reviewer         = null
evidence_ids     = []
source_connectors = ["private_source_proposal"]
```

Approved reviewed internal mapping:

```text
source_type      = reviewed_internal
privacy_class    = redacted_only unless explicitly commit_safe
review_status    = approved
reviewer         = human reviewer ID or role
source_connectors = ["reviewed_internal"]
```

Even after approval, live content recommendations still need normal WILQ
evidence IDs and source connectors. A reviewed internal fact may prove service
fit or claim policy; it does not prove GSC, GA4, Ads, Merchant, WordPress or
measurement behavior.

## Lifecycle Rules

- `private_candidate + review_required` may support analysis, UAT questions and
  ordinary handoff markdown.
- `private_candidate + review_required` must not compile into commit-safe
  production-depth knowledge cards.
- `reviewed_internal + approved` may compile into `approved_current` only when
  the WILQ review/audit path records reviewer, freshness and blocked claims.
- `stale` private proposals can be shown in Service Profile as coverage history
  but cannot unlock daily content readiness.
- `rejected` proposals must not match work items or appear as usable cards.
- Legal, penalty, environmental-obligation, product, current-law and
  measurement claims remain human-review gated even when source fit is approved.

## Service Profile Display

The read-only Service Profile can display private proposal coverage without
exposing protected content.

Allowed display:

- sanitized `source_id`;
- source class label;
- scope;
- lifecycle/review status;
- freshness status/date;
- owner role;
- audience;
- risk tier;
- target card ID/title;
- blocked claim labels;
- coverage gap labels;
- safe next step: review, refresh, reject, approve or request source.

Forbidden display:

- raw fact text if it contains protected details;
- full path/filename;
- private snippets;
- contact data;
- client file contents;
- credential source details;
- unredacted legal opinion text.

## Eval Requirements

Before a private proposal can influence production-depth readiness, run focused
evals that prove:

1. `review_required` proposals do not unlock `approved_current`.
2. Broad service terms do not overmatch unrelated services.
3. A draft claim outside the claim ledger is blocked.
4. Legal/current-law/penalty/product claims require human review.
5. Stale proposals remain visible as stale but cannot unlock daily readiness.
6. Operator-facing output cites only sanitized IDs/labels and never raw private
   paths, filenames or snippets.

Non-interactive Codex skill evals should also verify that Polish operator output
mentions evidence/source limitations and the next safe step.

## Implementation Notes

Do not add this as a second knowledge endpoint before the existing WILQ content
contracts need it. The likely sequence is:

1. design read-only Service Profile view model;
2. add private proposal schema/local loader only if a local artifact exists;
3. show proposal coverage as review-required/private in Service Profile
   (implemented for two redacted `ekologus-ai` handoff candidates);
4. add promotion tests before compiling approved proposals into cards.

This keeps WILQ aligned with the BDOS-class pattern: controlled adapters and
review gates around a canonical API, not prompt-only knowledge stuffing.
