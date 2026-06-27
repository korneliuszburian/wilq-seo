# PLAN.md - WILQ Clean Product Plan

This is the current canonical execution plan for WILQ in this checkout.

It replaces older demo and dev-preview-heavy plans. Do not recover old tasks
from git history unless the owner explicitly asks for them.

## 1. Product Identity

- WILQ = system/product.
- Wilku = human marketer/operator persona.
- Ekologus = first depth-first client workspace.
- WILQ Core must become reusable through clean workspace/profile contracts.
- Do not build multi-client SaaS, agency admin, tenant UI, billing or workspace
  switcher in this goal.

## 2. Correct Content Model

The previous direction over-weighted the dev preview host.

Correct model:

- `ekologus.pl` is the public canonical content home for Ekologus.
- `sklep.ekologus.pl` is a real product/shop source where relevant.
- A dev preview host is only optional design/staging context when the owner
  explicitly configures it for a specific workflow.
- The dev URL must not drive content decisions, canonical decisions, evidence
  selection, blocker states or default task priority.
- A redesign does not imply content migration or rewriting.
- Existing content is preserve-first: keep, refresh or merge before create.

Required URL semantics:

- `source_public_url`: current real public source URL.
- `final_canonical_url`: approved public canonical URL on the final site.
- `intended_final_url`: planned public URL when final canonical is not yet
  confirmed.
- `preview_url`: optional design/staging preview URL only.

Forbidden URL semantics:

- Do not keep stale dev-preview or migration-era content fields as a
  compatibility strategy.
- When touched active consumers still depend on stale names, migrate them in
  the same slice and add a guardrail preventing the stale contract from coming
  back.
- Historical proof folders may mention old terms, but active docs, API paths,
  dashboard copy, skill contracts and eval fixtures must not present them as
  current product logic.

## 3. Non-Negotiable Engineering Rules

- No evidence ID -> no recommendation.
- No source connector -> no recommendation.
- No preflight verdict -> no writing.
- No sales brief -> no draft.
- No claim review -> no publish-ready language.
- Brak sprawdzenia przez człowieka -> brak WordPress draft handoff.
- No audit -> no zapis zmian.
- No measurement window -> no success/failure claim.
- Do not invent metrics, facts, rankings, costs, ROAS, revenue or impact.
- Do not fix product behavior in skill references.
- Do not fix copy or semantics with React string replacement.
- Do not add route-local translators, `replaceAll` helpers, enum remappers,
  legacy label dictionaries or hardcoded cleanup functions.
- If marketer-facing copy is wrong, fix typed API/schema/view-model/domain
  source first.
- Dashboard route components render clean view-models; they do not invent
  business meaning.
- Technical IDs may exist in schemas, audit logs and technical drawers, but not
  in the marketer's primary decision surface.
- Every changed line must trace to this plan or an explicit owner request.
- Avoid broad refactors until active inconsistencies are removed and verified.

## 4. Marketer Language Rules

The marketer should see plain Polish operating language.

Preferred visible terms:

- `akcja do sprawdzenia`
- `sprawdzenie w WILQ`
- `podgląd zmian`
- `zapis zmian`
- `zatwierdzenie zmian`
- `blokada`
- `dowody`
- `źródła danych`
- `co zrobić dalej`
- `czego nie wolno obiecać`
- `co wymaga decyzji człowieka`

Forbidden visible terms:

- `kandydat zmiany`
- `payload`
- legacy English preview wording
- raw technical execution wording
- `wykonanie zmian`
- `tylko do sprawdzenia`
- legacy dev-preview placement wording
- migration-map wording
- mapping-review wording
- raw connector/debug jargon on first screen

If these terms appear in primary UI, API summaries, skill output, UAT packets or
active docs, fix the producing source and add a regression check.

## 5. Full Condensation Principle

WILQ must condense information, not dump registries.

Every marketer-facing domain surface must answer, in this order:

1. Co jest teraz najważniejsze?
2. Dlaczego to ma znaczenie?
3. Co WILQ rekomenduje zrobić?
4. Co jest zablokowane i dlaczego?
5. Jakie dowody to wspierają?
6. Jakie źródła danych są świeże albo brakujące?
7. Jaki jest następny bezpieczny krok?
8. Jak sprawdzimy efekt później?

Raw diagnostics, IDs, JSON, connector trace and audit detail go behind a
technical drawer. They remain available for operators, but are not the default
experience.

## 6. Self-Improving Rules

Every repeated issue becomes a durable rule.

When a stale term, confusing UI, false claim, bad test expectation or developer
shortcut is found:

1. Fix the source of truth, not the symptom.
2. Add the smallest guardrail that catches the issue next time:
   - schema/API assertion,
   - focused unit test,
   - dashboard route test,
   - skill smoke,
   - eval case,
   - browser proof checklist,
   - progress note.
3. Record what changed, what proof passed and what remains open in
   `docs/PROGRESS.md`.
4. If the same kind of issue appears again, promote the guardrail into the
   relevant shared test or skill hygiene check.

Do not create append-only planning clutter. Prune outdated done/history from
active docs instead of layering new plans over old plans.

## 7. OpenAI Goal And Prompt Standards

Use these official standards as operating requirements:

- ExecPlans / `PLANS.md`:
  `https://developers.openai.com/cookbook/articles/codex_exec_plans`
- Goals:
  `https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex`
- Codex prompting:
  `https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide`

Long-running task requirements:

- Work must be restartable from repo files, not chat memory.
- `PLANS.md` must keep `Progress`, `Surprises & Discoveries`,
  `Decision Log` and `Outcomes & Retrospective` current.
- Every milestone must be written as: goal, work, result, proof.
- Every stopping point must say what is done, what remains and what exact next
  action should happen.
- A vague task must be rewritten before implementation. Examples of vague
  wording that must be expanded: "clean up", "improve UX", "make it better",
  "continue", "polish", "fix copy".

Goal requirements:

- A `/goal` must state:
  - outcome,
  - verification surface,
  - constraints,
  - boundaries,
  - iteration policy,
  - blocked stop condition.
- A goal is complete only when the named verification surface proves it.
- If proof cannot be produced, record the blocker, gathered evidence, safe
  remaining scope and exact input needed to unblock.

Prompt requirements:

- Say what to read first.
- Say what to search.
- Say which tools and commands to use.
- Say which files or areas are out of scope.
- Say what counts as proof.
- Say what to do if blocked.
- Do not ask for next steps when the next step is explicit in `PLAN.md`.
- Do not invent broad architecture beyond the active milestone.

## 8. Current State To Respect

Known current direction:

- Command Center, Merchant, Content Planner, Ads Doctor and GA4 form the core
  demo path.
- Content Planner is the deepest product area, but must be cleaned from
  dev-site/migration assumptions.
- Ads Doctor, Merchant, GA4 and Localo are useful review surfaces, not full
  optimizer/write systems.
- Skills must call WILQ API and must not invent product logic.
- Real marketer UAT is still the human usefulness proof unless explicitly
  deferred by the owner.
- Browser/audit proof is useful but does not replace marketer feedback.

Known cleanup already started:

- Active content fields are being migrated to public/final URL semantics.
- Mapping-review packet artifacts are being removed.
- UI translators and ad hoc string cleanup helpers are being removed.
- Action/detail summaries are being moved to clean typed/domain copy.
- Skill smoke is being hardened against old content fields and marketer-facing
  jargon.
- Command Center daily-decision labels and summaries now come from typed WILQ
  API/shared-schema fields instead of route-local React dictionaries.
- `wilq-daily-command` reaches the live WILQ API and the daily context-pack
  smoke passes after capping embedded evidence summaries at 32. Keep watching
  context-pack size as live evidence grows.

## 9. Current Goal

Clean all active inconsistencies first, then continue product development.

Immediate outcome:

```txt
clean public/final URL semantics
-> clean marketer language from API/domain sources
-> condensed marketer surfaces
-> self-improving guardrails
-> verified current goal prompt
```

Do not add new drafting, WordPress handoff, zapis zmian or multi-client feature
work before this cleanup passes focused verification.

## 10. Workstream A - Recovery And Audit

Objective:

Confirm current repo truth before editing.

Tasks:

- Run `rtk git status --branch --short`.
- Run recent git logs for content, PLAN, WILQ, UAT, workspace and client.
- Read `PLAN.md`, `PLANS.md`, `docs/PROGRESS.md`, `docs/CONTEXT.md`,
  `docs/goals/001-goal.md`, `AGENTS.md`.
- Search active code/docs/tests with the stale-term guardrail list maintained
  in the content strategist smoke and any newer hygiene checks.
- Classify every hit as:
  - active product behavior to migrate now,
  - internal technical type safe for now,
  - stale test fixture to rewrite,
  - obsolete artifact to delete,
  - historical archive only,
  - real blocker needing owner decision.

Acceptance:

- Current docs do not claim old dev-site/migration semantics as active product
  strategy.
- Every active stale hit has either been removed or has a dated removal task.

Verification:

- `rtk rg` scans for stale active terms.
- `rtk git diff --check`.

## 11. Workstream B - Active Contract Cleanup

Objective:

Remove stale content and jargon semantics from active API/schema/action/skill
contracts.

Tasks:

- Remove stale dev-preview and migration-era fields from content diagnostics,
  content action payloads and context packs.
- Replace old content URL semantics with:
  `source_public_url`, `final_canonical_url`, `intended_final_url`,
  nullable `preview_url`.
- Ensure dev preview URLs cannot become final canonical URLs.
- Ensure dev/design URL is not a required blocker for preserve/refresh/merge.
- Remove internal action-model, raw preview, raw execution and review-process
  jargon from marketer-facing paths.
- Keep internal code identifiers only where renaming would require a separate
  schema/API migration.
- Add focused tests and skill smoke checks for the removed stale fields.

Acceptance:

- `/api/content/diagnostics`, `/api/actions/...`, `/api/codex/context-pack`
  and skill smoke do not expose old content fields on active marketer paths.
- Marketer-facing summaries use plain Polish from API/domain source.

Verification:

- Focused pytest for content/actions/contracts.
- `wilq-content-strategist` smoke.
- Stale-term `rtk rg` scan.

## 12. Workstream C - Dashboard Condensation

Objective:

Make the dashboard useful to Wilku without narration.

Tasks:

- Keep the core path first:
  `/command-center -> /merchant -> /content-planner -> /ads-doctor -> /ga4`.
- For every domain route, add or refine selected-first panels:
  - one primary decision,
  - why it matters,
  - safe next step,
  - blocker,
  - evidence/source summary,
  - effect/measurement plan.
- Move raw IDs, connector traces, JSON-like payloads, audit rows and low-level
  diagnostics behind technical drawers.
- Remove UI-level translators and route-local cleanup dictionaries.
- If a route receives dirty copy, fix the source API/view-model.
- Source visible daily-decision labels and summaries from typed API/schema/
  view-model fields. Do not add route-local business dictionaries for decision
  copy, source labels, metric labels, blocked promises, CTA labels or skill
  labels.
- Use `agent-browser` screenshots/snapshots for the touched routes.

Acceptance:

- A marketer can understand the first screen without knowing internal models.
- Browser proof for touched routes has no forbidden visible terms.

Verification:

- Dashboard route tests.
- `rtk pnpm --dir apps/dashboard typecheck`.
- `agent-browser` snapshots for touched routes.

## 13. Workstream D - Content Product Completion

Objective:

Turn Content Planner from strong review cockpit into a real content operating
loop.

Tasks:

- Implement first-class `ContentPreflight`:
  preserve, refresh, merge, create or block.
- Make preserve-first the default when existing content exists and no
  evidence-backed refresh reason is present.
- Build Content Inventory v2 over real public content:
  title, H1/H2, meta, FAQ, CTA, links, canonical, body extract, freshness,
  evidence IDs.
- Build duplicate/canonical/cannibalization checks before creation.
- Build `ContentSalesBrief` from preflight, GSC, WP inventory, Ahrefs review
  rows and Ekologus service knowledge.
- Build Claim Ledger for risky legal/environmental/performance claims.
- Require Human Review before WordPress draft handoff.
- Add draft-only WordPress handoff with preview, confirmation and audit.
- Add post-publication measurement windows before claiming success/failure.

Acceptance:

- WILQ can answer: czy pisać, co pisać, co zachować, czego nie wolno obiecać,
  gdzie ma trafić finalny URL i kto musi to zatwierdzić.
- No generated draft bypasses preflight, sales brief, claim review and human
  review.

Verification:

- Content API contract tests.
- Skill evals for messy marketer prompts.
- Browser proof of content first screen.

## 14. Workstream E - Workspace-Ready Core

Objective:

Keep Ekologus depth-first while preventing hardcoded core.

Tasks:

- Add formal typed contracts:
  - `ClientWorkspace`
  - `SiteProfile`
  - `BrandProfile`
  - `ServiceMap`
  - `ClaimPolicy`
  - `ConnectorProfile`
  - `MeasurementProfile`
  - `KnowledgeNamespace`
- Move Ekologus service/claim/tone rules into workspace/profile/card layers.
- Do not build account switchers, agency UI, billing or permissions yet.
- Add a second fake workspace fixture only when it helps prove isolation.

Acceptance:

- Ekologus behavior is preserved.
- Core no longer depends on global Ekologus-only service vocabulary.
- Future client support is a clean extension point, not prompt copy.

Verification:

- Workspace/profile load tests.
- Regression tests for Ekologus decisions.

## 15. Workstream F - Knowledge And Memory Layer

Objective:

Turn source material and decisions into compact reusable knowledge.

Tasks:

- Add source registry with owner, freshness, confidence and source type.
- Convert sources into typed knowledge cards, expert rules, validators,
  playbooks and eval cases.
- Store feedback from sprawdzenie przez człowieka and rejected/approved reasoning as knowledge.
- Store content outcomes after measurement windows.
- Keep broad vector/RAG deferred until typed cards prove useful.

Acceptance:

- WILQ remembers what worked, what was rejected and why.
- Stale knowledge lowers confidence or blocks claims.
- Skills consume compact knowledge via API/context packs, not long prompt dumps.

Verification:

- Knowledge compiler tests.
- Rule-to-decision lineage tests.
- Skill evals that prove stale/unsupported knowledge is blocked.

## 16. Workstream G - Skills, Hooks And Self-Improving Runtime

Objective:

Make Codex runtime a disciplined operator layer over WILQ API.

Tasks:

- Keep skills small and procedural.
- Update skills only after API/schema/view-model contracts exist.
- Add messy prompt evals that check behavior, not just output shape.
- Add hooks or checks that block common regressions:
  stale URL fields, forbidden visible jargon, missing evidence, unsafe write
  paths, non-Polish operator output.
- Record skill eval findings in `docs/evals/skill-eval-ledger.md`.

Acceptance:

- Skills do not decide from prompt prose.
- Every skill answer is backed by WILQ API evidence, source connectors and
  blocked-claim handling.

Verification:

- Skill smoke scripts.
- `scripts/codex_skill_eval.sh` when behavior/output changes.
- Hygiene checks.

## 17. Workstream H - Safe Execution Expansion

Objective:

Expand zapis zmian only after review-first contracts are clean.

Tasks:

- Keep destructive and high-risk execution blocked until explicitly supported.
- Every write path needs typed payload, preview, confirmation, audit and failure
  handling.
- Add one low-risk adapter at a time.
- Preserve rollback/partial failure story before enabling broader writes.

Acceptance:

- No external mutation happens without explicit validated path.
- Blocked write paths remain honest in dashboard and skills.

Verification:

- blocked zapis zmian tests.
- Mutation audit tests.
- Secret redaction tests.

## 18. Verification Plan

Use focused checks first:

- Docs-only: `rtk git diff --check`.
- API/action/schema: focused `rtk uv run pytest ...`.
- Dashboard: touched route tests plus `rtk pnpm --dir apps/dashboard typecheck`.
- Skills: deterministic smoke and targeted eval when behavior changes.
- Browser: `agent-browser` proof for touched marketer routes.
- Broad final: `rtk scripts/verify.sh`.

Do not claim completion from a screenshot, shape smoke or internal eval alone.
Real marketer UAT or explicit owner deferral is required for usefulness claims.

## 19. Current Completion Definition

This cleanup goal is complete when:

- `PLAN.md`, `docs/goals/001-goal.md` and `docs/PROGRESS.md` no longer present
  obsolete dev-site/migration tasks as active.
- Active API/content/action/skill contracts no longer expose old content fields
  on marketer paths.
- Primary dashboard surfaces no longer show forbidden visible terms.
- UI translators/string replacement cleanup helpers are removed.
- Focused API/dashboard/skill checks pass.
- Browser proof confirms touched routes are readable and free from old jargon.
- Remaining historical mentions are either archived or recorded as explicit
  removal debt with owner-visible status.

The final WILQ product is not complete until ContentPreflight, sales brief,
claim ledger, sprawdzenie przez człowieka, WordPress draft handoff, measurement loop,
workspace contracts, knowledge lifecycle and safe execution gates are done.

## 20. Current `/goal` Prompt

```text
/goal

Work in the WILQ repository:
/home/krn/coding/krn/active/wilq-seo

Use `rtk` before every shell command.

Use these standards:
- ExecPlans / PLANS.md:
  https://developers.openai.com/cookbook/articles/codex_exec_plans
- Goals:
  https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex
- Codex prompting:
  https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide

First read:
1. `PLAN.md`
2. `PLANS.md`
3. `docs/PROGRESS.md`
4. `docs/CONTEXT.md`
5. `docs/goals/001-goal.md`
6. `AGENTS.md`

Product identity:
- WILQ = system/product.
- Wilku = human marketer/operator persona.
- Ekologus = first depth-first workspace/client.
- WILQ Core should become reusable through workspace/profile contracts.
- Do not build multi-client SaaS in this goal.

Main outcome:
Clean WILQ's active product semantics and marketer-facing surfaces, then
continue toward the final Marketing Operating System described in `PLAN.md`.

Goal contract:
- Outcome: active WILQ contracts, docs and marketer surfaces are logically clean,
  condensed and free from stale dev-preview/migration assumptions.
- Verification surface: focused API/dashboard/skill checks, stale-term scans,
  browser proof for touched routes and `rtk git diff --check`.
- Constraints: no invented metrics, no prompt-side product logic, no UI
  translators, no compatibility aliases for stale active fields, no broad
  unrelated refactor.
- Boundaries: work in this repo; preserve Ekologus depth-first behavior; do not
  build multi-client SaaS, agency UI, production deployment or high-risk writes.
- Iteration policy: after each failed check, inspect the producing source,
  patch the smallest correct layer, rerun the focused check and update recovery
  docs.
- Blocked stop condition: if a credential, runtime, owner decision, connector
  contract or browser proof is unavailable, record the missing input, evidence
  gathered, safe remaining scope and exact unblocker.

Critical correction:
- `ekologus.pl` is the public canonical content home.
- A dev preview host is optional design/staging context only.
- Do not build or preserve a dev-site migration axis.
- Do not keep stale dev-preview or migration-era content fields as a
  compatibility strategy. Migrate touched active consumers directly.

Engineering constraints:
- Do not implement before recovery and repo search.
- Keep `PLANS.md` long-running sections current: `Progress`,
  `Surprises & Discoveries`, `Decision Log`, `Outcomes & Retrospective`.
- Do not add UI string translators, `replaceAll` cleanup helpers, route-local
  business dictionaries or hardcoded label replacement functions.
- If marketer copy is wrong, fix typed API/schema/view-model/domain source.
- Do not patch business logic in skills.
- Do not invent metrics or claims.
- Every recommendation needs evidence IDs and source connectors.
- Every write path needs typed payload, preview, confirmation and audit.
- Every repeated issue must become a durable self-improving guardrail.
- Every vague task must be rewritten into observable behavior, files to inspect,
  commands to run, acceptance criteria and proof before implementation.

Recovery:
- Run `rtk git status --branch --short`.
- Run recent `rtk git log --oneline --decorate -30`.
- Search active code/docs/tests using the stale-term guardrail list maintained
  in smoke/hygiene checks, then classify every hit.
- Classify each hit as active behavior to migrate, internal technical type,
  stale fixture, obsolete artifact, archive-only history or owner blocker.

Execution order:
1. Finish active stale-term and dev-site/migration cleanup.
2. Remove UI translators and fix dirty copy at typed/domain source.
3. Condense touched dashboard routes into marketer-first decision panels.
4. Add focused tests/smokes preventing regressions.
5. Use `agent-browser` to inspect touched marketer routes.
6. Update `PLAN.md`, `docs/goals/001-goal.md`, `docs/PROGRESS.md` and eval
   ledgers with what changed, proof passed and what remains.

Verification:
- Focused pytest for touched API/action/schema behavior.
- Dashboard route tests and `rtk pnpm --dir apps/dashboard typecheck`.
- Relevant skill smoke/eval when skill behavior changes.
- `agent-browser` proof for touched routes.
- `rtk git diff --check`.
- Use `rtk scripts/verify.sh` before broad completion claims.

Stop only when the current completion definition in `PLAN.md` is true, or when
an exact blocker is recorded with missing input, evidence gathered, safe scope
left and the implementation/input needed to unblock.
```
