# PLANS.md - Goal 005 Knowledge Depth And UAT Closure

This is the active long-running ExecPlan for the current WILQ product layer.
It must stay restartable without chat history.

Current cleanup truth remains in `PLAN.md`, `docs/CONTEXT.md`,
`docs/PROGRESS.md`, `docs/goals/001-goal.md`,
`docs/goals/archive/004-goal.md`, `docs/goals/005-goal.md` and Beads.

## How To Use This File

- Read `AGENTS.md`, `PLAN.md`, `docs/CONTEXT.md`,
  `docs/PROGRESS.md` and `docs/goals/005-goal.md` first.
- Run `bd prime` and `bd ready --json` before choosing work.
- Use Beads for operational task tracking. Do not copy the Beads issue list
  into markdown TODOs.
- Update this file only when the active product plan, proof, decision or
  blocker changes.
- Keep `Progress`, `Surprises & Discoveries`, `Decision Log` and
  `Outcomes & Retrospective` current.

## Latest Completed Goal

Goal 004: Content Operations Layer.

Status: completed on 2026-07-01. Beads epic `wilq-seo-2qq`.

Goal 004 proved the safe mechanics of content operations:

```text
queue candidate
-> opportunity enrichment
-> typed Ekologus knowledge cards
-> operations-grade Sales Brief
-> claim-gated draft variants
-> deterministic quality review
-> bounded revision application
-> human review
-> audit
-> WordPress draft-only handoff
-> measurement window
-> conservative outcome interpretation
```

Broad proof passed with `rtk scripts/verify.sh`: 509 Python tests, 107
dashboard/shared tests and 14 Playwright E2E/demo checks.

Important limitation: Goal 004 closed the architecture and test proof, not
daily usefulness for Wilku. The UAT harness exists, but the first real content
operations session with Wilku is still not a product proof unless completed or
explicitly owner-deferred with residual risk.

## Active Goal

Goal 005: Ekologus Knowledge Depth & UAT Closure.

Status: active. Beads epic `wilq-seo-1oa`.

Objective:

Validate that WILQ's safe content operations loop is useful with real Ekologus
knowledge, not only mechanically complete. Goal 005 must deepen typed knowledge
cards, expose a read-only Service Profile/review path, run or explicitly defer
the first real Wilku UAT, and audit Sales Brief v2 signal quality.

This is not a new writing-flow goal. Do not add autopublishing, social
publishing, broad RAG/vector DB, multi-client SaaS, workspace admin, outcome
claims before measurement, or direct Codex/OpenAI/WordPress bypasses.

## Product Thesis

WILQ's hardest anti-slop problem after Goal 004 is no longer "can the system
block unsafe writing?". It can. The harder question is whether the typed
knowledge and evidence signals are deep enough that Wilku gets a useful
Ekologus-specific brief instead of formally correct generic SEO copy.

The next product step is therefore:

```text
knowledge-card depth audit
-> Service Profile read/review surface
-> Sales Brief signal-quality audit
-> first real Wilku UAT
-> precise follow-up blockers or implementation slices
```

## Non-Negotiable Rules

- WILQ API owns product logic.
- Dashboard renders API-owned view models.
- Codex skills consume WILQ API; they do not invent product behavior.
- No evidence ID means no recommendation.
- No source connector means no recommendation.
- Weak, stale or thin evidence must become an explicit low-confidence/blocker
  state, not a polished generic brief.
- Typed knowledge cards do not replace live evidence.
- Knowledge-card updates must be reviewed/gated. Initial Service Profile work
  is read-only plus flag/review request, not ungated self-service writes.
- No broad RAG/vector DB before typed cards, source lineage, freshness,
  validators and evals are strong.
- No fake SEO score or magic content score.
- No publish-ready draft claim.
- WordPress remains draft-only/review-gated. No automatic publish.
- Measurement outcome remains conservative and cannot claim success before the
  observation window has usable data.

## Current Discovery

Current `wilq/content/knowledge/cards.py` contains three seeded cards:

- `ekologus_service_environmental_compliance`
- `ekologus_cta_consultation_without_guarantee`
- `ekologus_evidence_live_connector_requirement`

That is enough for Goal 004 contract proof. It is not yet enough to claim deep
Ekologus knowledge coverage across real services, buyer problems, triggers,
CTA patterns, claim policies and evidence requirements.

Goal 005 now has the first data-driven source-fact layer:

- `wilq/content/knowledge/source_facts.json` stores commit-safe public
  Ekologus facts from the source pack.
- `wilq/content/knowledge/source_facts.py` validates source type, privacy,
  review state, freshness, evidence IDs, source connectors and blocked claims.
- `wilq/content/knowledge/cards.py` compiles those facts into
  `source_backed_review_required` cards and keeps seeded cards as contract
  guardrails.

This is still not production-depth knowledge. Public source facts support
analysis and UAT only until owner/Wilku review marks the relevant facts
approved.

First `ekologus-ai` reuse must use the existing knowledge/source-fact/card
layer. Do not add a separate endpoint or dashboard surface for the same
knowledge unless a reviewed artifact/UAT proves that the existing content
workflow cannot use it. The right operator output is a normal brief, draft,
current-state summary, question list or handoff markdown for Wilku/owner
review. Keep `ekologus-ai` facts redacted and review-required until explicit
review promotes them.

The broader product roadmap is now summarized in
`docs/roadmap/bdos-class-wilq-master-roadmap.md`. Current maturity against the
long-term BDOS-class bar is estimated at `35-45%`: the API-first safety/content
foundation is substantial, while reviewed knowledge depth, UAT, claim-level
generation gating, measurement provenance, optimizer depth and write execution
remain unfinished.

Public `ekologus-ai` audit is recorded in
`docs/audits/005-2026-07-01-ekologus-ai-reuse-audit.md` and Beads task
`wilq-seo-5fd`. Reuse the old repository as a contract/source-pattern catalog,
not as a revived product. The strongest candidates for WILQ are evidence pack,
source claim markers, generation gate, quarantine/post-output validation,
Guardian rules, strategy evidence hydration and marketer usefulness rubric.

Private `krn-ekologus-brain` audit is recorded in
`docs/audits/005-2026-07-01-ekologus-brain-source-catalog-audit.md` and Beads
task `wilq-seo-409`. Reuse it as a governed source-catalog pattern:
metadata-only intake, owner/audience/risk decisions, schema-gated condensation,
owner review, import proof and eval. Do not auto-connect private folders,
commit raw internal materials or let private review-required facts unlock
production-depth cards. The next useful WILQ slices are read-only Service
Profile review and/or a private source-proposal schema.

Private source proposal protocol is designed in
`docs/architecture/private-source-proposal-protocol.md` under Beads task
`wilq-seo-wtf`. It is a design contract only: no automatic import, no raw
private text, no paths/filenames/contact data, and no production-depth unlock
without review/eval. Future implementation should start with read-only Service
Profile coverage display.

Read-only Service Profile review surface is designed in
`docs/architecture/service-profile-review-surface.md` under Beads task
`wilq-seo-94k`. Proposed endpoint: `GET /api/content/service-profile`. The
view model should aggregate existing cards/source facts into Polish service
coverage, claim rules, evidence requirements, source lineage, gaps and blocked
write policy. V1 has no card editing and no fact promotion.

Read-only Service Profile v1 is implemented under Beads task `wilq-seo-lmm`.
Endpoint: `GET /api/content/service-profile`; dashboard route:
`/service-profile`. Live smoke after stack restart returned
`read_only=True`, `status=source_backed_review_required`, `service_card_count=6`,
gaps `gap_service_operat_wodnoprawny` and `gap_no_approved_current_cards`, and
`can_edit_cards=False`.

Draft variant selection guard is implemented under Beads task `wilq-seo-87i`.
`ContentDraftVariantsResult` now exposes the recommended variant, comparison
dimensions, a `magic_score_used=false` policy and a safe next step. The first
rule favors preserve-first refresh when the work item already has an approved
refresh plan; all variants remain non-publishable and WordPress-write blocked.

Measurement outcome provenance is hardened under Beads task `wilq-seo-708`.
`ContentMeasurementObservedMetric` must now tie every usable observation to
metric facts, connector refresh runs, the exact work item, measurement window,
content URL, allowed metric and allowed connector. Missing lineage returns
`insufficient_data`; it cannot produce `directional_improvement` or
`measured_success`.

Goal 006 claim-gate work has started with a small compatible slice under
Beads task `wilq-seo-sby`: quality review now blocks
`unsupported_claim_used` when a structured draft includes a claim absent from
the Claim Ledger. This does not replace the larger per-work-item Claim Ledger
roadmap, but it prevents invented output claims from reaching human review as
ready.

Structured draft preview now has the matching early gate under Beads task
`wilq-seo-eva`: preview blocks `unknown_claim_reference` when runtime output
uses a claim not present in `contract.model_input.claims_allowed`.

WordPress draft handoff audit lineage is hardened under Beads task
`wilq-seo-unp`: audit evidence must overlap with the approved human review
evidence and the draft package evidence map, otherwise handoff blocks with
`audit_evidence_mismatch`.

Claim Ledger consistency is hardened under Beads task `wilq-seo-d6h`: forged
or manually assembled entries cannot use safe-looking statuses for guarantee
claims, human-review claim types without a reviewer, or measurement-dependent
claim types without measurement. The existing draft, quality review and
publish-ready paths inherit this gate through `claim_ledger_blockers`.

Google Search Console vendor read is aligned with the first official
Search Analytics ingestion pattern under Beads task `wilq-seo-kr8`: check
available dates first, use the latest available day for detailed query/page
facts, page with `rowLimit`/`startRow`, and keep the stored result bounded and
sanitized.

Content diagnostics evidence is now condensed through the same latest metric
fact identity rule as tactical queue under Beads task `wilq-seo-alf`. This
keeps GSC/content skill context focused on current proof instead of dragging
stale duplicate refresh IDs into every operator answer.

`wilq-gsc-content-doctor` smoke now guards this behavior under Beads task
`wilq-seo-uk3`: live skill proof fails if content diagnostics includes stale
duplicate GSC refresh evidence instead of the latest completed vendor-read
evidence.

## In Scope

Goal 005 includes:

1. Knowledge-card depth audit against real Ekologus services, buyer problems,
   buyer triggers, CTA patterns, claim constraints and evidence requirements.
2. Use the implemented read-only Ekologus Service Profile/review surface in
   Wilku UAT and future private proposal review.
3. First real Wilku content UAT, or explicit owner defer with residual risk.
4. Sales Brief v2 signal-quality audit across current queue candidates,
   connector freshness/density and enrichment usefulness.
5. Use the implemented evidence-based draft variant selection guard: no fake
   score, no new generation flow, just API-owned comparison by evidence
   coverage, service fit, buyer problem, CTA fit, duplicate risk and
   quality-review dependency.
6. Focused blockers/tests for missing required knowledge or weak signals.

## Out Of Scope

Goal 005 must not build:

- automatic WordPress publishing,
- destructive updates of existing `ekologus.pl` content,
- mass article generation,
- direct Codex-authored production content,
- direct Codex/OpenAI calls bypassing WILQ API,
- direct WordPress client calls from skills,
- broad RAG/vector memory,
- multi-client SaaS or agency admin,
- Ads/Merchant/Localo write automation,
- social publishing,
- public success/failure claims before measurement readiness.

## Completion Definition

Goal 005 is complete only when repo evidence proves all of this:

1. Knowledge-card coverage is audited against real Ekologus services, buyer
   problems, triggers, CTA patterns, claim constraints and evidence
   requirements.
2. The audit states whether current cards are production-depth, thin, stale or
   placeholder-like, with exact gaps and source lineage.
3. Missing required card states are represented as typed blockers and covered by
   focused tests or a documented blocker.
4. A read-only Service Profile/review design or implementation exists for
   Wilku-facing inspection of cards, freshness, source lineage and gaps.
5. Knowledge-card write/update behavior remains blocked unless a future
   human-review/audit path is explicitly implemented.
6. Sales Brief v2 signal quality is assessed for current queue candidates:
   sufficient, thin, stale or blocked, with connector/domain cause stated.
7. Draft variant selection has an evidence-based comparison plan or
   implementation and does not introduce a fake SEO/content score.
8. One real Wilku UAT session is completed in 45 minutes or less, or the owner
   explicitly defers it with residual risk and exact next UAT input required.
9. UAT proof captures confusion points, off-brand/generic SEO findings,
   source-trace questions, selected work item and exact follow-ups.
10. `docs/PROGRESS.md`, `PLANS.md`, `docs/goals/005-goal.md` and Beads agree.
11. Focused verification passes for changed areas, and full
    `rtk scripts/verify.sh` passes before completion claims.

## Verification Surface

Use focused verification after every slice and full verification before
completion.

Minimum proof surface:

- Knowledge-card domain tests under `tests/content`.
- API contract tests for Service Profile/review endpoints if implemented.
- Dashboard route/component tests if a Service Profile surface is implemented.
- `wilq-content-operator` smoke/eval if the skill consumes new Service Profile
  or UAT fields.
- `rtk git diff --check` for docs-only slices.
- `rtk uv run pytest tests/content -q` for content domain changes.
- Relevant dashboard tests/typecheck for UI changes.
- `rtk scripts/verify.sh` before completion.

## Beads Operational Graph

Use Beads as the authoritative development task graph. Active Goal 005 epic:

- `wilq-seo-1oa` - Goal 005: Ekologus Knowledge Depth & UAT Closure.

Initial slices:

- `wilq-seo-9do` - Goal 005 recovery and plan alignment.
- `wilq-seo-3lk` - audit Ekologus knowledge-card depth.
- `wilq-seo-94k` - design read-only Ekologus Service Profile review surface.
- `wilq-seo-jst` - run first real Wilku content UAT or record explicit defer.
- `wilq-seo-n8r` - audit Sales Brief v2 signal quality.
- `wilq-seo-87i` - define evidence-based draft variant selection guard.
- `wilq-seo-708` - harden measurement outcome provenance for content decisions.
- `wilq-seo-ciz` - collect source-backed Ekologus service and claim source pack.
- `wilq-seo-lt1` - expand typed Ekologus knowledge cards from reviewed sources.
- `wilq-seo-t13` - add knowledge-card production-depth guard tests.
- `wilq-seo-409` - evaluate private Ekologus Brain source catalog relevance
  for Goal 005; this is not an automatic integration.

This section is a recovery index only. Operational status lives in Beads.

## Execution Order

### 1. Recovery and plan alignment

Inspect first: `AGENTS.md`, `PLAN.md`, `PLANS.md`, `docs/CONTEXT.md`,
`docs/PROGRESS.md`, `docs/goals/archive/004-goal.md`, current knowledge-card
code and Beads.

Build: this active plan, `docs/goals/005-goal.md`, progress/context alignment
and Beads graph.

Do not build: product behavior.

Proof: `bd ready --json`, `git diff --check`, commit and push.

### 2. Knowledge-card depth audit

Inspect first:

- `wilq/content/knowledge/cards.py`
- `wilq/content/briefs/sales.py`
- `wilq/content/enrichment/opportunity.py`
- `tests/content/test_content_knowledge_cards.py`
- current Ekologus source docs and live queue/enrichment when API is reachable.

Build: a coverage audit and exact implementation blockers for missing or thin
cards.

Do not build: broad RAG or prompt-only knowledge.

Proof: focused tests or explicit blocker if production-depth cards cannot be
created without owner/source input.

### 3. Service Profile review path

Inspect first: content knowledge cards, knowledge API router, dashboard knowledge
surfaces and shared schemas.

Build: read-only Service Profile/review design or implementation. It should let
Wilku inspect current service knowledge, source lineage, freshness, claim
constraints and missing coverage. Flagging/review requests are allowed only if
they are explicitly gated.

Do not build: direct knowledge-card editing.

Proof: API/dashboard tests if implemented; otherwise a concrete design with
blocked write-path rules.

### 4. Sales Brief v2 signal-quality audit

Inspect first: queue candidates, enrichment source facts, GSC/GA4/Ahrefs/
WordPress connector freshness and Sales Brief v2 output.

Build: an audit that classifies signals as sufficient, thin, stale or blocked
and names connector/domain causes.

Do not build: fake opportunity scores.

Proof: domain/API tests or a documented blocker for weak source data.

### 5. Wilku UAT

Inspect first: UAT harness, `/content-workflow`, current content queue and
operator skill output.

Build: a real UAT packet and session proof, or explicit owner defer with
residual risk.

Do not build: a prettier demo that hides missing depth.

Proof: participant/date/scope, selected work item, completion time, confusion
points, off-brand/generic SEO findings, source-trace questions and follow-ups.

## Stop Conditions

Stop and record a blocker if:

- current knowledge cards are mostly seed/placeholder coverage and no trusted
  Ekologus source exists to deepen them,
- Wilku cannot complete one content session within 45 minutes without developer
  intervention,
- draft variants sound like generic SEO despite passing formal gates,
- WordPress draft-only handoff requires debugging during normal UAT,
- Wilku asks "skąd to wzięło?" and the UI cannot show a concrete source fact,
- a proposed endpoint lets Wilku update knowledge cards without human
  review/audit,
- live Structured Outputs is enabled without a separate adapter-boundary audit.

## Progress

- 2026-07-01: Goal 005 Beads epic `wilq-seo-1oa` created. Initial recovery,
  knowledge audit, Service Profile, UAT, Sales Brief signal-quality and variant
  selection slices created.
- 2026-07-01: Current knowledge implementation inspected. It has three seeded
  cards, so Goal 005 starts from "contract proof exists, depth unverified".
- 2026-07-01: Second-opinion follow-up checked against local code. The reported
  `unknown` content POST request gap is already fixed in `api.ts` and shared
  schemas. A real remaining measurement risk was filed as `wilq-seo-708`:
  outcome interpretation needs explicit metric_store/JobRun/evidence
  provenance before WILQ can claim hard measurement usefulness.
- 2026-07-01: Knowledge-card depth audit completed in
  `docs/audits/005-2026-07-01-knowledge-depth-audit.md`. Current cards are
  typed Goal 004 seeds and guardrails, not production-depth Ekologus knowledge.
  Follow-up tasks created for source pack (`wilq-seo-ciz`), source-backed card
  expansion (`wilq-seo-lt1`) and production-depth guard tests (`wilq-seo-t13`).
  Focused proof passed: `rtk uv run pytest tests/content/test_content_knowledge_cards.py -q`.
- 2026-07-01: Source-backed Ekologus source pack completed in
  `docs/audits/005-2026-07-01-ekologus-source-pack.md`. Public `ekologus.pl`
  sources give commit-safe candidates for environmental consulting/outsourcing,
  BDO/reporting, waste/packaging obligations, training, remediation/monitoring,
  sorbents/product content and Zielony Lad education. The pack is source
  material for `wilq-seo-lt1`, not an approval to mark cards production-depth
  without Wilku/owner review.
- 2026-07-01: Production-depth guard slice `wilq-seo-t13` added
  `production_depth_readiness` to the content knowledge-card contract. Seeded
  cards now report `seeded_contract_proof` and cannot be treated as daily-use
  production knowledge. Source-backed public cards remain review-required until
  owner/Wilku approval. The matcher no longer lets broad environmental terms
  alone unlock a service card.
- 2026-07-01: Master roadmap and abandoned `ekologus-ai` reuse audit added.
  WILQ should port selected content-safety contracts into the existing API
  workflow, especially Claim Ledger and Generation Gate candidates, instead of
  adding another Wilku packet/product layer.
- 2026-07-01: Local WILQ API blocker cleared. `scripts/local_stack.sh start`
  restored API/dashboard reachability. Live Goal 005 refreshes completed for
  GSC (`refresh_google_search_console_27ca850b1fa4`), GA4
  (`refresh_google_analytics_4_5ebc4ba1c966`) and WordPress Ekologus
  (`refresh_wordpress_ekologus_691cbe6ab27d`). The WordPress HTTP client call
  timed out at 120 seconds, but the backend refresh run completed and persisted
  evidence.
- 2026-07-01: `wilq-ga4-analyst` API-backed proof recorded in
  `docs/handoffs/2026-07-01-ga4-traffic-quality-proof.md`. The skill separates
  measurement blockers from traffic-quality review candidates and blocks
  unsupported ROAS/revenue/conversion conclusions.
- 2026-07-01: AGENTS.md hardened local recovery and skill-eval rules. Future
  WILQ work must actively restore the local stack when API/dashboard is
  unreachable and must use non-interactive Codex evals as BDOS-class workflow
  proof for realistic marketer commands, not only deterministic smoke scripts.
- 2026-07-01: Skill eval layer aligned with OpenAI eval guidance: production-like
  Polish inputs, explicit testing criteria/graders, deterministic coverage
  audit and default `operator_usefulness_score >= 4`. Stale snapshots are not
  acceptable as final workflow value; skills must refresh, provide repair path
  or block conclusions before action.
- 2026-07-01: `wilq-ads-doctor` hardened for BDOS-style operator usefulness:
  broad Ads questions must handle freshness and use full diagnostics/full
  context for the complete review queue, while final output should prioritize
  3-5 review decisions instead of dumping every API field. Keyword Planner
  remains blocked by Google Ads developer token permissible-use/access state,
  not by WILQ credentials.
- 2026-07-01: Sales Brief v2 signal audit completed for the current content
  queue. BDO is the strongest UAT candidate; Zielony Lad is reviewable but
  service-fit thin; operat wodnoprawny and magazynowanie odpadów need reviewed
  knowledge cards before brief depth; Ahrefs blocked candidate needs a typed
  blocked snapshot surface. Enrichment source facts now preserve connector
  evidence lineage.

## Surprises & Discoveries

- The current cards are useful as guardrails but too broad for deep Ekologus
  operations: one service card covers BDO/odpady/Zielony Lad together.
- UAT harness proof is not the same as Wilku UAT. Treat it as preparation, not
  validation.
- Official public Ekologus pages are enough to create reviewed candidates, but
  they still need strict claim policy: public marketing copy must not become a
  WILQ guarantee, and stale article deadlines/rates cannot become current-law
  claims.
- A separate private project, `krn-ekologus-brain`, and internal Ekologus
  knowledge bases exist. They may be useful later, but Goal 005 must treat them
  as private source context to evaluate, not as automatic WILQ SEO input.

## Decision Log

- Goal 005 focuses on usefulness validation and knowledge depth, not another
  writing pipeline.
- Service Profile starts read-only plus review/flag semantics. Direct
  self-service knowledge writes are out of scope until a review/audit path
  exists.
- Variant selection must be evidence-based dimensions/blockers, not a fake
  score.
- Measurement outcome hardening is a Goal 005 support slice, not a replacement
  for knowledge depth and UAT. The request-typing part of that second opinion is
  stale; provenance remains valid.
- Do not expand cards from memory. Production-depth cards require reviewed
  Ekologus source lineage or an explicit source blocker.
- Source-backed card expansion may proceed from public Ekologus URLs only as
  review-required/claim-gated cards unless Wilku or the owner approves them as
  current service knowledge.
- Private Ekologus Brain/customer-document material is not commit-safe lineage.
  Any future use needs a sanitized review path and explicit promotion in a
  later slice.
- Content diagnostics ranking is allowed to penalize stale secondary connector
  decisions when fresh primary content evidence exists. Ahrefs remains useful
  as a review/gap source, but stale Ahrefs must not outrank a fresh
  GSC/WordPress `refresh_or_merge` next step in the general marketer queue.
- Goal 006 claim-gate slices should keep migrating the `ekologus-ai`
  source-claim-marker pattern into WILQ API contracts. Structured generation
  now carries typed `claim_markers` beside backward-compatible
  `claims_allowed`, so future preview/quality gates can reason from claim ID,
  type, status, evidence and reviewer metadata instead of text matching alone.
- Claim markers are not just context fields: structured draft preview now
  blocks a section that uses a marker-backed claim without referencing that
  claim's required evidence IDs. This keeps faithfulness local to the section,
  not only global to the whole draft.
- Workflow tests should distinguish deterministic ready-chain fixtures from the
  live diagnostics snapshot. The live snapshot may legitimately block Sales
  Brief/draft when the top freshness-ranked decision lacks production-depth
  service or CTA knowledge cards.

## Outcomes & Retrospective

Not completed. Goal 005 is active.
