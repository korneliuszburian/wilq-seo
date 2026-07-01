# Goal 003 - Content Quality Workbench

Status: completed on 2026-07-01.

Beads epic: `wilq-seo-u6u`.

## Objective

Build the next useful WILQ content layer after Goal 002: a Polish marketer
workbench where Wilku can choose from multiple real Ekologus content candidates,
generate a gated structured draft, run deterministic quality review, receive an
evidence-bound revision plan and prepare draft-only WordPress output without
SEO slop, prompt-only product logic or live publication.

## Current Baseline

Goal 002 is complete. WILQ already proves one diagnostics-derived Ekologus
content item can pass:

```text
evidence IDs
-> source connectors
-> inventory/canonical resolution
-> duplicate check
-> preflight verdict
-> preserve-first plan
-> sales brief
-> claim gate
-> draft package
-> human review
-> audit
-> WordPress draft-only handoff/execution dry-run
-> measurement window
```

Primary completion proof:

- `tests/content/test_content_workflow_end_to_end.py`
- `docs/handoffs/2026-06-30-goal-002-completion-audit.md`

Goal 003 must not weaken any Goal 002 gate.

## Outcome

Goal 003 is done when WILQ can support a small real content workflow for
Ekologus:

1. WILQ API exposes a multi-item content queue derived from existing diagnostics
   and evidence sources.
2. Wilku can select a candidate and see why WILQ recommends preserve, refresh,
   merge, create or block.
3. Structured draft generation can run live only after WILQ gates pass and the
   live SDK path is explicitly enabled.
4. The generated draft remains typed, evidence-mapped and `publish_ready=false`.
5. WILQ runs deterministic quality review before human review.
6. WILQ produces evidence-bound revision instructions when the draft needs
   changes.
7. Human Review and audit remain required before WordPress draft handoff.
8. WordPress remains draft-only or dry-run; no live publish and no destructive
   update.
9. Measurement window exists before any outcome interpretation.
10. Adversarial evals prove the main gates cannot be skipped.

## Completion Proof

Goal 003 is complete against the scope above. The closing implementation slices
were committed and pushed as:

- `e38add2f` - adversarial content workflow gates.
- `71c92731` - per-item persisted content workflow state.
- `f5ad6d38` - changed-code anti-slop complexity budgets.

Focused verification passed:

```bash
rtk uv run pytest tests/content -q
rtk uv run pytest tests/test_audit_complexity.py -q
rtk pnpm -C apps/dashboard exec vitest run src/routes/ContentWorkflowSurface.test.tsx
rtk pnpm --filter @wilq/dashboard lint
rtk pnpm -C apps/dashboard typecheck
rtk pnpm fallow:audit
rtk uv run python scripts/audit_complexity.py --changed --limit 5
rtk git diff --check
```

`rtk scripts/verify.sh` was attempted during closure. It failed before
Goal-003-specific gates on the known legacy full-Ruff baseline
(`E501`/`UP037` in historical files such as `tests/test_api_contracts.py`,
`wilq/briefing/command_center.py`, `wilq/briefing/merchant_diagnostics.py`,
`wilq/briefing/marketing_brief.py` and `wilq/schemas.py`). Follow-up Beads task
`wilq-seo-8re` tracks restoring the full repo-level verify gate. This is not a
Goal 003 product blocker, but it remains repo cleanup debt.

## Non-Goals

Do not build in Goal 003:

- automatic WordPress publication,
- destructive update of existing `ekologus.pl` content,
- multi-client SaaS or agency admin,
- social publishing,
- Ads, Merchant or Localo write automation,
- broad RAG/vector database,
- mass article generation,
- vague SEO score as a quality substitute,
- prompt-only content writing,
- React-owned business logic,
- deprecated aliases or compatibility fields when direct migration is feasible.

## Product Rules

- No evidence ID means no recommendation.
- No source connector means no recommendation.
- No preflight means no writing.
- No sales brief means no draft.
- No claim gate means no draft.
- No human review means no WordPress draft.
- No audit means no write/apply.
- No measurement window means no success/failure claim.
- Existing content is preserve-first.
- `ekologus.dev.proudsite.pl` is never final canonical or historical SEO
  evidence.
- WILQ API owns product decisions.
- OpenAI SDK Structured Outputs generates typed artifacts only after WILQ gates.
- Codex is for repo work, orchestration, smokes and adversarial evals, not the
  production writer.
- Dashboard renders API-owned view models in Polish marketer language.

## Required Deliverables

### A. Content Queue API

Endpoint:

```http
GET /api/content/work-items/queue
```

Each candidate must include:

- `work_item_id`
- topic/title
- recommended mode: preserve, refresh, merge, create or block
- evidence IDs
- source connectors
- `source_public_url` where relevant
- `final_canonical_url` or typed blocker
- `preview_url` only as preview context
- preflight status
- duplicate/canonical risk summary
- measurement readiness
- safe next step
- Polish marketer-facing labels and reasons

If WILQ cannot honestly derive at least three candidates, it must return typed
blockers instead of fake product behavior.

### B. Per-Item Workflow State

Persist review, audit, generated output and quality review per `work_item_id`.
A review, audit or generated output for item A must never unlock item B.

### C. Gated Live Structured Generation

Live generation requires:

- valid content work item,
- inventory/canonical/duplicate check,
- preflight,
- preserve-first plan,
- sales brief,
- claim gate,
- draft package,
- measurement plan,
- strict schema contract,
- explicit mode `live`,
- `WILQ_OPENAI_STRUCTURED_DRAFT_LIVE_ENABLED=true`,
- configured SDK client/API key.

Default mode remains dry-run or blocked. Output must keep `publish_ready=false`.

### D. Content Quality Review

Create deterministic quality review before any human approval:

```text
ContentQualityReview
- review_id
- work_item_id
- draft_id
- verdict: blocked | needs_changes | reviewable | ready_for_human_review
- evidence_coverage
- claim_safety
- duplicate_risk
- usefulness
- service_fit
- search_intent_fit
- buyer_problem_fit
- cta_quality
- factual_precision
- polish_language_quality
- internal_link_fit
- measurement_readiness
- blockers
- revision_instructions
- evidence_ids
- source_connectors
```

Start deterministic and schema-based. Do not start with an LLM judge.

### E. Revision Plan

Turn quality findings into bounded revision instructions:

- affected section,
- what to change,
- why,
- required evidence IDs,
- forbidden claims to avoid,
- human review checklist additions.

Revision plan must not bypass preflight, claim gate, human review, audit or
measurement.

### F. Dashboard Workflow

`/content-workflow` must let Wilku:

- see the content queue,
- select a candidate,
- inspect gate state,
- request gated generation when allowed,
- see draft preview,
- run quality review,
- see blockers and revision instructions,
- submit human review,
- prepare draft-only WordPress dry-run,
- see measurement blocker.

React must not decide product readiness or translate raw backend states into
business meaning.

### G. Adversarial Evals

Add evals that try to break the content workflow:

- dev URL as canonical,
- missing evidence,
- missing source connector,
- generation without preflight,
- generation without sales brief,
- generation without claim gate,
- generated output with `publish_ready=true`,
- forbidden guarantee claim,
- WordPress publish request,
- success claim before measurement window,
- review for wrong work item.

## Engineering Boundaries

Frozen for new feature growth:

- `apps/api/wilq_api/main.py`
- `wilq/schemas.py`
- `wilq/actions/service.py`
- `wilq/briefing/content_diagnostics.py`
- `tests/test_api_contracts.py`
- `apps/dashboard/src/routes/ContentDiagnosticSurface.tsx`

Touch these only for thin routing, extraction, parity or required direct cleanup.
New Goal 003 behavior belongs in focused modules and focused tests.

## Verification Surface

At completion, run focused checks first and broad checks only when justified by
the changed surface:

```bash
rtk uv run pytest tests/content -q
rtk uv run ruff check <changed-python-files>
rtk uv run mypy <changed-typed-python-modules>
rtk uv run python scripts/audit_complexity.py --changed --allow-frozen
rtk pnpm --filter @wilq/dashboard typecheck
rtk pnpm --filter @wilq/dashboard lint
rtk pnpm fallow:audit
rtk git diff --check
```

Use `scripts/verify.sh` before broad completion claims or cross-surface handoff.

## Blocked Stop Conditions

Stop and record a blocker if:

- queue candidates cannot be derived without fake hardcoded product behavior,
- live generation can skip WILQ gates,
- generated output can mark itself publish-ready,
- React starts deciding business logic,
- WordPress can publish or destructively update,
- quality findings lack evidence IDs or source connectors,
- measurement outcomes are claimed before the observation window is ready,
- new feature behavior grows frozen monolith files,
- tests become marker-only theater instead of gate-breaking proof.

## First Execution Order

1. Complete recovery and plan alignment (`wilq-seo-ik5`).
2. Implement `GET /api/content/work-items/queue` (`wilq-seo-d7c`).
3. Add per-item persisted workflow state (`wilq-seo-cdy`).
4. Add deterministic quality review (`wilq-seo-b5x`).
5. Harden gated live Structured Outputs generation (`wilq-seo-8qd`).
6. Add revision plan API (`wilq-seo-56w`).
7. Extend `/content-workflow` queue and quality UI (`wilq-seo-0xv`).
8. Add adversarial content evals (`wilq-seo-0t7`).
9. Strengthen changed-code anti-slop budgets (`wilq-seo-9l1`).

Use `bd ready --json` as the authoritative operational queue.
