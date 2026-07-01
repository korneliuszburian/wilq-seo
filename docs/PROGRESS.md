# WILQ Progress Ledger

This file is the short recovery ledger. It is not a changelog and must not
become an append-only transcript.

Current cleanup plan: `PLAN.md`
Active product execution plan: `PLANS.md`
Goal 001 contract: `docs/goals/001-goal.md`

## Current Readout

Date: 2026-07-01

- WILQ is the system/product.
- Wilku is the human marketer/operator persona.
- Ekologus is the first depth-first workspace/client.
- `ekologus.pl` is the public canonical content home.
- Dev preview hosts are optional design/staging context only when explicitly
  configured. They are not canonical content targets and must not drive content
  decisions by default.
- WILQ API is the product brain. Dashboard and Codex skills consume typed API
  contracts, source connectors and WILQ-described evidence.
- Beads (`bd`) is the operational task graph for current work. Run `bd prime`
  and `bd ready --json` after recovery. Active Goal 005 epic:
  `wilq-seo-1oa`. Goal 004 epic `wilq-seo-2qq` is completed. Goal 003 epic
  `wilq-seo-u6u` is completed. Historical Goal 001 cleanup epic:
  `wilq-seo-6rw`.
- Marketer-facing UI and skill output must use Polish operating language.
- Marketer-facing text must defend itself: every empty, missing or blocked
  state has to say what it means for the next decision, not just that data is
  absent.
- Raw IDs, connector trace, raw payloads and audit details belong only in
  technical detail.
- Dirty copy must be fixed in typed API/schema/view-model/domain source, not
  with React translators, string replacement helpers or stale label maps.
- Do not preserve deprecated active fields, compatibility aliases or stale
  dev-preview/migration semantics when direct migration is feasible.
- Real marketer UAT for Goal 001 is explicitly deferred by the owner in
  `docs/handoffs/2026-06-30-owner-defer-marketer-uat.json`. This does not
  claim that UAT happened. It means the current cockpit may be treated as a
  verified review surface while WILQ moves through Goal 003 content-quality work
  before presenting it as a daily content workbench to Wilku.

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

## Current Goal Transition

- Goal 005: Ekologus Knowledge Depth & UAT Closure is active under Beads epic
  `wilq-seo-1oa`. The goal is not another writing pipeline. It validates
  whether the Goal 004 safe content operations loop is useful for Wilku with
  real Ekologus knowledge. Initial Beads slices are: recovery/plan alignment
  `wilq-seo-9do`, knowledge-card depth audit `wilq-seo-3lk`, read-only Service
  Profile review design `wilq-seo-94k`, first real Wilku UAT or explicit defer
  `wilq-seo-jst`, Sales Brief v2 signal-quality audit `wilq-seo-n8r`, and
  evidence-based draft variant selection guard `wilq-seo-87i`.
- Goal 005 starts from an important discovery: current
  `wilq/content/knowledge/cards.py` has three seeded cards
  (`ekologus_service_environmental_compliance`,
  `ekologus_cta_consultation_without_guarantee` and
  `ekologus_evidence_live_connector_requirement`). They prove the Goal 004
  typed-card contract, but they do not yet prove deep coverage of real Ekologus
  services, buyer triggers, CTA patterns, claim policies and evidence
  requirements.
- Goal 005 stop line: do not claim daily content usefulness until knowledge
  coverage, Sales Brief signal quality and a real Wilku UAT session are proven
  or explicitly owner-deferred with residual risk. Initial Service Profile work
  is read-only plus review/flag semantics; ungated knowledge-card writes remain
  out of scope.
- Second-opinion follow-up after Goal 005 activation: the reported loose
  `unknown` request typing for core content POSTs is stale in the current repo;
  `api.ts` validates preflight, Sales Brief, draft package, human review and
  measurement-window requests through shared Zod schemas. The still-valid risk
  is measurement provenance: `wilq-seo-708` tracks whether measurement outcome
  interpretation is tied to metric_store facts, connector refresh/JobRun
  lineage, evidence IDs and the original content decision before any broader
  usefulness claim.
- Knowledge-card depth audit is recorded in
  `docs/audits/005-2026-07-01-knowledge-depth-audit.md`. Result: the current
  three cards are typed Goal 004 seeds and useful anti-slop guardrails, but they
  are too broad and internally sourced to prove production-depth Ekologus
  knowledge. Follow-ups: collect source-backed service/claim source pack
  `wilq-seo-ciz`, expand reviewed typed cards `wilq-seo-lt1`, and add
  production-depth guard tests `wilq-seo-t13`. Focused proof passed:
  `rtk uv run pytest tests/content/test_content_knowledge_cards.py -q`.
- Goal 005 source-pack slice `wilq-seo-ciz` produced
  `docs/audits/005-2026-07-01-ekologus-source-pack.md`. Public Ekologus pages
  now give commit-safe source candidates for environmental consulting/
  outsourcing, BDO/reporting, waste/packaging obligations, training,
  remediation/monitoring, sorbents/product content and Zielony Lad education.
  This removes the "no source material" blocker for the next card-expansion
  slice, but it does not approve production-depth cards: legal/environmental/
  risk/product/current-law claims remain review-gated, and Wilku/owner review is
  still needed before treating cards as fully approved Ekologus knowledge.
- Goal 005 production-depth guard slice `wilq-seo-t13` is implemented with a
  typed `production_depth_readiness` guard on content knowledge-card responses.
  Current seeded cards are explicitly `seeded_contract_proof` and
  `ready_for_daily_content=false`; public source-backed cards will still be
  `source_backed_review_required` until reviewed. The matcher also blocks broad
  environmental terms from overmatching as a service card. Focused proofs passed:
  `rtk uv run pytest tests/content/test_content_knowledge_cards.py -q`,
  `rtk pnpm test` and `rtk pnpm typecheck` in `packages/shared-schemas`, plus
  dashboard API tests/typecheck.
- Goal 005 source-fact registry slice is implemented. Public Ekologus source
  material now lives in `wilq/content/knowledge/source_facts.json` and validates
  through `wilq/content/knowledge/source_facts.py`; `cards.py` compiles
  commit-safe public facts into lifecycle-aware `source_backed_review_required`
  cards with source fact IDs, source connectors, blocked claims and review
  gates. The API still reports `ready_for_daily_content=false`; these cards
  support analysis/UAT only until owner/Wilku review marks facts approved.
  Focused proofs passed: `rtk uv run pytest tests/content -q`,
  `rtk uv run ruff check wilq/content/knowledge tests/content/test_content_knowledge_cards.py`,
  `rtk pnpm --filter @wilq/shared-schemas test` and
  `rtk pnpm typecheck` in `packages/shared-schemas`.
- Goal 005 first `ekologus-ai` reuse slice now treats
  `materials_clean/approved` as a reviewed internal knowledge source for WILQ,
  not as a separate UI module. Redacted review-required source facts can inform
  content briefs, drafts, quality checks and handoff artifacts, but they do not
  compile into production-depth cards or daily-content readiness until reviewed
  in WILQ. Wilku-facing outputs should be ordinary repo artifacts or content
  drafts/briefs written in plain Polish, not a special “packet” product layer.
- First ordinary Wilku artifact from `ekologus-ai` now lives at
  `docs/handoffs/2026-07-01-wilku-eko-opieka-review.md`. It gives a
  human-readable Eko-Opieka/Eko Kalendarz current-state summary, draft angles,
  safe/unsafe wording and exact questions to ask Wilku. This is the intended
  handoff shape before any new endpoint/dashboard work.
- Second ordinary Wilku artifact now lives at
  `docs/handoffs/2026-07-01-wilku-audyt-zgodnosci-review.md`. It frames Audyt
  zgodności as a possible product wejściowy with draft angles, safe/unsafe
  wording and questions for Wilku, still without claiming legal/publication
  readiness.
- Service Profile now exposes non-persistent review requests for the two
  redacted `ekologus-ai` private proposals. These proposals are now compiled
  from redacted `reviewed_internal` service facts in
  `wilq/content/knowledge/source_facts.json`, not maintained as a second
  hardcoded catalog. Live API proof on 2026-07-02:
  `private_review_action_count=2`, targets
  `ekologus_service_eko_opieka_calendar` and
  `ekologus_service_environmental_compliance_audit`, `approved_count=0`,
  `ready_for_daily_content=false`, `source_type=reviewed_internal`,
  `privacy_class=redacted_only` and `scope=service`. These actions help Wilku
  decide what to review next, but they do not promote private proposals into
  approved facts or knowledge cards.
- Service Profile now also exposes redacted per-proposal details for private
  source proposals: target card, source class, review status, support level,
  risk tier, confidence label, blocked claims and safe next step. Live proof on
  2026-07-02 returned `proposal_count=2`, first target `Eko-Opieka / Eko
  Kalendarz`, `review_status=review_required`, `support_level=partial`,
  `risk_tier=medium`, `promotion_allowed=false`, `redacted=true`.
- Shared schemas now enforce the private proposal review/status contract:
  `review_status`, `support_level` and `risk_tier` are typed enums matching the
  Python `PrivateSourceProposal` literals, so dashboard and skill consumers
  reject invented private-proposal states before they reach operator output.
- Private proposal review now includes an API-owned promotion checklist in the
  Service Profile. Live proof after stack restart on 2026-07-01:
  `promotion_ready=false`, `promotion_checklist` has 5 items,
  `approved_count=0`, `review_required_count=2`. This tells Wilku what must be
  true before a private proposal can become a reviewed source fact, while still
  blocking automatic promotion.
- The `wilq-content-operator` UAT packet now includes live Service Profile
  evidence instead of only queue/enrichment items. Live proof on 2026-07-01:
  `uat_readiness.status=blocked_for_full_uat`,
  `recommended_scope=review/blokady i traceability`, gaps
  `gap_service_operat_wodnoprawny` and `gap_no_approved_current_cards`,
  `private_review_action_count=2`. It now also carries private proposal
  `promotion_ready=false`, the promotion blocked reason and the 5-item
  promotion checklist from Service Profile. Live proof on 2026-07-02 added
  `private_proposal_details`: 2 redacted details with support/risk/blocked
  claims and `promotion_allowed=false`. This prepares Goal 005 UAT without
  claiming that Wilku completed the session.
- A normal Wilku-ready UAT handoff now lives at
  `docs/handoffs/2026-07-01-wilku-content-uat-ready.md`. It condenses the live
  UAT packet into questions, current blockers, source trace IDs and result
  fields to fill during the actual session. It is preparation only, not UAT
  proof.
- `wilq-content-operator` non-interactive eval now requires refresh-first
  handling for stale brief decisions. The targeted proof at
  `.local-lab/evals/codex-skill/20260701T222739Z/summary.json` passed with
  `operator_usefulness_score=4`, `blocked=true`, six evidence IDs and explicit
  `refresh-first` / `dane wymagają odświeżenia` / `odśwież dane źródłowe`
  language. The eval prompt no longer seeds `ActionObject` into
  operator-facing output.
- Marketing brief `safe_next_actions` now mirrors refresh-first stale decision
  handling. Live proof after stack restart on 2026-07-01 showed Merchant,
  content refresh and WordPress draft handoff actions rendered as `kind=blocker`
  with `Odśwież dane przed akcją`, `refresh-first` summaries and concrete stale
  source labels before any review step.
- Goal 005 live refresh-first proof: WILQ API vendor reads refreshed the stale
  brief sources on 2026-07-01. Completed runs:
  `refresh_google_merchant_center_a04a45a6e6fd`,
  `refresh_ahrefs_5eee21244cff` and
  `refresh_wordpress_sklep_c1db9b8fa677`. After refresh,
  `/api/marketing/brief` dropped from 3 blockers to 1; Merchant and content
  refresh decisions became current metric/recommendation/action items instead
  of refresh-first blockers. Remaining blocker is GA4 claim safety, not stale
  source freshness.
- The Wilku-ready content UAT handoff
  `docs/handoffs/2026-07-01-wilku-content-uat-ready.md` is refreshed against
  the post-refresh live content-operator packet. It now uses the latest Ahrefs
  evidence `ev_refresh_refresh_ahrefs_5eee21244cff` and states that full UAT
  remains blocked by Service Profile/private-proposal review, not by stale
  Merchant/content sources.
- Goal 005 content UAT result proof now has a deterministic checker:
  `scripts/record_goal_005_content_uat_result.py`. It validates the filled
  session result fields for selected work item, blocker understanding, Service
  Profile readability, private review actions, source-trace questions,
  generic/off-brand findings, largest product gap and follow-up Beads when
  full UAT remains blocked. It renders a review report only; it does not
  promote private proposals, approve cards, unlock publishing or close Goal 005.
- Master roadmap for "better BDOS.ai" direction now lives at
  `docs/roadmap/bdos-class-wilq-master-roadmap.md`. Current overall WILQ
  maturity is estimated at `35-45%`: the API/safety/content workflow foundation
  is real, but reviewed Ekologus knowledge, Wilku UAT, claim-level generation
  safety, measurement provenance, BDOS-grade Ads/Merchant optimizers and write
  execution remain the large gaps.
- Public abandoned `ekologus-ai` reuse audit is recorded in
  `docs/audits/005-2026-07-01-ekologus-ai-reuse-audit.md` under Beads task
  `wilq-seo-5fd`. The reusable breakthrough is not the old CLI; it is the
  contract chain: source manifest -> evidence pack -> source claim markers ->
  generation gate -> quarantine -> post-output validation -> operator review ->
  marketer usefulness report. Port selected contracts into WILQ API; do not run
  `ekologus-ai` as a second product brain.
- API blocker cleared on 2026-07-01 in the local stack:
  `scripts/local_stack.sh start` restored `http://127.0.0.1:8000/api/health`
  and `http://127.0.0.1:5173/command-center`. `GET /api/metrics/status`
  reported DuckDB metrics enabled with `62339` metric facts and `4089` refresh
  runs before the fresh Goal 005 refreshes.
- Goal 005 live refresh proof: `POST /api/connectors/google_search_console/refresh`
  with `mode=vendor_read` completed as
  `refresh_google_search_console_27ca850b1fa4`; GA4 completed as
  `refresh_google_analytics_4_5ebc4ba1c966`; WordPress Ekologus completed in
  the backend as `refresh_wordpress_ekologus_691cbe6ab27d` after the local
  client timed out at 120 seconds. GA4 is now fresh and WordPress inventory has
  16 objects.
- `wilq-ga4-analyst` proof is recorded in
  `docs/handoffs/2026-07-01-ga4-traffic-quality-proof.md`. The skill smoke
  passed, `act_review_ga4_tracking_quality` validates, and the output correctly
  separates two GA4 measurement blockers from two `google / cpc` traffic-quality
  review candidates without claiming ROAS, revenue, profitability or conversion
  outcomes.
- AGENTS.md now makes WILQ API recovery an active operator duty: if local API or
  dashboard is unreachable, run the local stack manager, inspect logs/port
  owners, verify health/metrics/dashboard, and record a specific blocker instead
  of leaving "API unreachable" as a vague stop. It also raises the BDOS-class
  skill bar: deterministic smoke is not enough; realistic non-interactive Codex
  evals must prove that skill outputs use WILQ API evidence/action IDs, block
  unsafe claims and give a useful Polish next step.
- The skill eval layer now has an OpenAI-aligned contract in
  `docs/evals/openai-aligned-skill-evals.md`, a static coverage audit
  (`uv run python scripts/audit_skill_eval_coverage.py --strict`) and default
  non-interactive threshold `operator_usefulness_score >= 4`. Freshness handling
  is part of the gate: stale connector snapshots require refresh, repair path or
  blocker before recommendation.
- `wilq-content-operator` now has a realistic non-interactive eval case in
  `docs/evals/cases/wilq-skill-eval-cases.json`. Static coverage passes with
  all 13 WILQ skills covered. The first live Codex eval caught a useful harness
  issue: workflow gates without `action_id` must not be marked
  `validation_state="validated"`. `scripts/codex_skill_eval.sh` now states that
  rule explicitly. Fresh re-run passed at
  `.local-lab/evals/codex-skill/20260701T212839Z/summary.json` with
  `operator_usefulness_score=4`, `blocked=true`, six evidence IDs, two
  recommendations and six action candidates. The output preserved workflow
  gate states without fake ActionObject validation and blocked publish/final
  article/SEO success/lead/revenue/destructive-update claims.
- The `wilq-content-operator` eval case now requires Service Profile and
  private proposal promotion markers (`/api/content/service-profile`,
  `promotion_ready=false`, `promotion_checklist`, `reviewed source fact`).
  Its smoke script now fetches `GET /api/marketing/brief` and returns
  `brief_items` even when the live queue is blocked, keeping route context
  available for Codex evals.
- The `wilq-content-operator` non-interactive eval now also requires explicit
  Claim Ledger / generation-gate markers in actionable output: `Claim Ledger`,
  `claims_allowed`, `claim_markers`, `unsupported_claim_used` and
  `claim_missing_required_evidence`. This keeps operator answers from passing
  with generic content workflow prose that does not surface claim safety.
  Targeted proof passed at
  `.local-lab/evals/codex-skill/20260701T221439Z/summary.json` with
  `operator_usefulness_score=4`, `blocked=true`, 6 evidence IDs,
  2 recommendations and 6 action candidates.
- `/api/marketing/brief` is now refresh-first for stale daily decisions. If a
  ready decision depends on stale connector evidence, the brief surfaces it as a
  blocker, raises risk to medium and says to refresh stale sources before
  treating the item as an operational recommendation. Live proof after stack
  restart on 2026-07-01: the content refresh queue named only stale Ahrefs and
  WordPress sklep.ekologus.pl, while fresh GSC and WordPress ekologus.pl stayed
  out of the refresh-first source list.
- The Codex skill eval harness now supports `required_decision_terms_pl`; these
  markers must appear in actionable output, not only in `notes`. The hardened
  `wilq-content-operator` eval passed at
  `.local-lab/evals/codex-skill/20260701T213328Z/summary.json`.
- Content diagnostics decision ranking is now freshness-aware for secondary
  gap sources. If Ahrefs is stale while GSC and WordPress have fresh ready
  content evidence, `/api/content/diagnostics` promotes the GSC/WordPress
  `refresh_or_merge` decision above Ahrefs gap review. Live proof after stack
  restart on 2026-07-01: `google_search_console=fresh`,
  `wordpress_ekologus=fresh`, `ahrefs=stale`; top decision is
  `content_decision_https___www_ekologus_pl` with evidence
  `ev_refresh_refresh_google_search_console_b545c32e13f1` and
  `ev_refresh_refresh_wordpress_ekologus_691cbe6ab27d`.
- Draft variant selection guard is implemented in
  `wilq/content/drafts/variants.py`: variant results now expose
  `recommended_variant_id`, explicit comparison dimensions, `magic_score_used=false`
  policy and a safe next step. The guard recommends the preserve-first refresh
  for approved refresh work, keeps all variants non-publishable/non-WordPress,
  and compares by evidence coverage, service fit, buyer problem, CTA, duplicate
  risk and quality-review dependency instead of a fake score.
- Content measurement outcome provenance is hardened in
  `wilq/content/measurement/outcome.py`: observed metrics must now carry
  matching `work_item_id`, `measurement_window_id`, `content_url`,
  `metric_fact_ids`, `refresh_run_ids`, evidence IDs, allowed metric names and
  source connectors from the measurement window before WILQ can return
  directional or success states. Missing lineage fails closed as
  `insufficient_data`.
- Goal 006 candidate first gate slice is implemented: quality review now blocks
  `unsupported_claim_used` when a structured draft uses a claim that is not in
  the Claim Ledger at all. This closes the gap between "blocked claim leaked"
  and "new unsupported claim invented by output"; both now stop human-review
  readiness.
- Structured draft preview now blocks `unknown_claim_reference` before quality
  review when runtime output uses a claim absent from
  `contract.model_input.claims_allowed`. This catches invented output claims at
  the preview boundary, before they can look like a reviewable draft.
- Structured draft generation now exposes `claim_markers` in
  `contract.model_input`: claim ID, text, type, status, evidence IDs and
  reviewer ID from the Claim Ledger. `claims_allowed` stays for backward
  compatibility, but future gates can reason from typed source-claim-marker
  metadata instead of text-only claims.
- Structured draft preview now consumes `claim_markers`: if a section uses a
  claim whose marker requires evidence, that section must reference the marker
  evidence IDs or preview blocks with `claim_missing_required_evidence`. Text-only
  legacy contracts without `claim_markers` remain backward-compatible.
- Quality Review now applies the same claim-evidence guard at the final review
  boundary: a structured draft section that uses an `allowed_with_evidence`
  Claim Ledger entry must carry that claim's required evidence IDs, or review
  blocks with `claim_missing_required_evidence`.
- Claim Ledger source lineage is hardened: `allowed_with_evidence` entries now
  carry `source_connectors`, and any evidence-backed entry without a source
  connector blocks draft readiness with `missing_source_connector`. Work-item
  generated ledgers and structured draft claim markers preserve the connector
  lineage so later preview/review gates can show not just the evidence ID, but
  the data source behind it.
- Draft Package tests are realigned with the Claim Ledger source-connector
  contract: allowed evidence-backed fixture claims now carry source connectors,
  so the focused draft/claim/structured-generation chain passes under the same
  no-source-no-recommendation rule.
- Structured draft generation now carries `knowledge_constraints` from Sales
  Brief into `contract.model_input` and shared schemas. The runtime receives
  typed evidence requirements, blocked/review-required claim constraints and
  card lineage as contract data, not only prose in the system instruction.
- Structured draft preview now blocks
  `missing_forbidden_claim_acknowledgement` when model output does not list all
  `claims_removed_or_blocked` from the generation contract in
  `forbidden_claims_avoided`. This prevents the runtime from silently ignoring
  forbidden/removed claims while still passing preview.
- Quality Review now mirrors that same forbidden-claim acknowledgement gate, so
  direct quality-review calls cannot bypass preview by omitting
  `forbidden_claims_avoided` for claims removed or blocked by the draft package.
- Shared schemas now type `ContentQualityFinding.code` as the known quality gate
  enum instead of any string, including
  `missing_forbidden_claim_acknowledgement`. Dashboard/API tests now catch
  unregistered quality finding codes before they reach the UI.
- Shared schemas also type structured draft preview blocker codes with a
  preview-specific enum, so unknown preview gate codes are rejected before the
  dashboard treats them as valid workflow blockers.
- Shared `ContentWorkItemSchema` now mirrors Python workflow status literals for
  inventory, canonical, duplicate, preflight, artifact, human review, audit,
  WordPress handoff and measurement window states. Unknown workflow states are
  rejected before they can drive dashboard gates.
- Wilku content UAT handoff was refreshed on 2026-07-02 after the Claim Ledger
  connector hardening. Current skill proof still shows `candidate_count=3`,
  `actionable_candidate_count=1`, `queue_status=blocked` and
  `workflow_blocked=true`; therefore `wilq-seo-jst` remains open/in-progress
  until a real Wilku session or explicit owner defer is recorded.
- Quality-review API tests no longer depend on the current live
  `/api/content/work-items/snapshot` decision. They now build a deterministic
  BDO ready chain through the same Sales Brief, Draft Package and Structured
  Generation API helpers before review/revision assertions. Live snapshot
  semantics still need a separate follow-up because the freshness-ranked
  homepage decision can correctly block Sales Brief on missing service/CTA
  knowledge cards.
- Live content snapshot tests now distinguish diagnostic-derived snapshots from
  deterministic ready-chain fixtures. If the current freshness-ranked decision
  lacks service/CTA knowledge depth, the snapshot test expects
  `missing_required_knowledge_card`, no draft package and no structured
  contract instead of forcing a fake draft-ready state.
- WordPress draft handoff audit lineage is hardened: audit evidence must overlap
  with the approved human review evidence and draft package evidence map, or
  handoff blocks with `audit_evidence_mismatch`. Draft-only remains the only
  allowed WordPress path.
- Claim Ledger status/type consistency is hardened: forged entries can no
  longer mark guarantee claims, legal/risk/environmental claims without a
  reviewer, or SEO/performance/business-outcome claims without measurement as
  generally allowed. The shared ledger gate now blocks these before draft,
  quality-review or publish-ready helpers can treat them as safe.
- `wilq-ads-doctor` was tightened after a fresh Ads read
  `refresh_google_ads_be7011a4a261`: broad Ads prompts now require freshness
  handling and either full `GET /api/ads/diagnostics` or
  `context-pack full_context=true` before claiming a full review queue. The
  smoke proves default context-pack has 5 compacted decisions while full context
  has all 14 diagnostics decisions; non-interactive eval passed with
  `operator_usefulness_score=4`.
- Goal 005 Sales Brief v2 signal-quality audit is recorded in
  `docs/audits/005-2026-07-01-sales-brief-signal-quality.md`. That audit found
  `bdo co to` as the strongest UAT candidate at audit time, but current UAT
  preparation must follow live API state. Live queue proof on 2026-07-01 now
  shows `queue_status=blocked`, one actionable candidate
  `content_work_item_content_decision_https___www_ekologus_pl`, and no `bdo co
  to` item in the active queue. Use the live UAT packet and
  `docs/handoffs/2026-07-01-wilku-content-uat-ready.md` before presenting
  candidate choice to Wilku.
- Goal 005 waste-storage knowledge slice `wilq-seo-nlz` added
  `ekologus_public_waste_packaging_obligations_2026_07_01` as a commit-safe
  source fact compiled into `ekologus_service_waste_packaging_obligations`
  (`source_backed_review_required`). Live proof after stack restart:
  `magazynowanie odpadów` builds a Sales Brief with no blockers and
  `draft_allowed=false`; `operat wodnoprawny` still blocks with
  `missing_required_knowledge_card` until a direct public/reviewed source
  exists.
- Goal 005 blocked Ahrefs snapshot slice `wilq-seo-ad8` replaced the selected
  work-item snapshot HTTP 404 for blocked `beczki` with typed
  `blocked_snapshot`. Live proof: status 200, `recommended_mode=block`,
  blockers `duplicate_risk_unresolved`, `missing_inventory_resolution`,
  `missing_final_canonical`, `duplicate_gate_not_checked`, and no fake
  `preflight`/Sales Brief fields.
- Official Google Ads developer-toolkit sources are now tracked as WILQ Ads
  implementation patterns: MCP read-only account discovery/search/resource
  metadata, API Explorer live HTTP/JSON prototyping, Query Builder field
  discovery, Query Validator GAQL compatibility checks and Developer Assistant
  mission-control/skills architecture. They are patterns for WILQ API
  adapters/evals, not substitutes for WILQ evidence, ActionObjects or Google
  developer-token approval. Search Console API overview and Search Analytics
  guides are tracked as the wider GSC source beyond query/page metrics; WILQ GSC
  reads must account for date availability checks, typical 2-3 day delay,
  `rowLimit`/`startRow` paging and partial-detail caveats.
- Google Search Console vendor read now implements the first official
  Search Analytics pattern: it checks available dates with `dimensions=["date"]`,
  selects the latest available day, then reads `query,page` facts through
  bounded `rowLimit`/`startRow` paging. The adapter records availability and
  paging metadata instead of pretending a stale or missing day is complete data.
  The request now pins `type=web`, and persisted metric summaries mark
  `detail_dimensions=query,page` with `detail_data_completeness=partial_possible`
  so downstream skills do not treat detailed query/page rows as full traffic
  totals.
  Live proof `refresh_google_search_console_b545c32e13f1` completed on
  2026-07-01 with available range 2026-06-21..2026-06-30, detail date
  2026-06-29, 703 rows and `query_page_rows_truncated=false`.
- `wilq-gsc-content-doctor` now has the same Search Analytics caveat in smoke
  and non-interactive eval. Proof
  `.local-lab/evals/codex-skill/20260701T231227Z/summary.json` passed with
  `operator_usefulness_score=4`, six evidence IDs and a validated
  `act_prepare_content_refresh_queue`, while the output states that GSC
  query/page rows are `partial_possible` signals from the newest available day.
- `/api/content/diagnostics` now exposes an API-owned
  `gsc_search_analytics_contract` instead of requiring skills or dashboard
  code to scrape `latest_refreshes.metric_summary`. Live proof after stack
  restart returned `search_type=web`, `detail_dimensions=query,page`,
  `detail_data_completeness=partial_possible`, detail date `2026-06-29`,
  `rowLimit=250` and a Polish warning that query/page rows are not full traffic
  totals.
- The same API contract now carries official GSC operational caveats:
  `expected_data_delay_days_min=2`, `expected_data_delay_days_max=3`,
  `read_granularity=single_day_latest_available`,
  `api_recommended_page_size=25000` and
  `api_daily_row_cap_per_search_type=50000`. It also distinguishes the official
  Search Analytics paging model from WILQ's current safe internal cap
  `rowLimit=250` / `max rows=1000`. Non-interactive proof
  `.local-lab/evals/codex-skill/20260701T232526Z` passed after the oracle was
  tightened to require those caveats.
- Tactical queue now deduplicates metric facts by connector, metric name and
  dimensions before building items, choosing the newest collected fact. This
  prevents older GSC refresh evidence for the same `query,page` identity from
  polluting the current content decision metrics; section-level repetition of
  the same tactical item remains a view-model concern.
- Content diagnostics now uses the same latest-fact identity condensation
  before building sections and response evidence. `wilq-gsc-content-doctor`
  smoke after stack restart passed with the evidence trace reduced to 15
  current proof IDs instead of dozens of stale WordPress/GSC refresh IDs.
- `wilq-gsc-content-doctor` smoke now guards that content diagnostics includes
  the latest completed GSC vendor-read evidence and at most one
  `ev_refresh_refresh_google_search_console_*` ID. This turns the evidence
  condensation fix into a regression gate for future skill/API changes.
- User noted a separate private `krn-ekologus-brain` project and internal
  Ekologus knowledge bases. This is recorded as potential future source context
  only. It is not an active WILQ SEO integration and must not pull private
  client documents, attachments, emails or phone details into committed
  `wilq-seo` docs/cards. Follow-up: `wilq-seo-409`.
- Private `krn-ekologus-brain` source-catalog audit is recorded in
  `docs/audits/005-2026-07-01-ekologus-brain-source-catalog-audit.md` under
  Beads task `wilq-seo-409`. The reusable pattern is governed source intake:
  metadata-only catalog -> owner/audience/risk -> schema-gated condensation ->
  owner review -> import proof/eval. It should feed future local-only or
  redacted source proposals and read-only Service Profile review, not automatic
  RAG, raw private source facts, special packets or production-depth cards.
- Private source proposals now have an explicit design protocol in
  `docs/architecture/private-source-proposal-protocol.md` under Beads task
  `wilq-seo-wtf`. The proposal layer maps private materials to existing
  `ContentSourceFact` enums only after metadata-only intake, owner/audience/risk
  decision, schema-gated condensation, review and eval. It forbids raw private
  text, full paths, filenames, contact data and protected snippets in committed
  WILQ artifacts.
- Read-only Service Profile review surface is designed in
  `docs/architecture/service-profile-review-surface.md` under Beads task
  `wilq-seo-94k`. The proposed `GET /api/content/service-profile` view model
  aggregates existing knowledge cards/source facts into Polish review sections,
  coverage gaps, blocked write policy and non-persistent review requests.
  Direct card edits, fact promotion and private-source exposure stay blocked
  until a future ActionObject/audit path exists.
- Read-only Service Profile implementation is live under Beads task
  `wilq-seo-lmm`: `GET /api/content/service-profile` returns typed
  `read_only=true` coverage over existing knowledge cards/source facts, shared
  schemas parse the contract, and `/service-profile` renders Polish dashboard
  panels. Live smoke after stack restart returned
  `status=source_backed_review_required`, `service_card_count=6`, gaps
  `gap_service_operat_wodnoprawny` and `gap_no_approved_current_cards`, and
  `can_edit_cards=false`.
- Service Profile now surfaces redacted `ekologus-ai` private source proposals
  for review without compiling them into cards. Live proof after stack restart:
  `proposal_count=2`, `review_required_count=2`, `approved_count=0`,
  `redacted=true`, `ready_for_daily_content=false` and
  `production_depth_status=source_backed_review_required`.
- Goal 004: Content Operations Layer is completed under Beads epic
  `wilq-seo-2qq`. It delivered the safe content operations mechanics and typed
  architecture, not a proven daily-use content product: queue candidate -> opportunity
  enrichment -> typed Ekologus knowledge cards -> operations-grade Sales Brief
  -> claim-gated draft variants -> deterministic quality review -> bounded
  revision application -> human review -> audit -> WordPress draft-only handoff
  -> measurement window -> conservative outcome interpretation.
- Goal 004 planning slice `wilq-seo-xlw` is closed. Product slice
  `wilq-seo-6kd` froze the existing content workflow contract with a FastAPI
  route/response-model inventory test, a per-item `revision-plan` endpoint,
  dashboard API helper coverage for queue/snapshot/generation/quality/revision/
  review/audit/WordPress/measurement paths, and selected-work-item mutations for
  preview, quality review and revision plan.
- Goal 004 opportunity enrichment slice `wilq-seo-a3t` is implemented.
  `GET /api/content/work-items/{work_item_id}/enrichment` returns typed,
  evidence-bound `ContentOpportunityEnrichment` with intent, buyer problem,
  buyer trigger, service fit, CTA hypothesis, source facts, measurement
  baseline and typed blockers. `/content-workflow` renders this enrichment in
  Polish as a marketer-facing "why this topic matters" panel. The slice avoids
  broad RAG, fake scores and prompt-only keyword research; missing work items,
  missing evidence/source connectors, invalid dev canonical and missing service
  fit become blockers instead of recommendations.
- Goal 004 typed Ekologus knowledge cards slice `wilq-seo-dtj` is implemented.
  `GET /api/content/knowledge-cards` exposes typed service, CTA and evidence
  policy cards with source lineage, confidence, freshness and claim rules.
  Sales Brief now requires a matching knowledge-card set before drafting: no
  service/CTA/evidence policy match becomes a blocker instead of a prompt-only
  workaround. This is still typed cards/rules, not broad RAG.
- Goal 004 operations-grade Sales Brief slice `wilq-seo-8xc` is implemented.
  Sales Brief v2 now requires opportunity enrichment, consumes enrichment-owned
  buyer problem, buyer trigger, service fit, CTA hypothesis, source facts and
  measurement baseline, and exposes operations context, knowledge constraints
  and measurement boundary fields through shared schemas. Missing or blocked
  enrichment blocks the brief instead of falling back to seed-only prose.
- Goal 004 draft variants slice `wilq-seo-ao0` is implemented.
  `POST /api/content/work-items/draft-variants` returns typed variants for
  preserve-first refresh, problem-led, service-led and FAQ/supporting paths.
  Each variant wraps the existing Structured Outputs generation contract after
  Sales Brief, Claim Ledger and Draft Package gates, keeps `publish_ready=false`
  and exposes `wordpress_write_allowed=false`. Fake SDK runtime proof confirms
  the variant contract can generate structured output without bypassing WILQ.
- Goal 004 bounded revision application slice `wilq-seo-a09` is implemented.
  `POST /api/content/work-items/revision-apply` and the selected work-item
  variant turn a bounded revision plan into a versioned diff only after an
  updated quality review is supplied. Revision application is evidence-bound,
  cannot free-regenerate, keeps `publish_ready=false` and
  `wordpress_write_allowed=false`, and selected routes reject wrong-work-item
  requests before any application result.
- Goal 004 WordPress draft-only adapter boundary slice `wilq-seo-03a` is
  implemented. `ContentWordPressDraftExecutionResult` now exposes an explicit
  execution boundary: allowed operation is only `create_wordpress_draft`,
  dry-run is the default, API responses report whether live write and an
  adapter are configured, and `publish_allowed=false` plus
  `destructive_update_allowed=false` are part of the typed contract. The public
  API still blocks live writes by default; the domain-level live proof requires
  an explicit adapter and still passes only a `post_status=draft` payload.
- Goal 004 conservative measurement outcome interpreter slice `wilq-seo-prk`
  is implemented. `POST /api/content/work-items/measurement-outcome` returns a
  typed interpretation with statuses `not_ready`, `insufficient_data`,
  `noisy_inconclusive`, `directional_improvement`, `likely_underperformance`
  and `measured_success`. The interpreter refuses early claims before
  `earliest_verdict_date`, requires observed values plus evidence IDs, keeps
  directional signals separate from public success claims, and records
  limitations so WILQ does not pretend full causality.
- Goal 004 WILQ content operator skill/UAT harness slice `wilq-seo-wr4` is
  implemented. `.agents/skills/wilq-content-operator` is an operator workflow
  over WILQ API, not a writer skill: it uses content queue, selected snapshot,
  enrichment, knowledge cards, structured runtime, quality review, revision
  application, human review, WordPress draft-only execution and measurement
  outcome endpoints while forbidding direct OpenAI calls, direct WordPress
  calls, `publish_ready=true`, dev canonical usage and early success claims.
  Historical smoke proved a BDO selected refresh item, but current live queue
  state has moved. The UAT harness now prints a live 3-5 item Wilku packet from
  API queue/enrichment plus Service Profile readiness instead of relying on a
  static BDO control payload.
- Goal 004 UI/API hardening slice `wilq-seo-4wi` is implemented. First green
  sub-slice tightens the dashboard API boundary: content workflow POST helpers
  now validate shared Zod request schemas instead of accepting `unknown`, API
  errors include HTTP status/detail with a timeout boundary, and shared schemas
  expose typed preflight, sales brief, draft package, human review, WordPress
  draft handoff and measurement window requests. Second green sub-slice removes
  the route-to-route import between Ads Doctor and Custom Segments by moving the
  shared custom segment panels into `components/AdsCustomSegmentPanels.tsx`.
  Third green sub-slice introduces `components/DiagnosticSurfaceShell.tsx` and
  migrates Demand Gen onto it as the first diagnostic shell pilot without
  moving product logic into React. Fourth green sub-slice migrates Ahrefs onto
  the same shell, shrinking duplicated route chrome while keeping Ahrefs
  decisions, evidence and blocked-claim handling in the route/API data. Fifth
  green sub-slice migrates Localo onto the same shell, so the shared diagnostic
  chrome now covers Demand Gen, Ahrefs and Localo while Localo safety/evidence
  decisions remain API-data driven in the route. Sixth green sub-slice adds
  `components/SafetyGatePanel.tsx` and migrates the Demand Gen and Localo
  guard/evidence sections onto it without changing API-owned safety data.
  Seventh green sub-slice adds `components/DiagnosticDecisionCard.tsx` and
  migrates Ahrefs/Localo decision cards onto it while keeping domain-specific
  traces, metric facts and blocked claims in route/API data. Eighth green
  sub-slice extracts pure Ads number/cost/percentage/status formatting into
  `lib/adsFormatting.ts` with focused tests, reducing Ads Doctor utility
  ownership before broader panel extraction. Ninth green sub-slice extracts
  the Ads negative-keyword candidate panel into
  `components/AdsNegativeKeywordCandidatesPanel.tsx`, centralizes campaign/ad
  group fallback labels in `lib/adsLabels.ts`, and keeps the static Ads route
  guard checking `preview_card`/`payload_preview` invariants across the route
  and extracted panel. Tenth green sub-slice extracts Ads search-term summary,
  n-gram, safety and keyword-context tables into
  `components/AdsSearchTermPanels.tsx`, reducing Ads Doctor route ownership and
  carrying the static source guards over to the extracted module. Eleventh
  green sub-slice extracts Ads campaign metric, triage and derived-KPI panels
  into `components/AdsCampaignPanels.tsx`, moves campaign channel/status
  fallback labels into `lib/adsLabels.ts`, and keeps source guards pointed at
  the new module. Twelfth green sub-slice extracts Ads budget pacing, shared
  budget distribution, recommendation, impression-share and change-history
  panels into `components/AdsBudgetRecommendationPanels.tsx`, moves budget/date/
  preview fallback labels into `lib/adsLabels.ts`, and keeps static source guards
  pointed at the extracted module for budget/recommendation fields and
  `preview_card`/`payload_preview` safety. Thirteenth green sub-slice extracts
  Ads business target interpretation and change-impact readiness panels into
  `components/AdsBusinessReadinessPanels.tsx`, moves change-id/campaign-metric
  fallback labels into `lib/adsLabels.ts`, and reduces Fallow changed-scope
  duplication from 15 to 7 clone groups while keeping the same static source
  guards. Fourteenth green sub-slice extracts Ads operator summary, start-here
  decisions, optimizer readiness and decision cards into
  `components/AdsOperatorSummaryPanels.tsx`, keeping source guards on the
  extracted module and reducing `AdsDoctorSurface.tsx` to 628 lines. Fifteenth
  green sub-slice extracts the full Ads metric/evidence and diagnostic-table
  composer into `components/AdsMetricEvidencePanel.tsx`, keeps static guards on
  the extracted module, and reduces `AdsDoctorSurface.tsx` to 442 lines while
  Fallow changed-scope duplication drops to 6 clone groups. Sixteenth green
  sub-slice extracts the first-screen Ads overview/condensed-decision panels
  into `components/AdsOverviewPanels.tsx`, keeps source guards on the extracted
  module, and reduces `AdsDoctorSurface.tsx` to 275 lines. Seventeenth green
  sub-slice consolidates scattered static copy/source/status tests into
  `routes/operatorSafetyGuards.test.ts`, preserving the operator-safety
  assertions while removing misleading `*Copy`, `*Source` and badge-usage test
  names from the route tree. Eighteenth green sub-slice exposes connector scope
  clarity through existing API-owned `risk_notes`: WordPress now says
  inventory/draft-only handoff with publish/destructive updates blocked, Localo
  says access is not ranking/GBP-write proof, social publishing remains outside
  the current content workflow, and the Registry renders these notes without
  React inventing connector readiness. `risk_notes` stay out of compact Codex
  context-packs so skill contexts do not receive raw technical note copy. This
  keeps frozen schema files clean. Final broad gate passed with
  `rtk scripts/verify.sh`.
- Goal 004 broad proof passed with `rtk scripts/verify.sh` after the UI/API
  hardening and connector-scope cleanup. Next work should come from
  `bd ready --json`; do not reopen Goal 004 without an explicit new Beads task
  or regression.
- Goal 004 must keep WILQ API as the product brain. Codex may orchestrate and
  evaluate through `wilq-content-operator`, but must not become the production
  writer, direct OpenAI caller or direct WordPress client.
- Goal 001 cleanup is no longer blocked by missing UAT input because the owner
  explicitly deferred real marketer UAT until WILQ has a stronger content
  production workflow.
- Goal 002: Content Production Engine bez slopu is completed as the first safe
  content draft-preparation layer.
- Goal 003: Content Quality Workbench is completed under Beads epic
  `wilq-seo-u6u`. The goal was not "more writing"; it is multi-item content
  queue, gated live Structured Outputs, deterministic quality review,
  evidence-bound revision planning, Polish marketer workflow and draft-only
  WordPress boundary.
- WILQ may now be described as a safe content draft-preparation workflow for
  one diagnostics-derived Ekologus item: evidence, inventory/canonical check,
  duplicate gate, preflight, preserve-first plan, sales brief, rejestr twierdzeń,
  draft package, human review, audit, WordPress draft-only handoff/execution
  dry-run and measurement window are covered by a focused end-to-end proof. It
  must still not be described as an autopublisher, live WordPress writer or
  success-claiming content engine.
- WILQ must not wait for post-publication metrics before preparing useful
  content work. Every content item should get a measurement plan up front, and
  later GSC/GA4/Ahrefs/Ads/Merchant/Localo signals should become interpretation
  inputs, not a blocker for writing the brief or draft. Success/failure claims
  remain blocked until the measurement window has usable data.
- Production content generation must use WILQ runtime code through the OpenAI
  API SDK with Structured Outputs and strict schemas. `codex exec` is reserved
  for repository work, deterministic skill smokes, non-interactive evals,
  adversarial operator checks and local orchestration; it must not become the
  production writer or a second product brain.
- Goal 002 Beads epic `wilq-seo-zu4` is closed.
- Goal 003 plan lives in `docs/goals/archive/003-goal.md`.
- Goal 003 recovery and plan alignment task `wilq-seo-ik5` is closed. First
  implementation slice `wilq-seo-d7c` added the API-owned multi-item content
  queue at `GET /api/content/work-items/queue`. The queue currently derives 5
  candidates from content diagnostics: 4 actionable refresh candidates with
  public final canonical URLs and one Ahrefs review candidate blocked because
  it has no final canonical URL. Dev/preview URLs are rejected as final
  canonical targets.
- Goal 003 per-item state slice `wilq-seo-cdy` is closed. It added
  selected-work-item snapshot, human review and audit endpoints:
  `GET /api/content/work-items/{work_item_id}/snapshot`,
  `POST /api/content/work-items/{work_item_id}/human-review` and
  `POST /api/content/work-items/{work_item_id}/audit`. Tests prove review/audit
  for item A do not unlock item B, and blocked queue items do not receive fake
  workflow snapshots. Final sub-slice added item-scoped structured draft preview
  and quality-review endpoints plus store persistence for `StructuredDraftOutput`
  and `ContentQualityReview`; tests prove output/quality state for item A does
  not appear on item B and mismatched `work_item_id` requests are rejected.
- Goal 003 deterministic quality review slice `wilq-seo-b5x` is closed.
  `POST /api/content/work-items/quality-review` returns `ContentQualityReview`
  with verdict, blockers, dimension statuses, revision instructions, evidence
  IDs and source connectors. It blocks missing section evidence, forbidden
  claims, `publish_ready` draft packages, unresolved duplicate risk and missing
  measurement windows; weak CTA returns revision instructions instead of a fake
  SEO score. The first version is schema/rule-based and does not use an LLM
  judge.
- Goal 003 revision plan slice `wilq-seo-56w` is closed.
  `POST /api/content/work-items/revision-plan` turns `ContentQualityReview`
  findings into bounded revision instructions. It allows only explicit
  `needs_changes` fixes, returns `no_changes_needed` for clean drafts and stays
  blocked when quality review has hard blockers such as missing measurement,
  claim risk or duplicate/canonical risk.
- Goal 003 gated live Structured Outputs slice `wilq-seo-8qd` is closed as a
  proof/typing slice. Existing runtime tests prove live generation is disabled
  by default, live mode without SDK client is blocked, fake SDK strict output is
  parsed, `publish_ready=false` is preserved and no WordPress write/publication
  is attempted.
- Goal 003 dashboard queue slice `wilq-seo-0xv` is closed. `/content-workflow`
  now reads the API-owned content queue, lets Wilku select a candidate, shows
  blocked candidates without creating fake snapshots, uses selected
  `work_item_id` snapshot/review/audit paths, exposes structured draft preview,
  deterministic quality review and bounded revision-plan panels in Polish
  marketer language, and keeps WordPress dry-run/draft-only copy visible. React
  renders queue/quality/revision contracts from WILQ API and does not reconstruct
  claim logic or final canonical semantics.
- Goal 002 anti-slop baseline proof lives in
  `docs/handoffs/2026-06-30-goal-002-anti-slop-baseline.md`.
- `scripts/audit_complexity.py` now reports Python LOC, largest files,
  functions, classes and frozen-file growth risk. Latest Goal 003 changed-code
  audit reports 253 Python files, 91,397 non-empty Python LOC, 6 changed files
  and no changed frozen growth files in the current slice.
- The historical full Ruff and mypy blockers that stopped repo-level verify
  after Goal 003 closure have been cleared. Remaining anti-slop work should use
  changed-file budgets and focused Beads tasks, not broad drive-by cleanup.
- Latest Goal 003 dashboard proof:
  `pnpm -C apps/dashboard exec vitest run src/routes/ContentWorkflowSurface.test.tsx`,
  `pnpm --filter @wilq/dashboard lint`,
  `pnpm -C apps/dashboard typecheck`, `pnpm fallow:audit`,
  `uv run python scripts/audit_complexity.py --changed --allow-frozen` and
  `git diff --check` passed. An attempted `pnpm --filter @wilq/dashboard test
  -- src/routes/ContentWorkflowSurface.test.tsx` ran the full dashboard suite
  instead of the target file and hit unrelated existing failures in
  `ActionDetailRoute.test.tsx` and `App.test.tsx`; the precise Vitest command
  above is the valid proof for this slice.
- Goal 003 adversarial content eval slice `wilq-seo-0t7` is closed and pushed.
  `tests/content/test_content_workflow_adversarial_gates.py`
  now attacks dev URL as canonical, missing evidence/source connector, missing
  preflight, missing rejestr twierdzeń, missing measurement window, `publish_ready=true`,
  forbidden guarantee claims, WordPress publish/live write, premature measurement
  outcome claims and wrong-work-item human review. The slice found and fixed a
  real generation gap: Structured Outputs generation now checks
  `content_workflow_blockers(item, "prepare_draft")` before trusting supplied
  brief/claim/draft payloads, so forged payloads cannot bypass missing workflow
  state.
- Goal 003 anti-slop budget slice `wilq-seo-9l1` is closed and pushed.
  `scripts/audit_complexity.py --changed` now fails changed Python
  files that exceed the current per-slice budgets: file > 800 LOC, function >
  100 lines, function > 25 branches or class > 300 lines. Frozen growth files
  remain a separate blocker. `tests/test_audit_complexity.py` covers budget
  detection, unchanged legacy hotspot exclusion and clean budget reporting.
- Goal 003 final focused proof passed on 2026-07-01:
  `uv run pytest tests/content -q`,
  `uv run pytest tests/test_audit_complexity.py -q`,
  `pnpm -C apps/dashboard exec vitest run src/routes/ContentWorkflowSurface.test.tsx`,
  `pnpm --filter @wilq/dashboard lint`,
  `pnpm -C apps/dashboard typecheck`, `pnpm fallow:audit`,
  `uv run python scripts/audit_complexity.py --changed --limit 5` and
  `git diff --check`.
- Full repo-level verification passed on 2026-07-01 with `rtk scripts/verify.sh`.
  Proof covered full Python tests (`483 passed, 1 warning`), dashboard/unit
  tests (`102 passed`), security/dependency checks, API smoke, skill structure
  smoke, skill API smoke, Playwright dashboard proof (`14 passed`) and
  dashboard production build. Beads task `wilq-seo-8re` can be closed.
- Goal 002 content domain extraction has started under `wilq-seo-x4u`.
  Canonical/public URL semantics moved from
  `wilq/briefing/content_diagnostics.py` to `wilq/content/canonical/urls.py`.
  This is behavior-preserving extraction: focused canonical tests, two content
  diagnostics contract tests, Ruff, mypy for the new module, import-boundary
  smoke and `git diff --check` passed.
- Goal 002 content preflight verdict helpers moved from
  `wilq/briefing/content_diagnostics.py` to
  `wilq/content/preflight/verdicts.py`. This is behavior-preserving extraction:
  focused preflight tests, canonical tests, two content diagnostics contract
  tests, Ruff, mypy for the new module, import-boundary smoke,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed.
- Goal 002 content inventory gate rules moved from
  `wilq/briefing/content_diagnostics.py` to
  `wilq/content/inventory/gates.py`. This is behavior-preserving extraction:
  focused inventory gate tests, preflight tests, canonical tests, two content
  diagnostics contract tests, Ruff, mypy for the new module, import-boundary
  smoke, `scripts/audit_complexity.py --changed --allow-frozen` and
  `git diff --check` passed. Unused private WordPress inventory detail helpers
  were deleted instead of moved to a new module.
- Goal 002 content planning decision helpers moved from
  `wilq/briefing/content_diagnostics.py` to
  `wilq/content/planning/decisions.py`. This is behavior-preserving extraction:
  focused planning tests, inventory gate tests, preflight tests, canonical tests,
  two content diagnostics contract tests, Ruff, mypy for the new module,
  import-boundary smoke, `scripts/audit_complexity.py --changed --allow-frozen`
  and `git diff --check` passed.
- Goal 002 GSC content decision construction moved from
  `wilq/briefing/content_diagnostics.py` to
  `wilq/content/planning/decisions.py`. This is behavior-preserving extraction:
  focused planning tests now cover `gsc_content_decisions`, preserve-first
  handling and dev-preview URL rejection as canonical; the same content
  diagnostics contract tests, Ruff, mypy, import-boundary smoke,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed.
- Goal 002 GA4 tracking-gap content blocker moved from
  `wilq/briefing/content_diagnostics.py` to
  `wilq/content/measurement/decisions.py`. This is behavior-preserving
  extraction: focused measurement tests now cover GA4 tracking gaps as
  measurement blockers, not content rewrite recommendations. The same content
  diagnostics contract tests, Ruff, mypy, import-boundary smoke,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed.
- Goal 002 Ahrefs gap review decision construction moved from
  `wilq/briefing/content_diagnostics.py` to
  `wilq/content/planning/ahrefs.py`. This is behavior-preserving extraction:
  focused Ahrefs planning tests now cover relevant/off-topic filtering,
  candidate rows, GSC/WordPress overlap labels and blocked growth claims. The
  same content diagnostics contract tests, Ruff, mypy, import-boundary smoke,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed.
- Goal 002 GSC/WordPress vendor-read blocker moved from
  `wilq/briefing/content_diagnostics.py` to
  `wilq/content/preflight/vendor_read.py`. This is behavior-preserving
  extraction: focused vendor-read tests now cover blocker reasons, refresh
  evidence fallback and the `block_until_vendor_read` decision. The same content
  diagnostics contract tests, Ruff, mypy, import-boundary smoke,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed.
- Goal 002 marketer-facing content preflight/decision view construction moved
  from `wilq/briefing/content_diagnostics.py` to
  `wilq/content/preflight/marketer_view.py`. This is behavior-preserving
  extraction: focused marketer-view tests now cover preserve-first copy, draft
  blocking with sales brief allowance, concrete gate labels and generic unknown
  claim labels. The same content diagnostics contract tests, Ruff, mypy,
  import-boundary smoke, `scripts/audit_complexity.py --changed --allow-frozen`
  and `git diff --check` passed.
- Goal 002 content API view-model label helpers moved from
  `wilq/briefing/content_diagnostics.py` to
  `wilq/content/view_models/labels.py`. This is behavior-preserving
  extraction: content connector status labels, refresh labels, metric labels,
  live-data status copy and label hydration for diagnostic sections now have a
  content-domain home. `tests/content` (32 tests), four content diagnostics API
  contract tests, Ruff, mypy, import-boundary smoke,
  `scripts/audit_complexity.py --changed --allow-frozen` and
  `git diff --check` passed.
- Goal 002 content diagnostic section builders moved from
  `wilq/briefing/content_diagnostics.py` to
  `wilq/content/view_models/sections.py`. This is behavior-preserving
  extraction: the GSC query/page section, WordPress inventory match section and
  content action safety section now have a content-domain home. `tests/content`
  (36 tests), four content diagnostics API contract tests, Ruff, mypy,
  import-boundary smoke, `scripts/audit_complexity.py --changed --allow-frozen`
  and `git diff --check` passed.
- Goal 002 content operator summary helpers moved from
  `wilq/briefing/content_diagnostics.py` to
  `wilq/content/view_models/summary.py`. This is behavior-preserving
  extraction: the operator summary, query/page count, matched inventory count
  and Ahrefs/WordPress overlap count now have a content-domain home.
  `tests/content` (39 tests), four content diagnostics API contract tests,
  Ruff, mypy, import-boundary smoke,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed.
- Beads task `wilq-seo-x4u` is closed. The content diagnostics extraction
  baseline is complete enough to move from cleanup into product workflow slices.
  The Goal 002 feature slices that followed this baseline are now closed. Goal
  003 is also closed; use `bd ready --json` for the next unblocked cleanup or
  product work.
- Beads task `wilq-seo-wiz` is closed. `wilq/content/workflow/models.py` now
  defines a typed `ContentWorkItem` and workflow blockers for evidence, source
  connectors, inventory, public final canonical URL, duplicate gate, preflight,
  preserve-first plan, sales brief, rejestr twierdzeń, draft package, human review,
  audit and measurement window. Draft and WordPress handoff require a
  measurement plan up front, while outcome claims stay blocked until the
  measurement window is ready. `tests/content` (46 tests), Ruff, mypy,
  import-boundary smoke, `scripts/audit_complexity.py --changed --allow-frozen`
  and `git diff --check` passed.
- Beads task `wilq-seo-acy` is closed. `wilq/content/inventory/records.py` now
  defines Content Inventory v1 records and resolution: public URL/canonical,
  optional preview URL, source connectors, evidence IDs, preserve-first mode,
  duplicate-risk blockers and create-after-review only after a clear duplicate
  check. Focused tests cover existing public URL, missing final canonical, dev
  preview as invalid canonical, unresolved duplicate risk, clear duplicate
  create candidate and canonical deduplication. `tests/content` (52 tests),
  Ruff, mypy, import-boundary smoke,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed.
- Beads task `wilq-seo-jih` is closed. `wilq/content/preflight/workflow.py`
  now exposes a ContentPreflight v2 verdict over `ContentWorkItem` and Content
  Inventory v1 with `blocked`, `plan_allowed`, `brief_allowed`,
  `draft_allowed` and `handoff_allowed` states. Preflight still does not draft
  or write; it only exposes allowed next stages, blockers and disabled reasons.
  Focused tests cover no evidence, missing connector, missing final canonical,
  dev preview as canonical, existing content preserve-first, duplicate risk,
  missing brief, missing human review and full handoff allowed.
  `tests/content` (61 tests), Ruff, mypy, import-boundary smoke,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed.
- Beads task `wilq-seo-wxm` is closed. `wilq/content/claims/ledger.py` now
  defines Claim Ledger v1 with typed claim kinds, statuses, evidence IDs,
  reasons and optional reviewer. Deterministic rules block guarantee claims,
  block SEO/performance/business outcome claims until measurement is ready,
  require human review for legal/risk/environmental claims and block
  `allowed_with_evidence` entries without evidence. `tests/content` (67 tests),
  Ruff, mypy, import-boundary smoke,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed.
- Beads task `wilq-seo-pnz` is closed. `wilq/content/briefs/sales.py` now
  defines Sales Brief v1 as a typed contract built from `ContentWorkItem`,
  ContentPreflight v2, Content Inventory v1, Claim Ledger v1 and explicit
  source facts. The brief contains buyer problem, buyer trigger, target reader,
  search intent, service fit, final canonical URL, existing content plan,
  H1/H2/FAQ/CTA direction, internal link direction, forbidden claims, missing
  evidence and measurement plan. Focused tests prove no brief is produced
  without required evidence/source facts, valid final URL semantics, preflight
  allowance or measurement plan. `tests/content` (74 tests), Ruff, mypy,
  import-boundary smoke, `scripts/audit_complexity.py --changed --allow-frozen`
  and `git diff --check` passed.
- Beads task `wilq-seo-dhf` is closed. `wilq/content/drafts/package.py` now
  defines Draft Package v1 as an outline-first, not-publish-ready artifact.
  Draft packages require a `draft_allowed` preflight verdict, matching Sales
  Brief, matching Claim Ledger and source-fact evidence mapping. The package
  includes `brief_id`, `claim_ledger_id`, sections, section-to-evidence map,
  publish-ready claims, removed/blocked claims, human review questions and
  `publish_ready=false`. `tests/content` (78 tests), Ruff, mypy,
  import-boundary smoke, `scripts/audit_complexity.py --changed --allow-frozen`
  and `git diff --check` passed.
- Beads task `wilq-seo-4b5` is closed. `wilq/content/review/human.py` now
  defines Human Review v1 as a typed review record for sales brief, claim
  ledger, draft package and WordPress handoff stages. Review records require a
  reviewer, decision, checked items, evidence IDs and handled blocked claims.
  Only `approved` review can update a `ContentWorkItem` to
  `human_review_status=approved`; `needs_changes`, `rejected` and `deferred`
  keep WordPress handoff blocked. Focused tests prove review without reviewer,
  checklist or evidence is blocked, blocked claims must be handled and approved
  draft review updates workflow state for the WordPress handoff gate.
  `tests/content` (83 tests), Ruff, mypy, import-boundary smoke,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed.
- Beads task `wilq-seo-qsf` is closed. `wilq/content/handoff/wordpress.py`
  now defines WordPress Draft Handoff v1 as a prepare-only, draft-only handoff
  contract. It requires a public final canonical URL, matching Draft Package,
  approved Human Review and audit envelope with evidence IDs. It blocks dev
  preview URLs as canonical, missing audit, non-approved review, mismatched
  draft packages and any publish-ready draft package. The handoff emits
  `post_status=draft`, `publish_allowed=false` and
  `destructive_update_allowed=false`; workflow state becomes `prepared` until a
  real WordPress post ID exists, then `draft_created`. `tests/content`
  (88 tests), Ruff, mypy, import-boundary smoke,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed.
- Beads task `wilq-seo-w18` is closed. `wilq/content/measurement/window.py`
  now defines Content Measurement Window v1 with baseline period, observation
  period, earliest verdict date, allowed metrics, source connectors, evidence
  IDs, optional WordPress handoff link and status. Measurement windows block
  dev preview URLs as measured canonical targets, require at least one allowed
  metric and source connector, and keep `success_claim_allowed=false` until the
  observation window is ready for review. Focused tests prove WordPress handoff
  needs or schedules a measurement window and outcome claims remain blocked
  before `earliest_verdict_date`. `tests/content` (92 tests), Ruff, mypy,
  import-boundary smoke, `scripts/audit_complexity.py --changed --allow-frozen`
  and `git diff --check` passed.
- Goal 002 content workflow API bridge started under `wilq-seo-bl3`.
  `wilq/content/workflow/api.py` now exposes a typed request/response for
  `ContentWorkItem` preflight over Content Inventory v1. New endpoint
  `POST /api/content/work-items/preflight` lives in
  `apps/api/wilq_api/routers/content_workflow.py`, calls the domain inventory
  resolver and ContentPreflight v2 verdict builder, preserves evidence IDs and
  source connectors, and blocks dev preview URLs as final canonical. Existing
  `GET /api/content/preflight` shape remains unchanged. Focused API tests,
  Ruff, mypy, `scripts/audit_complexity.py --changed --allow-frozen` and
  `git diff --check` passed.
- Goal 002 Sales Brief API bridge started under `wilq-seo-asw`.
  `POST /api/content/work-items/sales-brief` now computes inventory resolution
  and ContentPreflight v2, then calls the typed Sales Brief v1 builder from
  `wilq/content/briefs/sales.py`. It returns the preflight verdict and
  `sales_brief_result` without creating draft packages or WordPress handoffs.
  Focused API tests prove a valid preserve-first item produces a source-fact
  and measurement-backed brief, missing source facts block the brief, and
  forbidden claims from Claim Ledger remain visible in the brief. Ruff, mypy,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed.
- Goal 002 Draft Package API bridge started under `wilq-seo-1tc`.
  `POST /api/content/work-items/draft-package` now computes inventory
  resolution and ContentPreflight v2, builds or accepts Sales Brief v1, then
  calls the typed Draft Package v1 builder from
  `wilq/content/drafts/package.py`. It returns `draft_package_result` with an
  outline-first, `publish_ready=false` package or typed blockers; it does not
  create WordPress handoffs. Focused API tests prove valid draft package
  creation, preflight-not-draft-allowed blocking, Claim Ledger blocking and
  section-to-evidence mapping. Ruff, mypy,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed.
- Goal 002 Human Review API bridge started under `wilq-seo-5mr`.
  `POST /api/content/work-items/human-review` now calls the typed Human Review
  v1 blockers and updates `ContentWorkItem` only after blocker-free review. The
  response includes `reviewed_item`, blockers and `wordpress_handoff_allowed`,
  but it does not create WordPress handoffs. Focused API tests prove approved
  draft review updates workflow state, missing reviewer/checklist/evidence
  blocks review, `needs_changes` blocks handoff and unhandled blocked claims
  keep handoff disabled. Ruff, mypy,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed.
- Goal 002 WordPress Draft Handoff API bridge started under `wilq-seo-24b`.
  `POST /api/content/work-items/wordpress-draft-handoff` now calls the typed
  WordPress Draft Handoff v1 builder and returns a prepare-only, draft-only
  handoff contract or typed blockers. It does not call WordPress, create a post,
  publish content or allow destructive updates. Focused API tests prove valid
  prepared handoff, missing-audit blocker, non-approved review blocker, dev
  canonical blocker, `publish_allowed=false`, `destructive_update_allowed=false`
  and evidence preservation. Ruff, mypy,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed.
- Goal 002 Measurement Window API bridge started under `wilq-seo-44e`.
  `POST /api/content/work-items/measurement-window` now calls the typed Content
  Measurement Window v1 builder and returns a planned observation window or
  typed blockers. The response applies `measurement_window_status/id` to the
  returned work item only when a window is created and exposes outcome blockers
  while `success_claim_allowed=false`. Focused API tests prove valid planned
  window after handoff, missing-metrics blocker, missing-source-connector
  blocker, dev canonical blocker, early outcome blocker and evidence
  preservation. Ruff, mypy and
  `scripts/audit_complexity.py --changed --allow-frozen` passed.
- Goal 002 API chain smoke started under `wilq-seo-8tu`. A focused
  fixture-backed API test now calls the content work item endpoints in order:
  preflight, Sales Brief, Draft Package, Human Review, WordPress draft handoff
  and Measurement Window. The proof asserts evidence IDs persist,
  `publish_ready=false`, WordPress `publish_allowed=false`,
  `destructive_update_allowed=false`, Measurement Window
  `success_claim_allowed=false` and early outcome blockers are present. Focused
  pytest, Ruff, `scripts/audit_complexity.py --changed --allow-frozen` and
  `git diff --check` passed.
- Goal 002 dashboard API boundary started under `wilq-seo-qso`. Shared Zod
  schemas now parse ContentWorkItem workflow responses for preflight, Sales
  Brief, Draft Package, Human Review, WordPress draft handoff and Measurement
  Window. Dashboard `api.ts` now has thin POST helpers for the matching
  `/api/content/work-items/*` endpoints, with tests proving each helper calls
  the API-owned path. The new schema work lives in
  `packages/shared-schemas/src/contentWorkflow.ts`, not in React route logic.
- Goal 002 marketer-facing content workflow route started under
  `wilq-seo-rtt`. Dashboard route `/content-workflow` now renders a first
  controlled content production path from the existing API-owned workflow
  contracts: preflight, Sales Brief, Draft Package, Human Review, WordPress
  draft handoff and Measurement Window. The view shows WordPress as draft-only,
  keeps outcome claims blocked until the measurement date and hides raw endpoint
  paths/schema names from the marketer-facing surface. It does not generate
  content, publish to WordPress or add behavior to `ContentDiagnosticSurface`.
  Focused dashboard route tests, dashboard typecheck, dashboard lint,
  `pnpm fallow:audit` and `git diff --check` passed.
  Focused Vitest suites, package typecheck/lint, Fallow audit and
  `git diff --check` passed. Fallow still reports inherited duplicate groups in
  the older shared `index.ts`, but the audit gate found no new changed-file
  issues.
- Goal 002 API-owned content workflow snapshot started under `wilq-seo-93p`.
  `GET /api/content/work-items/snapshot` now derives the first content workflow
  snapshot from `build_content_diagnostics().decision_queue` instead of a
  hardcoded BDO control payload. Dashboard `/content-workflow` fetches that API
  snapshot instead of constructing workflow payloads locally in React. The
  diagnostics-derived snapshot is now stage-aware: it keeps `review=null`,
  blocks WordPress handoff with `missing_human_review`/`missing_audit`, plans
  measurement without a handoff ID and keeps success/failure claims blocked.
  Shared Zod schemas parse the snapshot shape, and tests prove evidence/source
  connectors persist, final canonical stays on Ekologus public URLs and
  WordPress cannot receive a draft until real review evidence exists. The
  previous public control-snapshot endpoint and backend `_control_*` payload
  helpers were removed.
- Beads task `wilq-seo-s0u` adds the first persisted Human Review path for the
  diagnostics-derived snapshot. `POST /api/content/work-items/snapshot/human-review`
  stores only a valid review for the current work item in local SQLite state.
  Later `GET /api/content/work-items/snapshot` applies that real review, while
  WordPress handoff remains null/blocked until an audit envelope exists. Wrong
  work-item review is rejected and not stored as approval.
- Beads task `wilq-seo-di8` adds the persisted audit envelope path for the
  diagnostics-derived snapshot. After a real stored review,
  `POST /api/content/work-items/snapshot/audit` stores only a matching audit
  envelope and later snapshot reads can return a prepare-only WordPress handoff
  contract with `post_status=draft`, `publish_allowed=false` and
  `destructive_update_allowed=false`. Mismatched audit is not stored as handoff
  approval, and measurement success/failure claims remain blocked.
- Beads task `wilq-seo-pr9` wires that review/audit path into the
  `/content-workflow` dashboard. The route can now submit Human Review and a
  matching audit through typed WILQ API helpers, then refetches the API-owned
  snapshot. React still does not decide handoff readiness, write to WordPress,
  publish or create destructive updates.
- Beads task `wilq-seo-6l1` cleans the API-owned operator messages for human
  review and WordPress draft handoff blockers. The domain contracts now explain
  missing review, draft package, audit and dev-canonical blockers in Polish
  marketer language; tests guard against jargon leaking back into blocker
  labels, reasons and next steps.
- Beads task `wilq-seo-3y8` cleans the remaining content workflow blocker
  messages for workflow state, preflight, inventory, draft package and claim
  ledger domains. Operator-facing blocker labels, reasons, next steps and
  review questions no longer use English workflow jargon such as Sales Brief,
  Claim Ledger, Draft Package, human review, handoff, publish-ready, work item,
  evidence ID or final canonical URL.
- Beads task `wilq-seo-vr4` adds a separate WordPress draft execution contract
  for Goal 002. `POST /api/content/work-items/wordpress-draft-execution` can
  return a draft-only dry-run payload after a valid WordPress handoff and
  matching draft package. It keeps `post_status=draft`, `publish_allowed=false`,
  `destructive_update_allowed=false` and `external_write_attempted=false`.
  Live write mode is explicitly blocked until a future adapter is enabled.
- Beads task `wilq-seo-ee2` wires the WordPress draft dry-run into the
  `/content-workflow` dashboard and shared TS schemas. After review/audit and a
  prepared handoff, the route can ask WILQ API for a dry-run preview, show that
  WordPress would receive only a draft, and keep publication/destructive update
  disabled.
- Beads task `wilq-seo-bkr` moves the ordered Content Workflow step wording
  into the WILQ API snapshot as `operator_steps`. The dashboard now renders
  those API-owned marketer labels/statuses instead of building local workflow
  step semantics in React.
- Beads task `wilq-seo-ffk` reduces `ContentSelectedDecisionPanel` complexity
  without changing content dashboard behavior or product rules. The selected
  content decision panel now uses a small view model plus focused rendering
  components instead of one large React function. Focused route tests,
  dashboard typecheck, dashboard lint and Fallow changed audit passed.
- Beads task `wilq-seo-rob` adds the first structured draft generation
  contract for the future OpenAI SDK runtime. The new content-domain contract
  builds a strict schema, model input and instructions only after matching
  Sales Brief, Claim Ledger and Draft Package gates. It does not call OpenAI,
  write to WordPress or mark content publish-ready. Focused structured draft
  tests, full `tests/content`, Ruff, mypy, complexity audit and
  `git diff --check` passed.
- Beads task `wilq-seo-up9` exposes that structured draft generation contract
  through WILQ API and shared dashboard schemas. New
  `POST /api/content/work-items/structured-draft-generation` returns a typed
  strict-schema contract or typed blockers; dashboard `api.ts` has only a thin
  parser/helper. This still does not call OpenAI, generate prose, write to
  WordPress or mark content publish-ready.
- Beads task `wilq-seo-sap` adds a safe OpenAI Structured Outputs runtime
  dry-run. The new content-domain adapter builds a `responses.create` payload
  with strict `json_schema`, blocks live mode unless a separately audited
  adapter enables it, and parses fake structured outputs in tests. New
  `POST /api/content/work-items/structured-draft-runtime` exposes only the
  dry-run/live-block contract; it still does not call OpenAI from the WILQ API,
  generate prose, write to WordPress or mark content publish-ready.
- Beads task `wilq-seo-r2k` adds shared TypeScript schemas and a dashboard
  `api.ts` helper for the structured draft runtime endpoint. The dashboard now
  has a typed boundary for dry-run/live-block runtime responses without adding
  UI product logic, label mappers, live OpenAI calls or WordPress writes.
- Beads task `wilq-seo-2tv` exposes the structured draft runtime dry-run in the
  marketer-facing `/content-workflow` route. The workflow snapshot now includes
  API-owned structured generation status, and the dashboard can check draft
  readiness through the typed dry-run endpoint without showing raw OpenAI
  payloads, calling the model live, writing to WordPress or publishing content.
- Beads task `wilq-seo-63l` adds a gated OpenAI SDK client boundary for the
  structured draft runtime. The runtime still defaults to dry-run, live mode
  stays blocked unless `WILQ_OPENAI_STRUCTURED_DRAFT_LIVE_ENABLED=true`, missing
  SDK/API-key state returns a typed blocker, and tests prove a fake SDK client
  can return a strict structured draft with `publish_ready=false`. This does not
  create a WordPress draft, write to WordPress or publish anything on
  `ekologus.pl`.
- Beads task `wilq-seo-n0b` adds a structured draft preview contract before
  WordPress handoff. `POST /api/content/work-items/structured-draft-preview`
  turns strict `StructuredDraftOutput` into a marketer-facing preview only when
  the output still maps to WILQ evidence, has no claims needing review and keeps
  `publish_ready=false`. This preview does not create a WordPress draft, does
  not write to WordPress and does not publish anything on `ekologus.pl`.
- Beads task `wilq-seo-17z` wires that structured draft preview into the
  `/content-workflow` dashboard route. The marketer can request "Podgląd treści"
  only after generated structured output exists, see the evidence-mapped title,
  sections and human review checklist, and still cannot write to WordPress or
  publish on `ekologus.pl`.
- Beads task `wilq-seo-wfw` adds a focused end-to-end API proof for Goal 002.
  The test starts from the diagnostics-derived `/api/content/work-items/snapshot`
  item, verifies evidence/source connectors and public Ekologus canonical URL,
  exercises structured draft runtime dry-run, structured draft preview, human
  review, audit, WordPress draft execution dry-run and measurement blockers.
  The proof asserts `post_status=draft`, `publish_allowed=false`,
  `destructive_update_allowed=false`, `external_write_attempted=false` and
  `success_claim_allowed=false`; nothing is published on `ekologus.pl`.
- Beads task `wilq-seo-bw9` strengthens that proof against the exact PLANS.md
  completion chain. The end-to-end test now asserts inventory/canonical
  resolution, duplicate check, initial preflight blockers, preserve-first plan,
  draft-allowed transition, sales brief facts, approved rejestr twierdzeń, ready draft
  package, structured draft evidence mapping, human review, audit, draft-only
  WordPress handoff/execution dry-run and the measurement blocker. No WordPress
  write or publication is attempted.
- Goal 002 API router extraction has started under `wilq-seo-hdl`. Read-only
  connector endpoints moved from `apps/api/wilq_api/main.py` to
  `apps/api/wilq_api/routers/connectors.py` without changing endpoint paths or
  response shapes. The first slice left connector refresh POST in `main.py`
  until cache invalidation could be extracted safely. Focused connector API
  tests, route-shape smoke, Ruff, mypy for the new router,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed.
- Goal 002 jobs router extraction moved `/api/jobs*` and `/api/job-runs*`
  endpoints from `apps/api/wilq_api/main.py` to
  `apps/api/wilq_api/routers/jobs.py` without changing endpoint paths or
  response shapes. Focused scheduler tests, jobs route-shape smoke, Ruff, mypy,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed.
- Goal 002 evidence/metrics router extraction moved `/api/evidence*` and
  `/api/metrics*` read endpoints from `apps/api/wilq_api/main.py` to
  `apps/api/wilq_api/routers/evidence.py` and
  `apps/api/wilq_api/routers/metrics.py` without changing endpoint paths or
  response shapes. Focused evidence/metrics API tests, route-shape smoke, Ruff,
  mypy, `scripts/audit_complexity.py --changed --allow-frozen` and
  `git diff --check` passed.
- Goal 002 knowledge/expert router extraction moved `/api/knowledge*` and
  `/api/expert*` endpoints from `apps/api/wilq_api/main.py` to
  `apps/api/wilq_api/routers/knowledge.py` and
  `apps/api/wilq_api/routers/expert.py` without changing endpoint paths or
  response shapes. Context-pack compaction helpers remain in `main.py` for a
  later scoped extraction. Focused knowledge/expert API tests, route-shape
  smoke, Ruff, mypy, `scripts/audit_complexity.py --changed --allow-frozen`
  and `git diff --check` passed.
- Goal 002 workflow router extraction moved `/api/workflows*` and
  `/api/workflow-runs*` endpoints from `apps/api/wilq_api/main.py` to
  `apps/api/wilq_api/routers/workflows.py` without changing endpoint paths or
  response shapes. Focused workflow API tests, route-shape smoke, Ruff, mypy,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed.
- Goal 002 system router extraction moved root, `/api/health` and
  `/api/system/status` endpoints from `apps/api/wilq_api/main.py` to
  `apps/api/wilq_api/routers/system.py` without changing endpoint paths or
  response shapes. Focused system API tests, route-shape smoke, Ruff, mypy,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed.
- Goal 002 opportunities router extraction moved `/api/opportunities*`
  endpoints from `apps/api/wilq_api/main.py` to
  `apps/api/wilq_api/routers/opportunities.py` without changing endpoint paths
  or response shapes. Context-pack construction still calls
  `list_opportunities()` directly until context runtime extraction. Focused
  opportunities API tests, route-shape smoke, Ruff, mypy,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed.
- Goal 002 diagnostics router extraction moved `/api/dashboard/command-center`,
  `/api/marketing/*`, `/api/ads/diagnostics`, `/api/merchant/diagnostics`,
  `/api/content/*`, `/api/ga4/diagnostics`, `/api/localo/diagnostics` and
  `/api/ahrefs/diagnostics` from `apps/api/wilq_api/main.py` to
  `apps/api/wilq_api/routers/diagnostics.py` without changing endpoint paths
  or response shapes. At that slice, Demand Gen diagnostics stayed in `main.py`
  until its context-heavy readiness builder could be wrapped safely. Focused
  diagnostics API tests, route-shape smoke, Ruff, mypy, dashboard tests,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed. The touched Localo contract fixture now expects the current
  `token obecny` label instead of the outdated shorter form.
- Goal 002 actions/audit router extraction moved `/api/actions*`,
  `/api/audit/events` and `/api/action-mutation-audits` from
  `apps/api/wilq_api/main.py` to `apps/api/wilq_api/routers/actions.py`
  without changing endpoint paths or response shapes. The router receives
  `clear_api_view_model_caches` as an injected callback, so validation, review,
  preview, confirm, impact-check and apply still clear dashboard/context caches
  after mutating state. Focused action API tests, route-shape smoke, Ruff, mypy,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed. At that slice, `main.py` still kept connector refresh, Demand Gen
  diagnostics and Codex/context endpoints.
- Goal 002 connector refresh router extraction moved
  `POST /api/connectors/{connector}/refresh` from `apps/api/wilq_api/main.py`
  to `apps/api/wilq_api/routers/connectors.py` without changing endpoint path
  or response shape. The connector router now receives
  `clear_api_view_model_caches` as an injected callback, so refresh still clears
  dashboard/context caches after collecting state. Focused connector API tests,
  route-shape smoke, Ruff, mypy, `scripts/audit_complexity.py --changed
  --allow-frozen` and `git diff --check` passed. `main.py` now keeps only
  Demand Gen diagnostics and Codex/context endpoints.
- Goal 002 Demand Gen diagnostics router extraction moved
  `/api/demand-gen/diagnostics` from `apps/api/wilq_api/main.py` to
  `apps/api/wilq_api/routers/demand_gen.py` without changing endpoint path or
  response shape. The router receives the existing readiness builder as an
  injected callback; the context-heavy builder remains in `main.py` for a later
  scoped context extraction. Focused Demand Gen API/context tests, route-shape
  smoke, Ruff, mypy, `scripts/audit_complexity.py --changed --allow-frozen`
  and `git diff --check` passed. At that slice, `main.py` still kept only
  Codex/context endpoints.
- Goal 002 Codex router extraction moved `/api/codex/context`,
  `/api/codex/context-pack` and `/api/codex/runs` from
  `apps/api/wilq_api/main.py` to `apps/api/wilq_api/routers/codex.py`
  without changing endpoint paths or response shapes. `ContextPackRequest`
  now lives in `apps/api/wilq_api/context_models.py`. The router receives the
  existing `context_pack` callable as an injected builder; heavy context-pack
  construction remains in `main.py` for a later runtime extraction. Focused
  Codex/context API tests, route-shape smoke, Ruff, mypy,
  `scripts/audit_complexity.py --changed --allow-frozen` and
  `git diff --check` passed. `main.py` no longer declares direct route
  handlers.
- Beads task `wilq-seo-hdl` is closed. Remaining heavy context-pack runtime
  extraction is tracked separately as `wilq-seo-462`, so router extraction is
  not conflated with context-pack internals.
- Goal 002 context-pack runtime extraction started under `wilq-seo-462`.
  `apps/api/wilq_api/context_cache.py` now owns request-skill parsing and the
  skill context-pack cache. `main.py` still owns heavy context-pack builder and
  compaction helpers, so `wilq-seo-462` remains open. Focused context-pack
  tests passed for daily action preview audit, metric-invention instruction and
  content strategist scoping. A lowercase audit-summary copy mismatch was fixed
  while preserving response meaning.
- `apps/api/wilq_api/context_scopes.py` now owns skill connector, keyword,
  action, knowledge-card and expert-rule scope maps. `main.py` still consumes
  those maps while the heavy diagnostics/context builders await extraction.
  Focused context-pack tests passed again for daily action preview audit,
  metric-invention instruction and content strategist scoping.
- `apps/api/wilq_api/context_knowledge.py` now owns skill-scoped knowledge-card
  and expert-rule selection plus scope text matching. `main.py` now calls that
  runtime module instead of keeping these helpers locally. Focused context-pack
  tests passed for daily action preview audit, metric-invention instruction,
  content strategist scoping and raw-history compaction. `wilq-seo-462` remains
  open because the heavy context-pack builders and compaction helpers still need
  extraction.
- `apps/api/wilq_api/context_actions.py` now owns full-context action selection,
  skill action scoping and connector action filtering. `main.py` preserves the
  previous ordering of action collection before diagnostics, then delegates
  filtering to the runtime module. The custom-segment context-pack test now
  asserts the current anti-slop contract: the diagnostic read contract can keep
  technical safety fields, while compact skill action plans hide
  `safety_contract` and expose marketer-readable status/check labels instead.
  Focused Ads/custom-segment/Demand Gen/context-pack tests, Ruff, mypy,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed.
- `apps/api/wilq_api/context_compaction.py` now owns shared context-pack
  compaction helpers for first-sentence trimming, raw vendor-mode stripping,
  audit-event summaries, metric facts and dimension labels. `tests/test_api_contracts.py`
  now imports those helpers from the runtime module instead of `main.py`.
  Focused context-pack/metric/audit tests, Ruff, mypy,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed. `main.py` still owns domain-specific context builders and larger
  action/diagnostic compaction functions, so `wilq-seo-462` remains open.
- `apps/api/wilq_api/context_compaction.py` also now owns neutral context-pack
  utility helpers for text truncation, recursive metric-fact removal, nested
  list lookup, simple metric-value lookup and numeric fallback. Focused
  context-pack/metric/audit tests, Ruff, mypy,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed. This is still behavior-preserving context runtime extraction, not new
  content product behavior.
- `apps/api/wilq_api/context_trace.py` now owns context traceability helpers for
  daily evidence IDs, daily source connectors, skill-scoped evidence IDs,
  recursive value collection and connector-scope intersection. Focused
  context-pack tests, Ruff, mypy,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed.
- `apps/api/wilq_api/context_merchant.py` now owns Merchant skill context
  compaction: decision queue summaries, issue cluster summaries, safe Merchant
  context IDs and Merchant preview compaction. The shared priority-list helper
  moved to `apps/api/wilq_api/context_compaction.py`, and `main.py` no longer
  keeps Merchant context helper copies. Focused Merchant/context-pack tests,
  Ruff, mypy for touched API files, `scripts/audit_complexity.py --changed
  --allow-frozen` and `git diff --check` passed.
- `apps/api/wilq_api/context_ga4.py` now owns GA4 skill context compaction and
  the Demand Gen context path reuses that module instead of a local `main.py`
  helper. Focused GA4/Demand Gen context-pack tests, Ruff, mypy for touched API
  files, `scripts/audit_complexity.py --changed --allow-frozen` and
  `git diff --check` passed.
- `apps/api/wilq_api/context_ahrefs.py` now owns Ahrefs skill context
  compaction. Connector-status, refresh-run and labelled-contract compaction
  helpers moved to `apps/api/wilq_api/context_compaction.py`, and the
  `test_api_contracts.py` import was moved off the old private `main.py`
  helper. Focused Ahrefs/context-pack tests, Ruff/mypy for touched API files,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed. Full Ruff on the historical `test_api_contracts.py` monolith still
  has existing line-length debt and was not broadened in this slice.
- `apps/api/wilq_api/context_marketing.py` now owns compact marketing brief,
  tactical queue and social draft context shaping for Codex context-pack
  payloads. `main.py` delegates daily marketing brief compaction, social skill
  diagnostics and social publisher scoped context to that runtime module.
  Focused daily/social context-pack tests, Ruff/mypy for touched API files,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed.
- `apps/api/wilq_api/context_content.py` now owns Content Planner, GSC content
  doctor and campaign-builder landing context shaping for Codex context-pack
  payloads. `main.py` delegates content diagnostics compaction, Ahrefs-filtered
  GSC context and landing-page candidate context to that runtime module. Focused
  content/GSC/campaign-builder context-pack tests, Ruff/mypy for touched API
  files, `scripts/audit_complexity.py --changed --allow-frozen` and
  `git diff --check` passed.
- `apps/api/wilq_api/context_ads.py` now owns Ads Doctor, Ads lite, custom
  segments and campaign-candidate context compaction for Codex context-pack
  payloads. `main.py` delegates Ads, custom-segment, campaign-builder Ads
  context and Demand Gen Ads-lite shaping to that runtime module. Focused
  Ads/custom-segment/campaign-builder/Demand Gen context-pack tests, Ruff/mypy
  for touched API files, `scripts/audit_complexity.py --changed --allow-frozen`
  and `git diff --check` passed.
- `apps/api/wilq_api/context_demand_gen.py` now owns Demand Gen context-pack
  diagnostics and readiness-contract construction used by both the skill
  context and `/api/demand-gen/diagnostics`. `main.py` delegates the Demand Gen
  router builder and skill payload to that runtime module. Focused Demand Gen
  context-pack and diagnostics tests, Ruff/mypy for touched API files,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed.
- `apps/api/wilq_api/context_action_payload.py` and
  `apps/api/wilq_api/context_action_previews.py` now own compact action payload
  and preview-card shaping for Codex context packs. `main.py` delegates daily
  action review-gate compaction and skill `active_action_objects` compaction to
  those runtime modules instead of keeping the action payload helpers locally.
  Focused daily/action/content/GSC/Ads/custom-segment/campaign-builder/Demand
  Gen/social context-pack tests, Ruff/mypy for touched API files,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed.
- `apps/api/wilq_api/context_daily.py` now owns the daily-command context pack,
  daily action compaction, daily command-center compaction and shared
  opportunity/evidence/knowledge/expert operator summaries used by skill
  context packs. `main.py` delegates `wilq-daily-command` context construction
  and skill scoped summaries to that runtime module instead of keeping daily
  helper internals locally. The audit-event summary contract was aligned to the
  existing operator-label test expectation with a capitalized second sentence.
  Focused daily/context-pack/operator-label tests, Ruff/mypy for touched API
  files, `scripts/audit_complexity.py --changed --allow-frozen` and
  `git diff --check` passed.
- `apps/api/wilq_api/context_skill.py` now owns skill-scoped context-pack
  orchestration, skill diagnostics dispatch and skill opportunity filtering.
  `main.py` delegates non-daily skill context packs to that runtime module
  instead of keeping the per-skill routing, evidence collection and redaction
  flow locally. Focused context-pack tests for content, GSC, Ads, custom
  segments, campaign builder, Demand Gen, social, knowledge and expert
  summaries passed with Ruff, mypy, `scripts/audit_complexity.py --changed
  --allow-frozen` and `git diff --check`.
- `apps/api/wilq_api/context_full.py` now owns full-context context-pack
  assembly for explicit full-context Codex requests. `main.py` delegates the
  full-context fallback to that runtime module instead of importing domain
  diagnostics, evidence, connector refresh, knowledge, expert-rule and
  redaction builders directly. Focused full-context tests, Ruff/mypy for
  touched API files, `scripts/audit_complexity.py --changed --allow-frozen`
  and `git diff --check` passed. Beads task `wilq-seo-462` is ready to close
  because `main.py` now owns app wiring and context-pack dispatch only.

## Latest Verified Product State

- Command Center, shared evidence freshness, GA4/Merchant freshness and Ads
  recommendation impact copy no longer turn unknown/missing data into bare
  `brak danych`, `brak odczytu` or a false zero-cost impact. Live
  `/api/dashboard/command-center` scan is clean, and focused API/dashboard
  checks plus marketer/context/operator language guards passed.
- `docs/goals/001-goal.md` has been pruned after closing Beads issue
  `wilq-seo-6rw.4`; raw-label cleanup is no longer listed as an active broad
  task. Future cleanup should start from fresh Fallow/browser/API evidence,
  context-pack guard failures or UAT findings.
- Action preview, Content, GA4 and tactical WordPress labels no longer use bare
  `brak`/`brak danych` fallbacks for missing review, URL, WordPress-match,
  percentage or Ads custom-segment values. They now describe the unconfirmed
  fact at API/schema/domain source, and no React label remapper was added.
  Focused API tests, dashboard route tests, ruff I/F, marketer/context/operator
  language guards, live API proof and `git diff --check` passed.
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
- `typescript` has been upgraded to `6.0.3`. Workspace typecheck, full
  dashboard test suite, lint, production build, Fallow changed-file audit,
  marketer/context-pack language guards and browser proof for `/command-center`
  passed after the upgrade.
- `zod` has been upgraded to `4.4.3`. Shared schemas now use explicit
  `z.record(z.string(), valueSchema)` contracts required by Zod 4, the action
  review gate has an explicit default state, and live shared-schema smoke uses
  a realistic timeout for heavier WILQ API endpoints. Workspace typecheck,
  shared-schema tests, live shared-schema smoke, full dashboard tests, lint,
  production build, Fallow changed-file audit, marketer/context-pack language
  guards and browser proof for `/command-center` passed after the upgrade.
- `tailwindcss` has been upgraded to `4.3.1` with `@tailwindcss/postcss`.
  Dashboard CSS now uses the Tailwind v4 import path with the existing config
  explicitly loaded. Dashboard typecheck, full dashboard test suite, lint,
  production build, Fallow changed-file audit, marketer/context-pack language
  guards, browser proof for `/command-center` and generated CSS proof for WILQ
  custom colors passed after the upgrade.
- `vite`, `vitest` and `@vitejs/plugin-react` have been upgraded to current
  major versions (`vite@8.1.0`, `vitest@4.1.9`,
  `@vitejs/plugin-react@6.0.3`). Shared schemas explicitly include Node types
  for the live schema smoke environment. Workspace typecheck, workspace tests,
  live shared-schema smoke, dashboard lint/build, Fallow changed-file audit,
  marketer/context-pack language guards, `pnpm outdated` and browser proof for
  `/command-center` passed after the upgrade.
- JS workspace dependencies are current as of 2026-06-29.
- Fallow is wired through `.fallowrc.json` and root package scripts. Dead-code
  and dependency hygiene are clean; full structural cleanup still has inherited
  dashboard duplication and complexity debt.
- Active dashboard/API/skill cleanup removed the worst slash-combined labels,
  stale dev-preview placement semantics, a hybrid Merchant sample-readiness
  field, misleading review wording, raw route slugs in action reasons and
  technical registry fallback language from primary surfaces.
- `scripts/live_contract_smoke.py` guards live content diagnostics against
  stale dev-preview URL and migration-era semantics.
- `tests/test_operator_endpoint_language_guard.py` now guards the main
  operator endpoints against stale route names, dev-preview/migration
  semantics and action-model jargon in serialized API output.
- Active dev-preview/migration semantics audit is closed in Beads
  (`wilq-seo-6rw.3`). Current active API/dashboard/schema/skill code no longer
  exposes dev preview as a final/canonical content target; remaining matches are
  guard/smoke tests or historical plan text. Focused operator endpoint/content
  URL tests, marketer language guard and live contract smoke passed.
- Merchant diagnostics active API contract now uses `change_preview` instead
  of `payload_preview`; `/api/merchant/diagnostics`, the Merchant context pack
  compaction and the Merchant skill smoke no longer expose `payload` wording.
- Google Ads connector versioning now documents why the REST endpoint stays on
  the major `v24` path while v24.2 capabilities enter WILQ as explicit read or
  review contracts. A focused contract test prevents accidental `v24.2`/`v24_2`
  endpoint churn.
- Codex context-pack compaction no longer builds operator-facing evidence
  summaries, knowledge-card titles or audit summaries from raw connector,
  source, card or event types. Focused API contract coverage guards those
  fallbacks.
- Central operator summary labels now explain decision limits instead of
  returning bare `brak ...` placeholders. Missing sources, evidence, actions,
  knowledge, required evidence, lineage, blocked promises and credential source
  summaries tell the marketer whether the item is safe to treat as a
  recommendation. Focused API/dashboard tests, marketer/context-pack language
  guards, dashboard typecheck/lint and `git diff --check` passed.
- Shared dashboard fallbacks now defend themselves: missing status labels,
  empty trace rows, empty registry lists, action audit history, opportunity
  metrics and knowledge/playbook lists explain what remains unsafe instead of
  serving a bare missing-state label. Focused dashboard tests, dashboard
  typecheck/lint, marketer language guard and `git diff --check` passed.
- Demand Gen metric rows now expose self-defending marketer labels from the
  typed API/schema contract. The dashboard no longer renders generic `brak`
  fallbacks or local Ads cost/GA4 percent formatters for Demand Gen metrics.
  Focused API/dashboard/shared-schema tests, dashboard typecheck/lint,
  marketer language guard and `git diff --check` passed.
- Demand Gen readiness now builds from Ads summary diagnostics instead of the
  full Ads cockpit. Direct/TestClient proof returns in about two seconds. A
  temporary HTTP timeout was traced to orphaned `agent-browser`/headless Chrome
  processes hammering the dashboard after Vite restarted; after closing them
  and restarting the canonical stack, `/api/health` returned in 0.001 s and
  `/api/demand-gen/diagnostics` returned in 1.47 s.
- Marketer-facing empty states now have to defend the decision surface: action
  evidence, action preview blockers, review conditions, workflow outcomes,
  brief workflow evidence, expert rule action mapping and evidence source
  references explain what the missing state means instead of showing bare
  `brak` placeholders. Focused dashboard tests, dashboard typecheck/lint,
  marketer language guard and `git diff --check` passed.
- Action validation, confirmation, effect-check and Tactical Queue empty states
  now explain the decision limit when errors, warnings, sources, evidence or
  actions are missing. These panels no longer use context-free `brak błędów`,
  `brak ostrzeżeń`, `brak dowodów do pokazania` or `brak akcji do sprawdzenia`
  as the operator-facing answer. Focused dashboard tests, dashboard
  typecheck/lint, marketer language guard and `git diff --check` passed.
- Content Planner empty states now explain why missing preflight inputs,
  similar URLs, preview URL, decision modes, evidence, GSC overlap or WordPress
  overlap limit the recommendation. The dashboard explicitly says not to treat
  a dev host as canonical and not to start writing without the content check.
  Focused content dashboard tests passed.
- Merchant empty states now explain the operational limit when scope, actions,
  decision source, data sources, evidence, validation inputs, issue types,
  product context or sample titles are missing. The route no longer uses
  `empty="brak..."` copy and its focused route test guards against regressions.
  Dashboard typecheck/lint, marketer language guard and `git diff --check`
  passed.
- GA4, Brief Workflow, Localo, Ahrefs and Custom Segments empty states now use
  decision-limit language instead of bare `brak...` placeholders. The copy
  clarifies when data is only context, when a recommendation is not justified,
  and when human review is still required. Focused source test, dashboard
  typecheck/lint, marketer language guard and `git diff --check` passed.
- Ads Doctor empty states now explain missing metrics, review, evidence,
  actions, source conditions, allowed uses, blocked uses, policy and human
  review as decision limits. Active dashboard routes/components no longer
  contain `empty="brak..."`, `?? "brak"` or `|| "brak"` fallbacks. Focused Ads
  source test, dashboard typecheck/lint, marketer language guard and
  `git diff --check` passed.
- GA4 action summary, Ads optimizer readiness, negative-keyword safety, workflow
  run history and connector-status fallbacks now explain the operational
  consequence of missing labels or runs. The dashboard says when a panel is not
  a list of actions, when a process is not executed automation, and when source
  status must be refreshed before judging readiness. Focused dashboard tests,
  typecheck/lint, marketer language guard and `git diff --check` passed.
- Content Planner preflight tiles and compact utility-route blockers no longer
  use bare `brak` wording for unavailable states. Missing content preflight now
  says `nie pisz` / `bramka niedostępna`, while utility routes explain what must
  not be done from that view. Focused route tests, dashboard typecheck/lint,
  marketer language guard and `git diff --check` passed.
- Ads field-level fallbacks for missing latest read, campaign channel/status,
  budget proposal, preview, date, campaign, ad group, change ID and campaign
  metrics now say what the operator must not infer or do. The Ads route no
  longer turns these missing fields into context-free missing-state answers in
  the active surface. Focused Ads dashboard tests, typecheck/lint, marketer
  language guard and `git diff --check` passed.
- Marketing brief Ads summaries are now condensed at API source. The brief keeps
  one metric observation, uses short action summaries for Ads actions and keeps
  the profitability/write blocker in the focus item instead of repeating the
  full Ads diagnosis across sections. Focused marketing-brief API tests,
  live `/api/marketing/brief` proof, marketer/context-pack language guards and
  `git diff --check` passed.
- Content metric tiles no longer show a bare missing-state word when a metric
  value is unavailable. They say `metryka niepotwierdzona`, while the Treści
  route continues to explain actual blockers and next safe steps in the page
  flow. Focused content dashboard tests, marketer language guard,
  `git diff --check` and browser proof for `/content-planner` passed.
- Shared metric chips no longer say `zmiana: brak` when a delta exists but the
  trend direction is not confirmed. They explain `zmiana: kierunek
  niepotwierdzony`, with a focused component test and browser proof that Localo
  metric chips still render correctly in the live dashboard.
- Merchant primary-surface fallbacks for report counts, problem resolution and
  product samples no longer use bare `brak` copy. Missing counts and samples now
  state what remains unconfirmed before product-file review. Focused Merchant
  source/render tests, marketer language guard, `git diff --check` and browser
  proof for `/merchant` passed.
- Ads missing status/channel fallbacks now come from API/domain labels instead
  of bare status/channel placeholders. Missing campaign status, channel type and
  keyword status explain that the state is unconfirmed. Focused pytest, App route
  test, ruff import/name checks, marketer language guard and browser proof for
  `/ads-doctor` passed.
- Ads change-history resource, operation and change-source fallbacks now explain
  unconfirmed state from API/domain labels instead of context-free missing
  placeholders. Focused Ads API tests, ruff import/name checks, marketer and
  context-pack language guards, live Ads diagnostics proof and `git diff --check`
  passed.
- Action detail validation no longer uses context-free `brak` answers. The
  validation result now says that WILQ did not report errors or warnings, so the
  positive empty state is tied to an actual check.
- Action detail safety-record fields now use API-owned labels for mutation
  audit status, write attempt, external write path and audit trace. The review
  panel shows concrete states such as `nie próbowano zapisu w systemie
  zewnętrznym`, `brak bezpiecznej ścieżki zapisu` and `ślad bezpieczeństwa
  zapisany` instead of local `brak` fallbacks. Focused action API tests,
  action-panel/detail route tests, shared-schema tests, dashboard
  typecheck/lint, language guards, live blocked-apply API proof and browser
  proof passed.
- GA4 dashboard trace lines no longer use generic `brak` empty states for
  measurement readiness, evidence or sources. Focused GA4 route tests,
  dashboard typecheck/lint, language guards and browser proof passed.
- Merchant dashboard trace lines no longer use generic `brak` empty states for
  decision sources, evidence, actions, source connectors or missing metrics.
  Focused Merchant route tests, dashboard typecheck/lint, language guards and
  browser proof passed.
- Merchant product-performance rows now use API-owned labels for missing
  Ads/GA4 product metrics. Product cards show concrete states such as
  `kliknięcia Ads do potwierdzenia`, `koszt Ads do potwierdzenia`,
  `zakupy GA4 do potwierdzenia` and `przychód GA4 do potwierdzenia` instead
  of context-free `brak`. Focused Merchant API/dashboard/shared-schema tests,
  dashboard typecheck/lint, marketer/context-pack language guards, live API
  proof and browser proof passed.
- Localo and Ahrefs dashboard evidence traces no longer use generic `brak`
  empty states. Focused route tests, dashboard typecheck/lint, language guards
  and browser proofs passed.
- Content diagnostics no longer expose generic Ahrefs/GSC overlap labels such
  as `GSC: brak` or `Overlap GSC`; API labels now distinguish confirmed GSC or
  WordPress matches from missing overlap. Focused API/dashboard tests,
  typecheck/lint, language guards, context-pack guard and browser proof passed.
- Custom Segments and Tactical Queue dashboard traces no longer use generic
  `brak` empty states for evidence, human review, audience forecasts or action
  availability. Focused dashboard tests, typecheck/lint and language guard
  passed.
- Google Ads dashboard traces no longer use generic `brak` empty states for
  evidence, blocked claims, missing data, actions, review gates or source
  conditions. Shared trace rows also no longer default to context-free `brak`.
  Focused Ads route tests, dashboard typecheck/lint, language guard and browser
  proof passed.
- Google Ads target-guardrail action previews no longer show context-free
  `Docelowy zwrot z reklam: brak` or `Docelowy koszt pozyskania celu: brak`.
  The API preview now says that the Ads target is not set and which business
  conclusion WILQ therefore will not make. Focused target-guardrail API tests,
  action-detail route tests, dashboard typecheck/lint, marketer/context-pack
  language guards, live API proof and browser proof passed.
- Google Ads budget preview cards no longer show context-free
  `Propozycja: brak` or `Propozycja do sprawdzenia: brak danych`. The API
  preview now explains that Google Ads did not provide a proposed amount and
  WILQ therefore shows the current budget while blocking budget writes. Focused
  Ads budget API tests, action-detail route test, dashboard typecheck/lint,
  marketer/context-pack language guards, live Ads diagnostics proof and browser
  proof passed.
- Localo marketer-facing summaries now use correct Polish aggregate-count
  wording and all shared metric tiles render decimal values with Polish number
  formatting. Focused API/dashboard tests, language guards and browser proof
  for `/localo` passed.
- Ahrefs gap summaries now use correct Polish count wording and condense
  repeated record-level facts into readable signal counts instead of repeating
  the same gap phrase. Focused Ahrefs/content API tests, dashboard route tests,
  language guards and browser proof for `/ahrefs` passed.
- Ahrefs authority summaries now format large ranking values with Polish
  grouping and keep the competitor-read sentence separated, so the summary is
  readable without dashboard-side cleanup.
- Ahrefs and Localo decision cards now label supporting proof as `Na czym można
  się oprzeć` instead of the contract-like `Dozwolone dowody`; focused
  dashboard tests, typecheck/lint, language guards and browser proof for both
  routes passed.
- Empty missing-data states now say `dane kompletne` instead of awkward
  negative phrasing such as `brak brakujących danych` or `Brakujące dane:
  brak`; focused API/dashboard tests, language guards and Ahrefs browser/API
  proof passed.
- GA4 conversion-readiness now carries an API-owned missing-data summary label,
  so `/ga4` shows `Brakujące dane: dane kompletne` when conversion/key-event
  data is present instead of relying on a route fallback. Focused GA4 API,
  dashboard, shared-schema, language-guard and browser proof passed.
- GA4 action preview blocked-claim labels now use concrete claim names instead
  of repeated fallback text like `wniosek GA4 do sprawdzenia`; focused GA4 API
  tests, language guards and browser proof for
  `/actions/act_review_ga4_tracking_quality` passed.
- `AGENTS.md` now codifies the marketer-content rule: first-screen summaries,
  decision cards and empty states must be understandable without developer
  translation and must state the decision, reason, proof, blocker or next safe
  step directly.
- Action detail now hides legacy English apply/audit summaries from the
  marketer-facing history. The GA4 action detail shows "Zapis zmian
  zablokowany" and a Polish safety summary instead of raw apply-contract text;
  focused API, dashboard, language-guard and browser checks passed.
- Main dashboard status chips no longer expose hidden semicolon separators or
  markdown backticks in marketer-facing text. Content and Merchant browser proof
  passed after the shared chip cleanup.
- Marketing brief, Merchant, GA4 and Ahrefs blocked-read summaries use Polish
  operator status labels instead of raw refresh status enum values.
- Command Center decision freshness notes use Polish source and freshness
  labels instead of raw `connector_id=state` pairs.
- Tactical queue Ahrefs diagnoses use Polish gap/context labels instead of raw
  `gap_type` values, backticks or `key=value` URL context.
- Codex context-pack refresh-run summaries use Polish evidence/access count
  labels instead of numeric fragments like `dowody 2` or `braki dostępu 0`.
- Skill context packs scope active actions per workflow, so the content
  strategist no longer receives unrelated GA4 action payloads.
- Skill context-pack actions expose compacted execution context as
  `action_plan`; the technical `payload` key remains on action detail endpoints
  and is guarded out of `active_action_objects`.
- Skill context-pack `action_plan` no longer exposes technical preview/safety
  field names such as `payload_preview`, `preview_contract`,
  `required_validation`, `apply_allowed`, `api_mutation_ready` or
  `destructive`, and no longer repeats raw action type/connector/mode fields.
  Compact action plans now use preview lists and Polish status labels for
  operator-facing skill context. Raw `source_metric_names` are also removed
  from compact action plans; metric meaning must come through labels/summaries.
  Search-term theme previews use marketer-readable compact keys instead of
  `ngram_preview`, and validation counters use required-check naming. Raw
  blocked-claim and missing-contract lists are removed from compact action
  plans when marketer-readable labels are present.
- Skill context-pack `action_plan` metric snapshots are condensed into
  `metric_tiles` keyed by marketer-readable labels; raw metric field names stay
  out of compact skill action context.
- Google Ads monetary values in raw `*_micros` units are stripped from compact
  skill action plans; full action endpoints keep the technical payload when
  needed for validation/review.
- Skill context-pack `action_plan` now keeps labeled contract/review-gate lists
  only. Raw `allowed_contracts`, `available_read_contracts` and
  `operator_review_gates` are removed from compact skill context when their
  marketer-readable label fields exist.
- Content skill plan items now keep labeled source, publication-readiness,
  blocker and risky-claim fields only. Raw `source_type`,
  `publication_readiness_status`, `publication_blockers` and `forbidden_claims`
  stay out of compact skill context when label fields exist.
- Ads skill campaign plans now use campaign/channel/review-gate labels in
  compact context. Raw `campaign_status`, `advertising_channel_type`,
  `human_review_gates`, `target_status` and safety `missing_requirements` stay
  out of compact skill context when label fields exist, while the budget preview
  keeps its reason and marketer-readable safety checks.
- Compact Ads and custom-segment skill plans no longer expose technical preview
  identifiers or internal safety contract names such as campaign IDs, budget
  IDs, custom-segment preview IDs, `safety_contract`, `target_scope`,
  `member_type` or `audit_required`; full action endpoints retain technical
  payload details for validation/review.
- Content skill plan items now use labeled inventory, canonical, duplicate and
  WordPress inventory gate fields. Raw gate status keys stay out of compact
  skill context, while full action endpoints retain technical payload details
  for validation/review.
- GA4 skill action plans now use labeled required-dimension fields. Raw
  `required_breakdowns` stay out of compact skill context, while full action
  endpoints retain the technical GA4 breakdown contract for validation/review.
- Skill context-pack expert capabilities use `required_inputs` instead of the
  technical `required_mapping` field name.
- Marketer language guard now blocks bare Ads missing status/channel
  placeholders, so future cleanup cannot reintroduce unexplained first-screen
  missing-state copy.
- Workflow cards now explain when a process has no dedicated route instead of
  rendering bare missing-view fallback text.
- Workflow API model now explains complete missing-data state for processes
  instead of returning a bare missing-state fallback in process detail labels.
- Localo and Command Center now explain missing Localo read contracts as
  unconfirmed/unconnected data scopes from API/domain copy instead of bare
  missing-data placeholders.
- Knowledge operating map now explains complete missing-data detail labels as
  a full operator sentence instead of a bare missing-state fallback.
- Ads business-context metric tiles now explain missing margin, business goal,
  budget goal and strategy review states as concrete operator states instead of
  bare missing placeholders.
- Daily, Ads, Ahrefs and Merchant missing-status labels now describe
  unconfirmed data scopes instead of returning bare missing-data copy in active
  briefing contracts.
- Content action labels now describe missing content contracts and unavailable
  GSC metrics as unconfirmed source data instead of bare missing placeholders.
- `docs/goals/001-goal.md` has been condensed back into an active goal
  contract: current state, active findings, execution policy, verification and
  completion definition. Detailed slice history remains in git/proof artifacts,
  not in the active goal.

## Current Blockers And Deferred Work

- Real marketer UAT with Wilku/Ekologus is still not complete. This is the main
  non-technical blocker before claiming the current cockpit is done for humans.
- Major JS dependency migrations are separate product-safe slices, not cleanup
  drive-by changes. JS workspace dependencies are currently up to date; future
  vendor API updates such as Google Ads release changes should land as explicit
  contract slices with focused proof.
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

- `rtk uv run pytest tests/content/test_content_work_item_queue_api.py -q`
- `rtk uv run pytest tests/content/test_content_work_item_state_api.py tests/content/test_content_work_item_queue_api.py -q`
- `rtk uv run pytest tests/content/test_content_quality_review_api.py -q`
- `rtk uv run pytest tests/content/test_content_quality_review_api.py tests/content/test_content_work_item_state_api.py tests/content/test_content_work_item_queue_api.py -q`
- `rtk uv run pytest tests/content/test_structured_generation_api.py -q`
- `rtk uv run pytest tests/content/test_content_workflow_adversarial_gates.py -q`
- `rtk uv run pytest tests/content/test_structured_generation_api.py tests/content/test_content_quality_review_api.py tests/content/test_content_work_item_state_api.py tests/content/test_content_work_item_queue_api.py -q`
- `rtk uv run pytest tests/content/test_content_work_item_state_api.py tests/content/test_workflow_store.py -q`
- `rtk uv run ruff check wilq/content/workflow/store.py apps/api/wilq_api/routers/content_workflow.py tests/content/test_content_work_item_state_api.py`
- `rtk uv run mypy wilq/content/workflow/store.py apps/api/wilq_api/routers/content_workflow.py`
- `rtk uv run pytest tests/test_audit_complexity.py -q`
- `rtk uv run ruff check scripts/audit_complexity.py tests/test_audit_complexity.py`
- `rtk uv run mypy scripts/audit_complexity.py`
- `rtk uv run python scripts/audit_complexity.py --changed`
- `rtk uv run ruff check wilq/content/drafts/structured_generation.py tests/content/test_content_workflow_adversarial_gates.py`
- `rtk uv run mypy wilq/content/drafts/structured_generation.py`
- `rtk uv run python scripts/audit_complexity.py --changed --allow-frozen`
- `rtk uv run pytest tests/content/test_content_workflow_end_to_end.py tests/content/test_work_item_preflight_api.py::test_content_work_item_snapshot_is_derived_from_content_diagnostics -q`
- `rtk uv run ruff check wilq/content/workflow/decision_mapping.py wilq/content/workflow/queue.py wilq/content/workflow/api.py apps/api/wilq_api/routers/content_workflow.py tests/content/test_content_work_item_queue_api.py`
- `rtk uv run mypy wilq/content/workflow/decision_mapping.py wilq/content/workflow/queue.py tests/content/test_content_work_item_queue_api.py`
- `rtk uv run python scripts/audit_complexity.py --changed --allow-frozen`
- `rtk git diff --check`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk pnpm --filter @wilq/dashboard test -- App.test.tsx --runInBand`
- `rtk pnpm --dir apps/dashboard lint`
- `rtk pnpm --dir apps/dashboard build`
- `rtk pnpm fallow:audit --format compact --no-cache`
- `rtk pnpm fallow health --hotspots --targets --format compact --no-cache`
- `rtk uv run pytest tests/test_operator_endpoint_language_guard.py -q`
- `rtk uv run pytest tests/test_api_contracts.py::test_marketing_tactical_queue_uses_dimensioned_metric_facts -q`
- `rtk uv run pytest tests/test_api_contracts.py::test_command_center_exposes_polish_operator_brief -q`
- `rtk uv run pytest tests/test_api_contracts.py -q -k 'blocked_refresh_summaries or operator_label_fallbacks'`
- `rtk uv run pytest tests/test_api_contracts.py -q -k 'operator_label_fallbacks'`
- `rtk uv run pytest tests/test_api_contracts.py -q -k 'operator_label_fallbacks or refresh_run'`
- `rtk uv run pytest tests/test_api_contracts.py -q -k 'content_strategist_payload or ga4'`
- `rtk uv run pytest tests/test_api_contracts.py -q -k 'context_pack_scopes_content_strategist_payload or ga4 or localo or ads_doctor_payload or custom_segments_payload or demand_gen_payload'`
- `rtk uv run pytest tests/test_api_contracts.py -q -k 'expert_capabilities or expert_rule_summaries'`
- `rtk uv run pytest tests/test_context_pack_language_guard.py -q`
- `rtk uv run pytest tests/test_api_contracts.py -q -k 'context_pack_scopes_content_strategist_payload or content'`
- `rtk uv run pytest tests/test_api_contracts.py -q -k 'ga4 and context_pack'`
- `rtk uv run ruff check wilq/actions/ga4/tracking_quality.py wilq/actions/service.py apps/api/wilq_api/main.py scripts/context_pack_language_guard.py tests/test_context_pack_language_guard.py`
- `rtk uv run pytest tests/test_api_contracts.py -q -k 'merchant and (price_impact or groups_reporting_contexts or context_pack)'`
- `rtk uv run pytest tests/test_api_contracts.py -q -k 'merchant_product_performance_readiness or merchant_diagnostics_promotes_ads_product_state_review_decision'`
- `rtk uv run pytest tests/test_api_contracts.py -q -k 'target_guardrail'`
- `rtk uv run pytest tests/test_api_contracts.py -q -k 'action_apply_requires_validation or apply_ready_action_blocks_without_mutation_adapter'`
- `rtk uv run pytest tests/test_api_contracts.py -q -k 'context_pack_scopes_content_strategist_payload or ga4 or localo or ads_doctor_payload or custom_segments_payload or demand_gen_payload'`
- `rtk pnpm --filter @wilq/shared-schemas test -- index.test.ts --runInBand`
- `rtk pnpm --filter @wilq/dashboard test -- src/routes/ContentWorkflowSurface.test.tsx`
- `rtk pnpm -C apps/dashboard typecheck`
- `rtk pnpm -C apps/dashboard lint`
- `rtk pnpm fallow:audit`
- `rtk uv run python scripts/marketer_language_guard.py`
- `rtk uv run pytest tests/test_marketer_language_guard.py -q`
- `rtk uv run pytest tests/content/test_preflight_verdicts.py tests/content/test_canonical_urls.py tests/test_api_contracts.py::test_content_diagnostics_exposes_query_page_inventory_queue tests/test_api_contracts.py::test_content_diagnostics_ignores_dev_site_alternatives_when_public_url_exists -q`
- `rtk uv run ruff check wilq/content/preflight/verdicts.py wilq/briefing/content_diagnostics.py tests/content/test_preflight_verdicts.py`
- `rtk uv run mypy wilq/content/preflight/verdicts.py`
- `rtk uv run python scripts/audit_complexity.py --changed --allow-frozen --limit 5`
- `rtk uv run pytest tests/content/test_inventory_gates.py tests/content/test_preflight_verdicts.py tests/content/test_canonical_urls.py tests/test_api_contracts.py::test_content_diagnostics_exposes_query_page_inventory_queue tests/test_api_contracts.py::test_content_diagnostics_ignores_dev_site_alternatives_when_public_url_exists -q`
- `rtk uv run ruff check wilq/content/inventory/gates.py wilq/briefing/content_diagnostics.py tests/content/test_inventory_gates.py`
- `rtk uv run mypy wilq/content/inventory/gates.py`
- `rtk uv run pytest tests/content/test_planning_decisions.py tests/content/test_inventory_gates.py tests/content/test_preflight_verdicts.py tests/content/test_canonical_urls.py tests/test_api_contracts.py::test_content_diagnostics_exposes_query_page_inventory_queue tests/test_api_contracts.py::test_content_diagnostics_ignores_dev_site_alternatives_when_public_url_exists -q`
- `rtk uv run ruff check wilq/content/planning/decisions.py wilq/briefing/content_diagnostics.py tests/content/test_planning_decisions.py`
- `rtk uv run mypy wilq/content/planning/decisions.py`
- `rtk uv run pytest tests/test_content_diagnostics.py tests/test_api_contracts.py::test_content_diagnostics_exposes_query_page_inventory_queue tests/test_api_contracts.py::test_content_diagnostics_preserves_gsc_query_page_after_newer_aggregate_runs -q`
- `rtk uv run ruff check wilq/briefing/content_diagnostics.py tests/test_content_diagnostics.py`
- `rtk uv run mypy wilq/briefing/content_diagnostics.py`
- `rtk uv run python .agents/skills/wilq-gsc-content-doctor/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000`
- `rtk uv run pytest tests/content/test_structured_generation_api.py tests/content/test_structured_draft_generation.py tests/content/test_structured_draft_preview.py -q`
- `rtk uv run ruff check wilq/content/drafts/structured_generation.py tests/content/test_structured_generation_api.py tests/content/test_structured_draft_generation.py`
- `rtk uv run mypy wilq/content/drafts/structured_generation.py`
- `rtk uv run pytest tests/content/test_structured_draft_preview.py tests/content/test_structured_generation_api.py -q`
- `rtk uv run ruff check wilq/content/drafts/preview.py tests/content/test_structured_draft_preview.py`
- `rtk uv run mypy wilq/content/drafts/preview.py`
- `rtk uv run pytest tests/content/test_content_quality_review_api.py -q`
- `rtk uv run pytest tests/content/test_content_work_item_brief_draft_api.py tests/content/test_structured_generation_api.py -q`
- `rtk uv run ruff check tests/content/test_content_quality_review_api.py wilq/content/workflow/api.py`
- `rtk uv run mypy wilq/content/workflow/api.py`
- `rtk uv run pytest tests/content/test_work_item_preflight_api.py -q`
- `rtk uv run pytest tests/content/test_work_item_preflight_api.py tests/content/test_content_quality_review_api.py tests/content/test_structured_draft_preview.py tests/content/test_structured_generation_api.py -q`
- `rtk uv run ruff check tests/content/test_work_item_preflight_api.py tests/content/test_content_quality_review_api.py wilq/content/workflow/api.py`
- `rtk pnpm --filter @wilq/shared-schemas test -- index.test.ts --runInBand`
- `rtk pnpm --dir packages/shared-schemas typecheck`
- `rtk pnpm --dir apps/dashboard test -- WorkflowPanels.test.tsx --runInBand`
- `rtk uv run pytest tests/test_api_contracts.py -q -k 'workflow_label_fallbacks_do_not_expose_raw_values or workflow_missing_contract_detail_fallback_explains_complete_process or workflows_are_decision_backed_operator_contracts'`
- `rtk uv run python scripts/context_pack_language_guard.py --api-base http://127.0.0.1:8000`
- `rtk pnpm outdated -r`
- browser proof with `agent-browser` for touched routes
- `rtk git diff --check`

## Recovery Rule

Older proof history is intentionally omitted from this recovery ledger. Use git
history and `.local-lab/proof/` when older evidence is needed. When adding new
status, remove or replace outdated lines instead of appending a new history
block.
