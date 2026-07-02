# PLANS.md - Goal 005 Knowledge Depth And UAT Closure

This is the active long-running ExecPlan for the current WILQ product layer.
It must stay restartable without chat history.

Current cleanup truth remains in `PLAN.md`, `docs/CONTEXT.md`,
`docs/PROGRESS.md`, `docs/goals/001-goal.md`,
`docs/goals/archive/004-goal.md`, `docs/goals/archive/005-goal.md` and Beads.

## How To Use This File

- Read `AGENTS.md`, `PLAN.md`, `docs/CONTEXT.md`,
  `docs/PROGRESS.md` and `docs/goals/archive/005-goal.md` first.
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
- Brak dowodu w WILQ oznacza brak rekomendacji.
- Brak źródła danych oznacza brak rekomendacji.
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

Redacted private-source proposal display is implemented under Beads task
`wilq-seo-8ye`. Service Profile now shows redacted `ekologus-ai`
review-required proposals with `approved_count=0` and `redacted=true`; they do
not compile into cards or unlock daily-content readiness.

Under Beads task `wilq-seo-dtx`, those Service Profile proposals are now
compiled from redacted `reviewed_internal` facts in `source_facts.json` instead
of a separate hardcoded proposal tuple. The live payload exposes sanitized
lineage (`source_id`, `source_type`, `privacy_class`, `scope`) for service and
claim-policy proposals.

Under Beads task `wilq-seo-kot2`, Service Profile now exposes typed private
proposal scope counts and the dashboard/UAT packet render them directly. Live
proof on 2026-07-02 returned `proposal_count=4`, `service_proposal_count=2`,
`claim_policy_proposal_count=2`, `evidence_requirement_proposal_count=0` and
`promotion_ready=false`, so Wilku can distinguish service proposals from
claim-policy review items without opening technical payloads.

Under Beads task `wilq-seo-ebv5`, Service Profile also owns the review-action
summary instead of leaving the UAT packet or dashboard to infer it. Live proof
on 2026-07-02 returned `total_count=12`, `review_request_count=11`,
`prepare_count=1`, `public_service_review_count=6`, `private_review_count=4`,
`private_service_review_count=2` and `private_policy_review_count=2`; the UAT
packet consumes the same API-owned summary.

Under Beads task `wilq-seo-pcgz`, every Service Profile review action now also
has API-owned `review_scope` and `priority`. Private `ekologus-ai` service
proposal actions are `private_service_proposal` / `medium`, while brand/legal
claim-policy actions are `private_claim_policy_proposal` / `high`; dashboard
and the UAT packet render these fields instead of parsing action IDs.

Under Beads task `wilq-seo-vu8c`, every Service Profile review action also
exposes API-owned `decision_options`, aligned with
`scripts/record_service_profile_review_result.py`: `approve`, `needs_changes`,
`stale` and `reject`. Dashboard and the UAT packet now show those options for
the review queue so Wilku can record outcomes without guessing accepted values.

Under Beads task `wilq-seo-pred`, Goal 005 completion is fail-closed through
`scripts/goal_005_completion_check.py`. Completion claims require either a
validated real UAT result or an explicit owner defer with residual risk,
blocked claims and next review. Without one of those inputs the script blocks
claims that Goal 005 is done, that real Wilku usefulness is proven, or that
production-depth/final draft readiness exists.

Repository audit follow-up on 2026-07-02 confirmed a real committed-state
risk: `wilq/credentials` was present locally but ignored by `.gitignore`, so a
fresh checkout could miss `wilq.credentials.runtime`. The package is now part
of the runtime surface and must stay covered by `tests/test_runtime_imports.py`.

The same audit follow-up also hardened connector/job refresh persistence:
`ConnectorRefreshRun` now carries `metrics_persisted`, metric-store failures
rewrite the run to `failed` with sanitized error type only, per-connector job
exceptions no longer abort the whole `JobRun`, and manual job API runs clear
the same view-model caches as direct connector refreshes.

Under Beads task `wilq-seo-x51h`, Service Profile review actions now expose
API-owned `review_requirements`, also aligned with
`scripts/record_service_profile_review_result.py`. The dashboard and UAT packet
show required decision fields (`action_id`, `target_card_id`, `decision`,
source/blocked-claim booleans and `notes`) plus the `follow_up_beads` rule for
blocking review decisions.

Under Beads task `wilq-seo-fjg8`, private source proposals now carry
governance metadata through API, shared schema, dashboard and UAT packet:
`data_classes`, `source_block_refs`, `retention_decision`, `deletion_path` and
`eval_case_ids`. This keeps private `ekologus-ai` reuse auditable and
deletable without exposing raw private content or treating review-required
facts as approved knowledge.

Under Beads task `wilq-seo-d0rw`, the BDO UAT handoff is prepared at
`docs/handoffs/2026-07-02-wilku-bdo-uat-review.md`. It gives Wilku a normal
review artifact for BDO language, CTA and blocked claims, while explicitly
stating that the current live content queue does not expose BDO as an active
work item on 2026-07-02. This prevents the historical `bdo co to` Sales Brief
proof from being presented as a current draft recommendation.

Under Beads task `wilq-seo-3cqd`, the Goal 005 UAT result recorder now requires
`pokazane_materialy_review`, validated as existing repo-relative files under
`docs/handoffs/`. The rendered UAT result lists the artifacts shown to Wilku,
so a future completion proof cannot claim that UAT happened without naming the
actual BDO/Eko-Opieka/Audyt or live packet materials used in the session.

Non-persistent review actions for those private proposals are implemented
under Beads task `wilq-seo-eb1`. Service Profile now gives Wilku concrete
review requests for `ekologus_service_eko_opieka_calendar` and
`ekologus_service_environmental_compliance_audit`, while
`blocked_write_claim` explicitly states that no private proposal is promoted
into an approved fact or knowledge card. Live API proof on 2026-07-02 returned
`private_review_action_count=2`, `approved_count=0` and
`ready_for_daily_content=false`.

Per-service public review actions are implemented under Beads task
`wilq-seo-8bq`. Service Profile now emits non-persistent review requests for
each source-backed public service card, including BDO, waste/packaging and
operat wodnoprawny. These actions stay `review_request`, keep
`can_promote_facts=false`, and explicitly say they do not promote source facts
or knowledge cards without a future ActionObject/audit path.

Under Beads task `wilq-seo-813`, the dashboard Service Profile service cards
now render source trace and review context directly: source connector labels,
source fact IDs, source lineage URLs and `review_request_hint`. This makes the
public service-card review path inspectable by Wilku without opening raw API
responses or inventing another review surface.

Under Beads task `wilq-seo-ht6`, public service-card review results can now be
recorded as a deterministic report through
`scripts/record_service_profile_review_result.py`. The script checks live
Service Profile action/card IDs, reviewer/date/scope, source trace clarity,
blocked-claim review and required follow-up Beads for blocking decisions. It
does not edit source facts, change lifecycle status, set `approved_current` or
unlock production-depth; an `approve` result only means a separate audited
promotion request can be prepared.

Under Beads task `wilq-seo-saf`, that next step now has a central WILQ
ActionObject preview: `act_prepare_service_profile_knowledge_promotion`. The
action validates as prepare-only, uses evidence
`ev_content_service_profile_source_facts`, exposes 6 public service-card
promotion-preview rows and marketer preview cards, and stays blocked with
`apply_allowed=false` plus `api_mutation_ready=false`. It does not mutate
`source_facts.json`, promote cards, set `approved_current` or unlock
production-depth; it only makes the later audited promotion request explicit in
the same ActionObject system as the rest of WILQ.

Redacted per-proposal details are implemented under Beads task `wilq-seo-0ap`.
Service Profile now shows target card, source class, review status, support
level, risk tier, confidence label, blocked claims and safe next step for each
private proposal. Live API proof on 2026-07-02 returned two proposals; the first
is `Eko-Opieka / Eko Kalendarz`, `review_required`, `partial`, `medium`,
`promotion_allowed=false`, `redacted=true`.

Shared schema hardening for private proposal details is implemented under
Beads task `wilq-seo-g1k`. The Service Profile frontend contract now rejects
unknown `review_status`, `support_level` and `risk_tier` values instead of
accepting arbitrary strings, keeping private-source review states explicit
before Wilku sees them in UI or skill output.

Private proposal review now includes a promotion checklist under Beads task
`wilq-seo-n1o`. The checklist is API-owned and rendered in Service Profile:
owner confirmation, redacted/source-safe condensation, claim policy, reviewer/
freshness/confidence/lineage and focused eval are required before any reviewed
source fact can exist. Live proof after stack restart on 2026-07-01 returned
`promotion_ready=false`, five checklist items, `approved_count=0` and
`review_required_count=2`.

The `wilq-content-operator` UAT packet now consumes
`GET /api/content/service-profile` under Beads task `wilq-seo-0bv`. It reports
Service Profile gaps, production-depth readiness and private proposal review
actions inside the existing UAT harness. Live proof on 2026-07-01 returned
`uat_readiness.status=blocked_for_full_uat`, one actionable queue item, two
Service Profile gaps and two private review actions. This is UAT preparation,
not proof that Wilku completed the session.

Under Beads task `wilq-seo-0ff`, the same UAT packet now separates public
service-card review requests from private proposal review requests. Live proof
on 2026-07-02 returned 6 `public_service_review_actions`, 2
`private_review_actions`, 10 total Service Profile review actions and explicit
UAT blockers for public service review, private proposal review and
non-production-depth readiness. This keeps the Wilku handoff concrete without
creating a separate endpoint or promoting source facts automatically.

Goal 005 dashboard typecheck is restored under Beads task `wilq-seo-ttb`.
Stale test fixtures now use the current typed `ContentWorkItem` and structured
draft generation contract, including `knowledge_constraints`, so the dashboard
quality gate no longer blocks broad verification for unrelated fixture drift.

`wilq-content-operator` evals now require refresh-first language when stale
brief decisions appear. The non-interactive proof at
`.local-lab/evals/codex-skill/20260701T222739Z/summary.json` passed with
`operator_usefulness_score=4`, `blocked=true`, six evidence IDs and decision
text that tells Wilku to refresh source data before draft/review work. The
eval harness no longer seeds the technical term `ActionObject` into
operator-facing output.

Non-interactive skill evals now include OpenAI-style task-specific hard gates
and failure tags under Beads task `wilq-seo-s55`. The structured result schema
requires `eval_rubric` and `failure_tags`; the harness fails runs where a false
hard gate has no matching failure tag and caps usefulness at 3 if any hard gate
fails. The first live proof passed for `wilq-gsc-content-doctor` at
`.local-lab/evals/codex-skill/20260702T001627Z` with score 4, all hard gates
true, empty failure tags, six evidence IDs and validated
`act_prepare_content_refresh_queue`.

Google Search Console vendor reads now carry the official Search Analytics
partial-detail caveat in the API contract. The adapter pins `type=web` and
persists `detail_data_completeness=partial_possible` for `query,page` reads, so
later diagnostics and skills can use those rows as SEO decision signals without
treating them as full traffic totals.

The GSC skill eval now enforces that caveat under Beads task `wilq-seo-3pq`.
`wilq-gsc-content-doctor` smoke exposes the latest GSC Search Analytics
contract fields and fails if they are missing. The non-interactive proof at
`.local-lab/evals/codex-skill/20260701T231227Z/summary.json` passed with
`operator_usefulness_score=4`, six evidence IDs, one recommendation and a
validated `act_prepare_content_refresh_queue`, while keeping rows for
zapytania i adresy as `partial_possible` signals from the newest available day.

The Search Analytics caveat is now API-owned under Beads task `wilq-seo-5y8`.
`/api/content/diagnostics` exposes `gsc_search_analytics_contract` with
available-date, `search_type=web`, `detail_dimensions=query,page`,
`detail_data_completeness=partial_possible`, paging and Polish warning labels,
so skills and dashboard code no longer need to infer this from raw
`latest_refreshes.metric_summary`.

The GSC aggregate-vs-detail split is implemented under Beads task
`wilq-seo-bos`. Google Search Console vendor reads now collect an additional
`byProperty` aggregate grouped by `country,device` for the same latest
available day, while keeping detailed `query,page` rows marked
`partial_possible`. The diagnostics contract exposes both so WILQ can discuss
overall organic volume without pretending detailed query/page rows are full
traffic totals.

The same contract now distinguishes official Search Analytics limits from
WILQ's smaller operating cap under Beads task `wilq-seo-llp`: typical 2-3 day
data delay, single-day latest-available reads, official 25k page size, 50k
daily row cap per search type, and the current WILQ `rowLimit=250` /
`max rows=1000` cap for zapytania i adresy. The tightened `wilq-gsc-content-doctor`
non-interactive eval passed at
`.local-lab/evals/codex-skill/20260701T232526Z`.

Marketing brief action items now preserve the same refresh-first semantics as
stale daily decisions. If a safe next action is attached to stale Merchant or
content data, it becomes a blocker titled `Odśwież dane przed akcją` and points
to the stale source labels before any review, queue or draft handoff step.

Live refresh-first recovery proof on 2026-07-01 refreshed the stale brief
sources through WILQ API `vendor_read`: Merchant
`refresh_google_merchant_center_a04a45a6e6fd`, Ahrefs
`refresh_ahrefs_5eee21244cff` and WordPress sklep
`refresh_wordpress_sklep_c1db9b8fa677`. The marketing brief then dropped stale
source blockers for Merchant/content from refresh-first to current review
items; the remaining blocker is GA4 claim safety.

The UAT packet now also exposes the Service Profile private proposal promotion
checklist under Beads task `wilq-seo-0pk`: `promotion_ready=false`, blocked
reason and five required conditions before reviewed source facts. This keeps
Wilku's UAT packet aligned with the Service Profile view model after the
promotion-checklist slice.

The UAT packet now carries redacted private proposal details under Beads task
`wilq-seo-aev`: target, review status, support, risk, blocked claims and
`promotion_allowed=false` for both proposals. This lets Wilku inspect the
private source candidates during UAT without opening another surface and
without exposing raw private text.

The `wilq-content-operator` non-interactive eval oracle is tightened under
Beads task `wilq-seo-6ah`: output must include Service Profile and private
proposal promotion markers (`/api/content/service-profile`,
`promotion_ready=false`, `promotion_checklist`, `reviewed source fact`). The
skill smoke now also fetches `GET /api/marketing/brief` and exposes
`brief_items`, so blocked queue runs still carry route-level marketing context.

The same `wilq-content-operator` eval is hardened further under Beads task
`wilq-seo-0aj`: actionable output must now surface Claim Ledger / generation
gate markers (`Claim Ledger`, `claims_allowed`, `claim_markers`,
`unsupported_claim_used`, `claim_missing_required_evidence`). This is an eval
quality bar only; it does not add a new content flow or bypass the existing WILQ
API claim gates. Targeted non-interactive proof passed at
`.local-lab/evals/codex-skill/20260701T221439Z/summary.json` with
`operator_usefulness_score=4`, `blocked=true`, 6 evidence IDs, 2 recommendations
and 6 action candidates.

Marketing Brief freshness handling is hardened under Beads task `wilq-seo-u0m`.
Ready daily decisions that depend on stale connector evidence are now
refresh-first in `/api/marketing/brief`: the item is surfaced as a blocker,
risk is at least medium, and the safe next step says to refresh stale sources
before treating the decision as operational. Live proof after stack restart on
2026-07-01 showed the content refresh queue naming only stale Ahrefs and
WordPress sklep.ekologus.pl, not fresh GSC or WordPress ekologus.pl.

The first Wilku-ready handoff for Goal 005 UAT is prepared at
`docs/handoffs/2026-07-01-wilku-content-uat-ready.md` under Beads task
`wilq-seo-w8o`. It is a normal review artifact generated from live UAT packet
state: current blockers, Service Profile gaps, private review actions, source
trace IDs and exact result fields. It must be filled after the real Wilku
session before `wilq-seo-jst` can close.

Goal 005 content UAT proof now has a deterministic result validator under
Beads task `wilq-seo-b6u`:
`scripts/record_goal_005_content_uat_result.py`. It validates the completed
Wilku session JSON for selected work item, blocker understanding, Service
Profile/private review feedback, source-trace questions, generic/off-brand
findings, largest product gap and follow-up Beads when full UAT is blocked. It
renders a safety-bounded report only; it does not run UAT, promote private
proposals, approve knowledge cards, unlock WordPress/publishing or close
Goal 005 by itself.

The same UAT result validator is tied to live packet provenance under Beads
task `wilq-seo-nan`. With `--api-base`, it checks that the selected work item
exists in the current WILQ content UAT queue and records queue status, selected
evidence/source connectors, Service Profile read-only state, production-depth
readiness and private proposal promotion state. Live proof on 2026-07-02
accepted `content_work_item_content_decision_https___www_ekologus_pl` with GSC
and WordPress evidence while keeping full UAT blocked by
`production_depth_ready=false` and private review actions.

Under Beads task `wilq-seo-8wn`, the Wilku UAT proof contract now also requires
feedback on public service-card review actions. The handoff asks separately
about public service review actions and private proposal review actions, and
`scripts/record_goal_005_content_uat_result.py` rejects completed result JSON
without `public_service_review_actions_czytelne`. Live proof on 2026-07-02
recorded `public_service_review_action_count=6`,
`private_review_action_count=2`, `production_depth_ready=false` and kept the
overall result as follow-up-required.

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

Sales Brief forbidden claims now flow into the draft/generation gate under
Beads task `wilq-seo-6ic`. `ContentDraftPackage.claims_removed_or_blocked`
includes forbidden claim text recorded on the Sales Brief even after the active
Claim Ledger is resolved for drafting, and structured generation passes that
list into `model_input` for preview/quality acknowledgement gates.

Removed and blocked claim markers are typed under Beads task `wilq-seo-zqs`.
Structured generation model input now carries
`removed_or_blocked_claim_markers` using the same marker shape as allowed
`claim_markers`, preserving claim ID, type, status, evidence, connector and
reviewer lineage for avoided claims.

WordPress draft handoff audit lineage is hardened under Beads task
`wilq-seo-unp`: audit evidence must overlap with the approved human review
evidence and the draft package evidence map, otherwise handoff blocks with
`audit_evidence_mismatch`.

Claim Ledger consistency is hardened under Beads task `wilq-seo-d6h`: forged
or manually assembled entries cannot use safe-looking statuses for guarantee
claims, human-review claim types without a reviewer, or measurement-dependent
claim types without measurement. The existing draft, quality review and
publish-ready paths inherit this gate through `claim_ledger_blockers`.

Claim Ledger high-risk review is tightened under Beads task `wilq-seo-ixa`:
legal, risk and environmental claims still need evidence/source proof after
human review. A reviewed high-risk claim without evidence blocks with
`missing_evidence` instead of becoming `allowed_general` or publish-ready.

Sales Brief product CTA safety is hardened under Beads task `wilq-seo-9i2`.
If a topic/source fact/CTA implies product purchase intent, the brief blocks
with `missing_product_evidence` unless Merchant Center or shop evidence is
present. This keeps product availability/pricing/offer claims out of content
work when WILQ only has SEO intent signals.

Water-permit service coverage is improved under Beads task `wilq-seo-d0m`.
`ekologus_public_water_permit_documentation_2026_07_02` now compiles into
`ekologus_service_operat_wodnoprawny` as `source_backed_review_required`.
Service Profile no longer reports `gap_service_operat_wodnoprawny`, but
production-depth readiness remains false until owner/Wilku approval. Sales
Brief can analyze operat wodnoprawny with GSC/WordPress evidence while keeping
draft readiness blocked by review-required legal/permit constraints.

Google Search Console vendor read is aligned with the first official
Search Analytics ingestion pattern under Beads task `wilq-seo-kr8`: check
available dates first, use the latest available day for detailed zapytania i adresy
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

Quality Review now carries claim-marker faithfulness through the final review
gate under Beads task `wilq-seo-odx`: if a section uses an
`allowed_with_evidence` Claim Ledger entry but omits that claim's required
evidence IDs, the review blocks with `claim_missing_required_evidence`.

Claim Ledger source lineage is hardened under Beads task `wilq-seo-bg4`:
evidence-backed entries now carry `source_connectors`, missing connector
lineage blocks with `missing_source_connector`, and structured generation claim
markers preserve connector lineage beside evidence IDs.

Structured draft generation now exposes Sales Brief `knowledge_constraints`
under Beads task `wilq-seo-tfk`. Generation contracts carry typed evidence
requirements and blocked/review-required knowledge constraints into
`model_input`, keeping review-required knowledge visible to runtime/preview/
quality gates instead of burying it in prose.

Full-draft generation is blocked on review-required knowledge under Beads task
`wilq-seo-7ph`. The same constraints can still support `section_draft` for UAT
and analysis, but `full_draft` returns
`review_required_knowledge_for_full_draft` until knowledge and claim policy are
reviewed enough for production-depth use.

Structured draft preview now requires forbidden-claim acknowledgement under
Beads task `wilq-seo-dfu`: every `claims_removed_or_blocked` item from the
generation contract must appear in `forbidden_claims_avoided`, otherwise
preview blocks with `missing_forbidden_claim_acknowledgement`.

Quality Review mirrors that gate under Beads task `wilq-seo-ygb`, so direct
quality-review calls cannot bypass preview's blocked-claim acknowledgement
requirement.

Shared schemas now type quality finding codes under Beads task `wilq-seo-hc2`;
unknown quality gate codes no longer pass the TypeScript/Zod contract silently.

Shared schemas now also type structured preview blocker codes under Beads task
`wilq-seo-y5x`, using a preview-specific enum instead of the generic workflow
blocker schema.

Shared `ContentWorkItemSchema` now mirrors Python workflow status literals under
Beads task `wilq-seo-kwl`, so unknown workflow states cannot silently drive the
dashboard.

Wilku content UAT preparation was refreshed under Beads task `wilq-seo-jst`.
The current WILQ packet is useful for showing blockers and traceability, but
not for closing full UAT: live proof still has only one actionable candidate
and `queue_status=blocked`. Keep `wilq-seo-jst` open until Wilku completes the
session or the owner records an explicit defer.

`wilq-content-operator` now has a completed non-interactive Codex eval pass
after the ActionObject validation prompt fix. Proof:
`.local-lab/evals/codex-skill/20260701T212839Z/summary.json`; result
`operator_usefulness_score=4`, `blocked=true`, six evidence IDs, two
recommendations and six action candidates, with publish/final article/success
claims blocked.

The eval harness now supports `required_decision_terms_pl`, used first by
`wilq-content-operator`, so critical workflow markers must appear in actionable
output rather than only in `notes`. Hardened proof:
`.local-lab/evals/codex-skill/20260701T213328Z/summary.json`.

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
10. `docs/PROGRESS.md`, `PLANS.md`, `docs/goals/archive/005-goal.md` and Beads agree.
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

Build: this active plan, `docs/goals/archive/005-goal.md`, progress/context alignment
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
- 2026-07-02: Skill eval layer aligned with OpenAI eval guidance:
  production-like Polish inputs, explicit testing criteria/graders,
  deterministic coverage audit, default `operator_usefulness_score >= 4`,
  task-specific hard gates and failure tags. Stale snapshots are not acceptable
  as final workflow value; skills must refresh, provide repair path or block
  conclusions before action.
- 2026-07-01: `wilq-ads-doctor` hardened for BDOS-style operator usefulness:
  broad Ads questions must handle freshness and use full diagnostics/full
  context for the complete review queue, while final output should prioritize
  3-5 review decisions instead of dumping every API field. Keyword Planner
  remains blocked by Google Ads developer token permissible-use/access state,
  not by WILQ credentials.
- 2026-07-01: Sales Brief v2 signal audit completed for the content queue at
  audit time. It found BDO as the strongest candidate then, but current UAT
  preparation must follow live API state, not a stale audit conclusion. Live
  queue proof later on 2026-07-01 shows `queue_status=blocked`, one actionable
  homepage refresh item and no `bdo co to` item in the active queue. Use the
  live UAT packet and Wilku handoff before presenting candidate choice.
- 2026-07-02: Goal 005 completion evidence audit is recorded in
  `docs/audits/005-2026-07-02-completion-evidence-audit.md`. Result: not
  complete. Live WILQ API is reachable and Service Profile is correctly
  read-only/review-gated, but production-depth readiness remains false and the
  live content queue is blocked with only one actionable candidate. Keep
  `wilq-seo-jst` open until Wilku completes the session or the owner records an
  explicit defer with residual risk; run full `rtk scripts/verify.sh` only
  before claiming completion.
- 2026-07-02: Service Profile private proposals now include redacted
  `ekologus-ai` claim-policy facts, not only service facts. Brand voice and
  legal-safety proposals appear as review-required targets with dedicated
  review actions, while promotion, fact editing and daily-content readiness
  remain blocked. This moves the useful `ekologus-ai` knowledge into normal
  WILQ review flow instead of creating another endpoint or artifact layer.
- 2026-07-02: Goal 005 UAT packet/result proof now separates private service
  review from private policy review. The packet exposes service and policy
  counts/actions separately, and the result validator requires
  `private_policy_review_actions_czytelne` plus records live policy provenance.
  This keeps Eko-Opieka/Audyt service review distinct from brand/legal-safety
  policy review while preserving the no-promotion/no-production-depth gates.
- 2026-07-02: Added
  `act_prepare_service_profile_private_proposal_promotion`, a prepare-only
  ActionObject for redacted `ekologus-ai` private proposals. It previews service
  and claim-policy proposals with required review gates and blocked claims, but
  validates only while `apply_allowed=false` and `api_mutation_ready=false`.
  This brings private proposal review into the same WILQ action/audit surface
  as public source-card promotion review without creating a write path.
- 2026-07-02: Service Profile review actions now carry
  `review_requirements` from the WILQ API into dashboard and UAT packet output.
  Live proof after stack restart returned required fields
  `action_id,target_card_id,decision,source_trace_clear,blocked_claims_reviewed,notes`
  and `follow_up_beads` as the blocking follow-up rule.
- 2026-07-02: The `wilq-content-operator` UAT markdown packet now renders those
  Service Profile review requirements next to public/private review actions, so
  Wilku can see the required review fields without opening JSON.
- 2026-07-02: `wilq-content-operator` non-interactive eval now fails unless
  the actionable output includes Service Profile `review_requirements`,
  `source_trace_clear`, `blocked_claims_reviewed` and `follow_up_beads`.
  Passing proof:
  `.local-lab/evals/codex-skill/20260702T043747Z/wilq-content-operator/result.json`.

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
- A diagnostic-derived snapshot is not proof of draft readiness. If the selected
  live decision lacks service/CTA knowledge cards, the correct product state is
  `missing_required_knowledge_card` and no structured draft contract. Ready
  workflow proofs must use a deterministic ready chain or a genuinely
  production-depth live work item.

## Outcomes & Retrospective

Not completed. Goal 005 is active. Latest completion audit:
`docs/audits/005-2026-07-02-completion-evidence-audit.md`.
