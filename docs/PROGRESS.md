# WILQ Progress Ledger

This file is the short recovery ledger. It is not a changelog and must not
become an append-only transcript.

Full current plan: `PLAN.md`
Long-range product plan: `PLANS.md`
Active goal: `docs/goals/001-goal.md`

## Current Readout

Date: 2026-06-29

- WILQ is the system/product.
- Wilku is the human marketer/operator persona.
- Ekologus is the first depth-first workspace/client.
- `ekologus.pl` is the public canonical content home.
- Dev preview hosts are optional design/staging context only when explicitly
  configured. They are not canonical content targets and must not drive content
  decisions by default.
- WILQ API is the product brain. Dashboard and Codex skills consume typed API
  contracts, source connectors and WILQ-described evidence.
- Marketer-facing UI and skill output must use Polish operating language.
- Raw IDs, connector trace, raw payloads and audit details belong only in
  technical detail.
- Dirty copy must be fixed in typed API/schema/view-model/domain source, not
  with React translators, string replacement helpers or stale label maps.
- Do not preserve deprecated active fields, compatibility aliases or stale
  dev-preview/migration semantics when direct migration is feasible.

## Live Connector State

Live API check on 2026-06-29:

- WILQ API health: `ok`.
- Google Search Console: configured, fresh, no missing credentials.
- Google Analytics 4: configured, fresh, no missing credentials.
- Google Merchant Center: configured, fresh, no missing credentials.
- Google Ads, Ahrefs, Localo and WordPress are configured.
- LinkedIn and Facebook credentials are missing; social remains later scope.
- Google Sheets is intentionally disabled for the current operator scope.

Do not reopen old WSL credential recovery for GSC, GA4 or Merchant unless live
API status later contradicts this state.

## Latest Verified Product State

- `App.tsx` route composition uses a dedicated route renderer map. Focused
  dashboard tests, typecheck, lint, Fallow audit/health, language guards,
  `git diff --check` and browser proof for `/merchant`, `/content-planner` and
  `/settings` passed. Fallow still lists `App.tsx` as a historical hotspot due
  to churn, but there are no current high-confidence refactoring targets.
- `App.test.tsx` mock API routing is split into focused endpoint handlers.
  Fallow no longer reports it as a current high-confidence refactoring target.
- `OperatingRouteSurfaces.tsx` and `GenericSurface.tsx` are split into focused
  sections. `/workflows` renders the main process decision surface before
  secondary process-run history is required.
- Dashboard patch/minor dependencies are current where no framework migration
  was required: `@tanstack/react-query@5.101.2`,
  `@playwright/test@1.61.1`, `postcss@8.5.16` and
  `autoprefixer@10.5.2`.
- `lucide-react` has been upgraded to `1.22.0`. Dashboard typecheck, focused
  route tests, lint, production build, Fallow changed-file audit and browser
  proof for `/command-center` passed after the upgrade.
- `jsdom` has been upgraded to `29.1.1`. Dashboard typecheck, full dashboard
  test suite, lint, production build, Fallow changed-file audit,
  marketer/context-pack language guards and browser proof for `/command-center`
  passed after the upgrade.
- `@types/node` has been upgraded to `26.0.1`. Workspace typecheck, full
  dashboard test suite, lint, production build, Fallow changed-file audit,
  marketer/context-pack language guards and browser proof for `/command-center`
  passed after the upgrade.
- The remaining outdated JS packages are major migrations and must be handled
  as separate verified slices: Vite, Vitest, Zod, Tailwind,
  `@vitejs/plugin-react` and TypeScript.
- Fallow is wired through `.fallowrc.json` and root package scripts. Dead-code
  and dependency hygiene are clean; full structural cleanup still has inherited
  dashboard duplication and complexity debt.
- Active dashboard/API/skill cleanup removed the worst slash-combined labels,
  stale dev-preview placement semantics, a hybrid Merchant sample-readiness
  field, misleading review wording, raw route slugs in action reasons and
  technical registry fallback language from primary surfaces.
- `scripts/live_contract_smoke.py` guards live content diagnostics against
  stale dev-preview URL and migration-era semantics.

## Current Blockers And Deferred Work

- Real marketer UAT with Wilku/Ekologus is still not complete. This is the main
  non-technical blocker before claiming the current cockpit is done for humans.
- Major JS dependency migrations are separate product-safe slices, not cleanup
  drive-by changes.
- Full Marketing OS layers remain later milestones unless explicitly promoted:
  workspace contracts, full content preflight, sales brief, claim review, human
  review, WordPress draft handoff, measurement loop, broader write/apply
  adapters and multi-client/agency UI.
- Social connectors are missing credentials and remain out of current core
  proof.
- Localo has access proof and guarded read data. Do not claim ranking, GBP,
  write or uplift behavior without explicit WILQ evidence.

## Next Queue

1. Run real marketer UAT or record explicit owner defer.
2. Continue active surface audits from current Fallow hotspots only when they
   affect marketer UX, product semantics or guardrails.
3. Take major dependency migrations one at a time with focused migration notes
   and verification.
4. Keep `PLAN.md`, `PLANS.md`, `docs/goals/001-goal.md`, `docs/CONTEXT.md` and
   this file pruned after every meaningful slice.
5. Before broad completion claims, run focused checks plus `scripts/verify.sh`.

## Recent Verification Commands

- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk pnpm --filter @wilq/dashboard test -- App.test.tsx --runInBand`
- `rtk pnpm --dir apps/dashboard lint`
- `rtk pnpm --dir apps/dashboard build`
- `rtk pnpm fallow:audit --format compact --no-cache`
- `rtk pnpm fallow health --hotspots --targets --format compact --no-cache`
- `rtk uv run python scripts/marketer_language_guard.py`
- `rtk uv run python scripts/context_pack_language_guard.py --api-base http://127.0.0.1:8000`
- browser proof with `agent-browser` for touched routes
- `rtk git diff --check`

## Recovery Rule

Older proof history is intentionally omitted from this recovery ledger. Use git
history and `.local-lab/proof/` when older evidence is needed. When adding new
status, remove or replace outdated lines instead of appending a new history
block.
