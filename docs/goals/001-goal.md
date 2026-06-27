# Goal 001 - Clean Product Semantics And Marketer Cockpit

Status: active

Date: 2026-06-27

## Objective

Clean WILQ's active product semantics and marketer-facing surfaces before
starting the next product layer.

The goal is not to finish the full WILQ Marketing Operating System. The goal is
to make the current review cockpit coherent, condensed and usable enough that
Wilku can inspect it without reading technical internals.

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
- No React string replacement as product cleanup.
- No route-local translators, stale compatibility aliases or hardcoded cleanup
  helpers for marketer-facing semantics.
- Dirty marketer-facing copy must be fixed in typed API/schema/view-model/domain
  source.

## Current State

- Core route path remains:
  `/command-center -> /merchant -> /content-planner -> /ads-doctor -> /ga4`.
- Current cleanup has already moved many Command Center, Content, Ads, GA4,
  Merchant, Localo, Ahrefs and Action Detail labels from dashboard helpers into
  API/domain/shared-schema labels.
- The latest committed code slice is:
  `6497044 fix(ads): source negative keyword labels from api`.
- That slice added API-owned negative-keyword labels for safety, validation,
  required checks, match type, exclusion level and keyword context, with focused
  API/dashboard tests and live browser proof.
- The current verified Ads recommendation/keyword-context cleanup removes raw
  recommendation enum summaries, mixed English/Polish recommendation-review
  wording, raw keyword match/status rendering and fixed English shorthand
  labels.
- Recovery docs are being condensed because long append-only progress logs made
  the active goal harder to resume.

## Active Findings

Use these as the next work queue. Do not start future product layers until these
are resolved or explicitly deferred.

1. Ads Doctor still has route-local raw-key fallback debt in secondary helper
   paths. These should disappear as API labels cover the remaining panels.
2. Merchant first-screen and expanded panels still expose raw connector/evidence
   and contract language:
   - source connector IDs
   - evidence IDs on the primary decision screen
   - `Obecne kontrakty`, `Potrzebne kontrakty`, `Klucze połączenia danych`
   - `API gotowe do zapisu`.
3. GA4 still exposes some implementation language:
   - `(not set)`
   - `tracking-gap`
   - evidence counts as `ID`.
4. Localo still exposes protocol/credential language in visible proof panels:
   - `OAuth code`
   - `PKCE S256`
   - `Token`
   - raw `localo` connector ID.
5. Action impact and detail panels still have raw connector/evidence fallback
   risk:
   - impact result source connectors
   - missing label fallback copy.
6. `PLAN.md`, `PLANS.md`, `docs/PROGRESS.md` and `docs/CONTEXT.md` must stay
   short and aligned. History belongs in git and proof artifacts, not active
   recovery docs.

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

- Active docs agree on the corrected product model.
- Active product paths no longer depend on dev-site migration semantics.
- Primary marketer surfaces no longer show forbidden technical jargon.
- UI translators/string replacement cleanup helpers are removed or proven
  out-of-scope internal utilities.
- Focused API/dashboard/skill checks pass for all touched slices.
- Browser proof verifies touched marketer routes.
- Remaining historical mentions are archived or explicitly tracked as removal
  debt.

The final WILQ Marketing Operating System remains a later goal. It still
requires ContentPreflight, sales brief, claim ledger, sprawdzenie przez
człowieka, WordPress draft handoff, measurement loop, workspace profiles,
knowledge lifecycle and safe execution gates.
