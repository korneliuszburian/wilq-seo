# Goal 001 - Clean Product Semantics And Marketer Cockpit

Status: active

Date: 2026-06-28

## Objective

Clean WILQ's active product semantics and marketer-facing surfaces before
starting the next product layer.

This goal does not finish the full WILQ Marketing Operating System. It makes
the current review cockpit coherent, condensed and usable enough that Wilku can
inspect it without reading technical internals.

## Identity

- WILQ = system/product.
- Wilku = human marketer/operator persona.
- Ekologus = first depth-first workspace/client.
- `ekologus.pl` = public canonical content home.
- Dev preview hosts = optional design/staging context only when explicitly
  configured for a workflow.

## Product Rules

- No evidence ID -> no recommendation.
- No source connector -> no recommendation.
- No preflight verdict -> no writing.
- No sales brief -> no draft.
- No claim review -> no publish-ready language.
- Brak sprawdzenia przez człowieka -> brak WordPress draft handoff.
- No audit -> no zapis zmian.
- No measurement window -> no success/failure claim.
- No business logic in prompts or skill references.
- No React/UI translator functions, `replaceAll` helpers or route-local
  dictionaries for product semantics.
- No compatibility aliases or deprecated active fields when a direct migration
  is feasible.
- Remove stale target/dev/migration semantics from active contracts.
- Dirty marketer-facing copy must be fixed in typed API/schema/view-model/domain
  source.
- Raw IDs may appear in technical panels, audit detail and trace views only.
- Every repeated issue becomes a typed API/schema/view-model field or a test
  guard.

## Current Cleanup Language

Active marketer language is being normalized as:

- `Command Center` -> `Centrum pracy`.
- `Content Planner` -> `Treści` / widok treści.
- `Ads Doctor` -> `Google Ads` / widok Google Ads.
- `blockery` -> `blokady`.
- `evidence IDs` -> dowody opisane w WILQ.

Dashboard paths may keep existing technical route slugs during this goal, but
primary navigation, headings, summaries, skill output and recovery docs should
use the cleaned language.

## Current State

- Cleanup has already moved many Ads, Merchant, GA4, Localo, Ahrefs,
  Knowledge, Brief Workflow, tactical queue and Action Detail labels from
  dashboard helpers into API/domain/shared-schema fields.
- Touched marketer surfaces now avoid raw evidence/action/connector IDs,
  endpoint names, raw enum keys, old dev-site mapping wording and English
  validation copy in normal UI.
- Action Detail normal preview renders typed API preview cards only. Raw action
  payloads remain available only behind the collapsed technical detail panel.
- Demand Gen diagnostics expose typed API preview cards; the route no longer
  builds its primary preview from raw `payload_preview` shape.
- Generic status routes, Demand Gen, Merchant, GA4, Ads, Content and custom
  segment first-screen labels have been tightened to marketer-readable Polish.
- Legacy raw audit summaries are no longer cleaned by string replacement
  helpers; raw historical summaries collapse to a neutral audit note.
- Ahrefs/content public contracts now use `referenced_public_url`; active
  diagnostics, source facts, tactical queue and WordPress draft handoff no
  longer expose or fall back to `target_url`.
- Knowledge operating map now carries API-owned labels for source connectors,
  evidence summaries, missing data and blocked claims, so the Knowledge route
  does not show playbook refusal rules or raw connector IDs on the first screen.
- Knowledge playbooks now expose Polish source rules and output contracts. Live
  `/api/knowledge/playbooks` proof shows no `Refuse`, `Evidence-backed`,
  `payload`, `connectora` or `query/page` residue in the playbook contract.
- UAT packet/result scripts now use marketer-facing Polish route names and
  markdown labels. Live packet proof shows no `Command Center`,
  `Content Planner`, `Ads Doctor`, `dev preview`, `Route`, `Pass` or `Fail`
  residue in the exported UAT packet.
- Ahrefs visible copy now uses `dowody`, `SEO i treści`, `linki zwrotne`,
  `widok Treści` and `organiczne słowa dla URL`; live Ahrefs API/browser proof
  shows no `Ahrefs evidence`, `SEO/content`, `backlinków` or `per URL` residue.
- Custom Segments candidates now expose API-owned preview cards and rejection
  reason labels. The dashboard route no longer derives the visible segment card
  from `candidate.payload_preview`.
- GA4 full review now renders API-owned action preview cards and no longer
  parses `action.payload.payload_preview` for the review card.
- Recovery docs are being kept short because append-only progress logs made the
  active goal harder to resume.

## Active Findings

Use these as the next work queue. Do not start future product layers until these
are resolved or explicitly deferred.

1. Keep `PLAN.md`, `PLANS.md`, `docs/PROGRESS.md` and this file short and
   aligned.
2. Remove scattered raw fallback paths in registry/workflow and knowledge
   routes by adding typed API/schema/view-model labels.
3. Continue moving repeated metric, dimension, source, blocker and evidence
   naming into API/domain labels. Pure numeric formatting can stay in UI.

## Execution Policy

- Use `rtk` before every shell command.
- Inspect existing implementation before editing.
- Prefer small verified slices and conventional commits.
- Use subagents for parallel read-only audits or disjoint write scopes.
- Do not let multiple workers edit the same files without explicit ownership.
- After each slice:
  - run focused tests,
  - capture browser/API proof when a marketer route changes,
  - update only current recovery facts,
  - commit and push a coherent green slice.

## Verification

Focused checks:

- Docs-only: `rtk git diff --check`.
- API/schema/action: focused `rtk uv run pytest ...`.
- Dashboard: touched route test plus `rtk pnpm --dir apps/dashboard typecheck`.
- Skill changes: deterministic smoke and targeted eval.
- Marketer copy: `rtk uv run python scripts/marketer_language_guard.py`.
- Browser: `agent-browser` snapshot for touched marketer routes.

Broad checks:

- `rtk scripts/verify.sh` before cross-surface completion claims.

## Completion Definition

Goal 001 is complete when:

- Active docs agree on the corrected product model and cleaned language.
- Active product paths no longer depend on dev-site migration semantics.
- Primary marketer surfaces no longer show forbidden technical jargon.
- UI translators/string replacement cleanup helpers are removed or proven
  out-of-scope internal utilities.
- Deprecated active fields and compatibility aliases are removed where direct
  migration is feasible.
- Focused API/dashboard/skill checks pass for all touched slices.
- Browser proof verifies touched marketer routes.
- Remaining historical mentions are archived or explicitly tracked as removal
  debt.

The final WILQ Marketing Operating System remains a later goal. It still
requires ContentPreflight, sales brief, claim ledger, sprawdzenie przez
człowieka, WordPress draft handoff, measurement loop, workspace profiles,
knowledge lifecycle and safe execution gates.
