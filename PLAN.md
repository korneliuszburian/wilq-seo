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
- Do not keep deprecated active fields, compatibility aliases or stale
  target/dev/migration semantics when touched consumers can be migrated
  directly.
- Every changed line must trace to this plan or an explicit owner request.
- Avoid broad refactors until active inconsistencies are removed and verified.

## 4. Marketer Language Rules

The marketer should see plain Polish operating language.

Preferred visible terms:

- `akcja do sprawdzenia`
- `sprawdzenie w WILQ`
- `Centrum pracy`
- `Treści`
- `Google Ads`
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
- `Command Center`
- `Content Planner`
- `Ads Doctor`
- `blockery`
- `evidence IDs`
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

- Centrum pracy, Merchant, Treści, Google Ads and GA4 form the core review
  path. Existing technical route slugs may remain during this cleanup, but
  visible active language should use the cleaned names.
- Treści is the deepest product area, but must be cleaned from
  dev-site/migration assumptions.
- Google Ads, Merchant, GA4 and Localo are useful review surfaces, not full
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
- Compact skill contexts now expose active actions through typed preview cards,
  Polish blocker labels and `/api/actions/{action_id}`, not raw action payloads
  or payload key lists.
- Merchant action detail previews now have typed API preview cards; remaining
  action kinds still need direct migration away from payload-shape inference.
- Google Ads recommendation action details now have typed API preview cards
  without raw recommendation enums or raw Google Ads IDs in primary card copy.
- Google Ads budget action details now have typed API preview cards without raw
  operation names or raw Google Ads IDs in primary card copy.
- Google Ads negative-keyword action details now have typed API preview cards
  without raw match types, raw levels or Google Ads IDs in primary card copy.
- Google Ads custom-segment action details now have typed API preview cards
  without raw member types, old English internal segment names or Google Ads IDs
  in primary card copy.
- Demand Gen action details now have typed API preview cards without raw Google
  Ads channel enum keys in primary card copy.
- Keyword Planner access blocker action details now have typed API preview
  cards without raw Google Ads API error strings in primary card copy.
- Social draft action details now have typed API preview cards without raw
  source connector IDs or metric keys in primary card copy, and the old
  `source_inputs` payload fallback was removed from Action Detail.
- WordPress draft handoff action details now have typed API preview cards
  without raw candidate IDs, preview-contract names or operation names in
  primary card copy.
- Content refresh action details now have typed API preview cards for content
  brief review and WordPress draft payload review. The primary card copy uses
  public/final URL semantics and no longer depends on stale dev-preview URL
  fields or old URL-review wording.
- Treści selected-decision first screen now uses API-owned
  `marketer_decision` fields for metrics, content angle, H1/H2/FAQ/CTA and
  source facts. The route no longer parses `action.payload.content_brief_preview`
  for the primary marketer card.
- Dashboard API smoke and demo proof now assert current marketer-readable copy
  and reject stale proof wording such as raw Merchant issue keys, raw proof IDs
  in the normal demo flow, `audience size`, `launchu`, `DR`, `brak facts` and
  `competitor_page`.
- Dashboard API smoke includes a shared runtime visible-copy guard over `main`,
  so old working route names, registry headings, stale URL/mapping terms, raw
  `payload` wording and vendor fallback keys fail on the actual rendered
  marketer routes.
- Google Ads search-term n-gram action details now have typed API preview
  cards without raw `SearchTermNgramReview`, preview-contract names or
  n-gram-to-negative-keyword contract keys in primary card copy. The route is
  still slow and needs a separate performance slice.
- Google Ads target-guardrail and strategy-review action details now have typed
  API preview cards without raw action types, validation keys or `.env` field
  names in primary card copy.
- Touched Ads, Merchant, GA4 and tactical queue paths no longer show endpoint
  names, route wording, raw evidence/action link labels or `ID` evidence
  counters in normal marketer copy.
- Detail views render source/domain labels as neutral text chips, not as visual
  status values. The shared status badge no longer injects hidden punctuation
  into browser text output.
- Central blocked-claim labels keep known Polish claims specific and prevent
  unknown raw technical values from becoming marketer-facing copy.
- Knowledge decision details use API-owned source labels instead of raw
  connector IDs, and count copy uses Polish plural forms.
- Knowledge decision-impact panels now consume API-owned missing-data,
  blocked-decision and blocked-claim summary labels. First-screen blocked-claim
  copy is condensed to count summaries; full blocked-claim lists stay in
  details.
- Procesy expanded details now use API/domain missing-data detail labels and
  condensed blocked-claim summaries; the route no longer joins label arrays in
  React for visible process detail copy.
- Primary dashboard navigation and touched route headings now use Polish
  marketer-facing labels instead of mixed legacy route names.
- Google Ads no longer carries unused route-local status/risk label helpers.
- Localo metric names now come from API/domain `metric_label` in diagnostics,
  marketing brief and shared metric chips; remaining dimension labels in metric
  chips now come from API-owned `dimension_labels` and
  `dimension_value_labels`.
- Google Ads campaign, KPI, budget, impression-share and change-history tables
  now consume API/domain row summary labels for human review gates, blocked
  claims and changed fields instead of joining label arrays in React.
- Localo visibility action details now have typed API preview cards;
  `DetailPanels.tsx` no longer renders Localo cards by inferring raw payload
  shape. The card is condensed to key visibility/review metrics.
- Merchant diagnostic metric facts now carry API-owned metric and dimension
  labels; `MerchantDiagnosticSurface` no longer owns a local metric-label
  dictionary for Merchant metric tiles.
- GA4 diagnostic metric facts now carry API-owned metric and dimension labels;
  `Ga4DiagnosticSurface` no longer owns a local metric-label dictionary for
  GA4 proof metric tiles.
- GA4 tracking-quality action previews now carry API-owned operation and
  missing-dimension labels; `Ga4DiagnosticSurface` no longer owns those
  preview translators.
- GA4 tracking-quality action details now have typed API preview cards;
  `DetailPanels.tsx` no longer renders GA4 cards by inferring raw payload
  shape. Live proof is clean, but the action endpoint is slow enough to need a
  separate performance slice.
- Merchant action preview payloads now carry API-owned preview-contract labels;
  `MerchantDiagnosticSurface` no longer owns that label dictionary.
- Merchant issue clusters and issue decisions now carry API-owned
  reporting-context labels; `MerchantDiagnosticSurface` no longer owns that
  fallback.
- Skill smoke is being hardened against old content fields and marketer-facing
  jargon.
- Centrum pracy daily-decision labels and summaries now come from typed WILQ
  API/shared-schema fields instead of route-local React dictionaries.
- Centrum pracy source freshness labels now come from typed WILQ
  API/shared-schema fields instead of route-local enum fallbacks.
- `wilq-daily-command` reaches the live WILQ API and the daily context-pack
  smoke passes after capping embedded evidence summaries at 32. Keep watching
  context-pack size as live evidence grows.
- Daily context-pack metric facts use `MetricFact.metric_label`,
  `dimension_labels` and `dimension_value_labels`. Do not expose raw metric
  keys or vendor dimension enums to Codex skills when a Polish operator label
  exists.
- Live compact context-pack language checks are now repeatable through
  `scripts/context_pack_language_guard.py` and run from `scripts/verify.sh`
  plus `scripts/pre_demo_gate.sh`.
- Marketer-useful metric dimensions such as query, landing page, campaign,
  source and country should keep meaningful Polish/free-text values instead of
  collapsing to generic "wartość wymiaru do sprawdzenia".
- Merchant, Treści and Ahrefs browser proof now passes the targeted
  stale-term scan for visible `ID` proof-count and product-ID wording.
- `/actions` priority cards now describe the safe operating step and keep raw
  action data behind the explicit technical toggle instead of showing
  technical-detail wording on the first screen.
- Ads live-data diagnostics and evidence detail now use Polish proof wording:
  `dowód w WILQ` / `Klucz dowodu w WILQ`, not `ID dowodu`; connector-status
  evidence summaries no longer expose English credential wording.

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
- Old content-review audit events based on dev-site mapping must be dropped
  from active action output instead of being rewritten into current review
  approval.

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
- Action result endpoints expose marketer-facing labels for sources, evidence
  summaries and blockers whenever they retain raw keys for audit.

Verification:

- Focused pytest for content/actions/contracts.
- `wilq-content-strategist` smoke.
- Stale-term `rtk rg` scan.

## 12. Workstream C - Dashboard Condensation

Objective:

Make the dashboard useful to Wilku without narration.

Tasks:

- Keep the core path first, with cleaned visible labels:
  `Centrum pracy -> Merchant -> Treści -> Google Ads -> GA4`.
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

## 13. Deferred Product Layers

The active `PLAN.md` is a cleanup and condensation plan. It must not become a
second long-range roadmap.

The following layers remain real product work, but they are deferred to
`PLANS.md` until this cleanup goal is green:

- Content operating loop: ContentPreflight, preserve-first mode, richer content
  inventory, duplicate/canonical/cannibalization checks, sales brief, claim
  ledger, sprawdzenie przez człowieka, WordPress draft handoff and measurement.
- Workspace-ready core: ClientWorkspace, SiteProfile, BrandProfile, ServiceMap,
  ClaimPolicy, ConnectorProfile, MeasurementProfile and KnowledgeNamespace.
- Knowledge and memory lifecycle: source registry, freshness, confidence,
  feedback memory, outcome cards and rule-to-decision lineage.
- Skills, hooks and self-improving runtime beyond guardrails needed for this
  cleanup goal.
- Safe write expansion beyond the existing validated prepare/review paths.

Do not start these layers from this plan. Finish the active cleanup first, then
promote the next product layer from `PLANS.md` into a new narrow goal.

## 14. Verification Plan

Use focused checks first:

- Docs-only: `rtk git diff --check`.
- API/action/schema: focused `rtk uv run pytest ...`.
- Dashboard: touched route tests plus `rtk pnpm --dir apps/dashboard typecheck`.
- Skills: deterministic smoke and targeted eval when behavior changes.
- Browser: `agent-browser` proof for touched marketer routes.
- Broad final: `rtk scripts/verify.sh`.

Do not claim completion from a screenshot, shape smoke or internal eval alone.
Real marketer UAT or explicit owner deferral is required for usefulness claims.

## 15. Current Completion Definition

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

## 16. Current `/goal` Prompt

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
continue toward the final Marketing Operating System described in `PLANS.md`.

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
