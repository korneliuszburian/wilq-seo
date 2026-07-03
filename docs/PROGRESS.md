# WILQ Progress Ledger

This file is the short recovery ledger. It is not a changelog and must not
become an append-only transcript.

Current cleanup plan: `PLAN.md`
Active product execution plan: `PLANS.md`
Goal 001 contract: `docs/goals/001-goal.md`

## Current Readout

Date: 2026-07-03

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
- 2026-07-03 local Wilku handoff usefulness review is stored in
  `docs/evals/2026-07-03-wilku-handoff-usefulness-review.md`. It scores the
  review packet at 7.5/10, keeps Goal 005 blocked on real Wilku UAT or owner
  defer, and moved technical IDs/language lower in
  `docs/handoffs/2026-07-02-co-pokazac-wilkowi.md`.
- 2026-07-03 skill ceremony reduction completed for the current slice: WILQ
  skills now start from narrow API-owned view models and answer the marketer
  decision directly. Output references, smoke scripts and context-pack
  comparison are development and eval tools, not mandatory steps in normal
  skill use. Daily Command non-interactive eval passed at
  `.local-lab/evals/codex-skill/20260703T053628Z`.
- 2026-07-03 eval-driven tuning after ceremony reduction produced two useful
  fixes: Content Operator now has to show human-readable źródła and Polish
  workflow step names, while Merchant visible copy must translate raw readiness
  fields into normal blocker language. Passing artifacts:
  `.local-lab/evals/codex-skill/20260703T054706Z` and
  `.local-lab/evals/codex-skill/20260703T055715Z`.
- 2026-07-03 follow-up skill usefulness checks passed for
  `wilq-gsc-content-doctor`, `wilq-content-strategist` and
  `wilq-social-publisher` after the skill ceremony reduction. Artifacts:
  `.local-lab/evals/codex-skill/20260703T061109Z`,
  `.local-lab/evals/codex-skill/20260703T061228Z` and
  `.local-lab/evals/codex-skill/20260703T061357Z`. All three score the current
  minimum `operator_usefulness_score=5`; treat this as "works out-of-the-box
  with evidence and blockers", not as final BDOS-class sharpness.
- 2026-07-03 reviewer-driven first-screen tuning landed for the same three
  content/social skills. GSC now translates partial GSC data into normal
  operator language and adds a manual review checklist; Content Strategist
  separates "can prepare refresh queue now" from blocked draft/publish claims;
  Social Publisher adds a three-line review draft and plain social-history
  blocker. Passing artifacts:
  `.local-lab/evals/codex-skill/20260703T065259Z`,
  `.local-lab/evals/codex-skill/20260703T065420Z` and
  `.local-lab/evals/codex-skill/20260703T065602Z`.
- 2026-07-03 Ads Doctor visible blocker tuning fixed a non-interactive eval
  failure where raw API/schema markers leaked into operator-facing fields. The
  passing artifact is `.local-lab/evals/codex-skill/20260703T070219Z`; raw Ads
  contract fields now stay in technical `notes`, while visible copy says which
  review queue to open and which claims/writes remain blocked.
- 2026-07-03 GA4 `(not set)` wording was tuned after the operator confusion
  around "blocked" rows. The skill now separates `Pomiar do naprawy` from
  `Ruch do oceny`: `(not set)` rows are measurement rows to fix, while readable
  landing/source rows can be reviewed for traffic quality. Passing artifact:
  `.local-lab/evals/codex-skill/20260703T070939Z`.
- 2026-07-03 Custom Segments visible blocker tuning fixed the same raw-marker
  problem for audience review. The passing artifact is
  `.local-lab/evals/codex-skill/20260703T071835Z`; visible copy now says that
  segment review can start from real source terms, while audience size, ROAS,
  write and campaign-effect claims stay blocked because Keyword Planner
  enrichment and audience-size forecast are missing.
- 2026-07-03 skill eval scoring was upgraded from a capped 1-5 pass scale to a
  1-10 marketer-usefulness scale. `5` is still the minimum pass, `7+` means a
  strong operator workflow and `10` means Wilku-ready / BDOS-class output. The
  focused proof eval for `wilq-daily-command` passed at
  `.local-lab/evals/codex-skill/20260703T121004Z` with
  `operator_usefulness_score=9`, `blocked=false`, 22 evidence IDs, 4
  recommendations, 4 actions and all hard gates true. Treat this as proof that
  the harness can now measure beyond baseline, not as proof that every skill is
  already 9-10/10.
- 2026-07-03 `wilq-content-operator` reached the strong workflow threshold on
  the 1-10 scale. Artifact:
  `.local-lab/evals/codex-skill/20260703T113839Z`; result:
  `operator_usefulness_score=7`, `blocked=true`, 6 evidence IDs, 2
  recommendations, 2 actions and all hard gates true. The latest skill
  coverage map now reports `strong_skill_count=2` and `wilku_ready_skill_count=0`.
- 2026-07-03 `wilq-content-strategist` also reached the strong workflow
  threshold. Artifact:
  `.local-lab/evals/codex-skill/20260703T114415Z`; result:
  `operator_usefulness_score=7`, `blocked=true`, 6 evidence IDs, 4
  recommendations, 2 actions and all hard gates true. Skill coverage now
  reports `strong_skill_count=3`.
- 2026-07-03 `wilq-gsc-content-doctor` reached 9/10 SEO/content diagnostic
  level after requiring a visible decision map, page-check instructions and a
  short brief packet for Wilku. Artifact:
  `.local-lab/evals/codex-skill/20260703T123952Z`; result:
  `operator_usefulness_score=9`, `blocked=false`, 5 evidence IDs, 4
  recommendations, 1 action and all hard gates true.
- 2026-07-03 `wilq-ads-doctor` re-evaluated at 9/10 core workflow level
  after tightening the visible operator contract around `Jak sprawdzić` and
  `Decyzja po review`. Artifact:
  `.local-lab/evals/codex-skill/20260703T120521Z`; result:
  `operator_usefulness_score=9`, `blocked=false`, 12 evidence IDs, 5
  recommendations, 5 actions and all hard gates true. Skill coverage now
  reports `strong_skill_count=5` and maximum score `9`.
- 2026-07-03 `wilq-content-operator` reached 9/10 core content workflow level
  after switching the visible contract from a gate report to one session:
  `Co wybieramy`, `Plan sesji`, `Kiedy stop` and `Co pokazać Wilkowi`.
  Artifact: `.local-lab/evals/codex-skill/20260703T121912Z`; result:
  `operator_usefulness_score=9`, `blocked=true`, 6 evidence IDs, 4
  recommendations, 2 actions and all hard gates true.
- 2026-07-03 `wilq-content-strategist` reached 9/10 content strategy level
  after requiring a decision map and review brief packet instead of only
  blocker-led planning. Artifact:
  `.local-lab/evals/codex-skill/20260703T122515Z`; result:
  `operator_usefulness_score=9`, `blocked=true`, 11 evidence IDs, 4
  recommendations, 2 actions and all hard gates true.
- 2026-07-03 `wilq-ga4-analyst` reached 9/10 analytics workflow level after
  requiring visible `Kolejność triage`, `Decyzja po review` and
  `Brief dla marketera`. Artifact:
  `.local-lab/evals/codex-skill/20260703T124506Z`; result:
  `operator_usefulness_score=9`, `blocked=false`, 19 evidence IDs, 4
  recommendations, 1 action and all hard gates true. It separates `(not set)`
  measurement repair from readable landing/source/campaign traffic review and
  blocks ROI/revenue/conversion/write claims.
- 2026-07-03 `wilq-merchant-feed-operator` reached 9/10 feed review level
  after requiring visible `Kolejność review`, `Liczby bez pułapki`,
  `Decyzja po review` and `Brief dla marketera`. Artifact:
  `.local-lab/evals/codex-skill/20260703T125343Z`; result:
  `operator_usefulness_score=9`, `blocked=false`, 4 evidence IDs, 5
  recommendations, 6 action candidates and all hard gates true. It separates
  issue occurrences from unique SKU, keeps product ROAS/revenue/reapproval/
  write claims blocked and gives a first review queue.
- 2026-07-03 source fact coverage audit now reports the operator value of
  private `ekologus-ai` proposals, not only the backlog. Live audit: 5 private
  proposals, 5 with blocked claims, 5 with CTA patterns, 5 with buyer/problem
  triggers, `promotion_allowed_count=0`, `operator_value_score=9`; production
  depth and daily-content readiness remain blocked until review.
- 2026-07-03 fresh full WILQ skill eval baseline is now 13/13 passing for all
  repo WILQ skills on production-like Polish prompts. The baseline originally
  proved "works out-of-the-box with evidence and blockers"; follow-up slices
  are now pushing core skills from that baseline toward 9/10.
- 2026-07-03 Goal 006 candidate `wilq-seo-1xv` was closed as already
  implementation-complete: `scripts/claim_ledger_gate_audit.py --format json`
  passed 13/13 and focused Claim Ledger/generation gate tests passed 65/65.
  Remaining production-depth proof still belongs to Goal 005: Wilku/owner
  review, approved-current knowledge and measurement windows.
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

Live API check on 2026-07-02:

- WILQ API health: `ok`.
- Connector summary: 12 total, 9 configured, 2 missing credentials and Google
  Sheets intentionally disabled for the current operator scope.
- Configured connectors: Google Ads, Google Search Console, Google Analytics 4,
  Google Merchant Center, Ahrefs, Localo, WordPress ekologus.pl, WordPress
  sklep and OpenAI Codex runtime.
- Missing credentials: LinkedIn (`LINKEDIN_ORGANIZATION_ID`,
  `LINKEDIN_ACCESS_TOKEN`) and Facebook (`FACEBOOK_PAGE_ID`,
  `FACEBOOK_PAGE_ACCESS_TOKEN`). Social publishing/history remains review-only
  and cannot support duplicate-free claims until metadata/evidence exists.
- Metric store: DuckDB enabled, 79,799 metric facts, 8 connector families with
  metric facts and 4,170 refresh runs.
- Recent refresh proof includes GSC `refresh_google_search_console_9b25d4143bea`
  completed `2026-07-02T03:13:21Z`, WordPress sklep
  `refresh_wordpress_sklep_c1db9b8fa677` completed
  `2026-07-01T22:38:18Z`, Ahrefs `refresh_ahrefs_5eee21244cff` completed
  `2026-07-01T22:37:01Z`, Merchant
  `refresh_google_merchant_center_a04a45a6e6fd` completed
  `2026-07-01T22:36:56Z` and Google Ads
  `refresh_google_ads_be7011a4a261` completed `2026-07-01T19:15:42Z`; all have
  `metrics_persisted=true`.
- Treat future Ads/Keyword Planner failures as Ads API/customer/readiness state
  unless status reports missing credential names. Current Keyword Planner can
  still be blocked by developer-token approval, not by missing OAuth
  credentials.

Do not reopen old WSL credential recovery for GSC, GA4, Merchant or Ads unless
live API status later contradicts this state.

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
- Goal 005 UAT capture helper: `scripts/record_goal_005_content_uat_result.py`
  can now print a fillable JSON example with `--print-input-example`, using the
  live API candidate ID when `--api-base` is provided. The example intentionally
  contains placeholders and is rejected by the normal validator until Wilku's
  real answers are filled in.
- Goal 005 UAT input example now ranks live content candidates for practical
  review value instead of picking the first ID alphabetically. With the current
  API queue it selects
  `content_work_item_content_decision_https___www_ekologus_pl`, the actionable
  homepage refresh candidate, instead of blocked GA4/Ahrefs review-only items.
- Goal 005 completion guard now surfaces the next UAT input directly in the
  blocked report. `scripts/goal_005_completion_check.py --api-base
  http://127.0.0.1:8000 --format json` still blocks completion without real
  UAT/defer, but returns `next_uat_input.selected_work_item` plus the fillable
  JSON command for the homepage candidate, so the next Wilku session does not
  require hunting through helper scripts.
- Goal 005 completion guard also renders the next Service Profile review
  actions as readable bullets with ActionObject ID, review scope, target
  service/policy and allowed decision options. The report still blocks
  completion without real UAT/defer, but now says exactly what Wilku should
  review next.
- Service Profile review recorder can now generate a live JSON input example
  from API-owned `review_actions` and `review_requirements`:
  `scripts/record_service_profile_review_result.py --print-input-example
  --review-type private_source_proposals --api-base http://127.0.0.1:8000`.
  Live proof on 2026-07-02 returned five private `ekologus-ai` proposal
  decisions and six public service-card decisions. This makes review practical
  without hand-copying action IDs, but still does not promote facts, cards or
  production-depth readiness.
- Service Profile review recorder also has a prepare-only promotion-readiness
  guard: `--promotion-readiness`. It validates the review result, builds an
  auditable promotion request preview, and still keeps `promotion_allowed=false`,
  `mutation_allowed=false` and `production_depth_unlocked=false`. Live proof on
  2026-07-02 with a clean private approval stayed blocked by
  `missing_evidence_ids` and `private_retention_not_usable`, which is correct
  because current redacted `ekologus-ai` proposals have no evidence IDs and
  retention remains `pending_owner_decision`.
- Goal 005 UAT input now recommends the full review set before any completion
  claim: WILQ model, plain "co pokazać Wilkowi" guide, BDO review artifact and
  `ekologus-ai` policy review artifact. It now also includes the social history
  blocker, so Wilku reviews the LinkedIn/Facebook metadata-only dedupe contract
  before WILQ can claim safe repurpose. The fillable scorecard is generated for
  all materials, so a shallow UAT cannot accidentally pass as complete.
- Social history dedupe is now a practical metadata-only input path, not only a
  blocker. `scripts/social_history_inventory_audit.py --print-input-example`
  prints the `social_history_inventory_v1` JSON shape; the audit rejects raw
  post bodies, comments, user fields and tokens, requires both LinkedIn and
  Facebook metadata, and returns `review_ready` only for dedupe review. Even a
  clean audit keeps `duplicate_free_claim_allowed=false` and
  `publish_allowed=false` until separate historical review evidence exists.
- Social history readiness is now exposed as a direct read-only API contract at
  `/api/social/history-inventory` and in the `wilq-social-publisher`
  context-pack. It records the public Ekologus LinkedIn posts URL as a
  `metadata_only` discovery seed, keeps LinkedIn/Facebook credentials as
  explicit blockers, and still blocks "new topic", "no duplicates" and
  publishing claims until reviewed metadata exists. Live proof on 2026-07-02:
  endpoint returned `social_history_inventory_v1` with one LinkedIn
  `discovery_seed`, and `wilq-social-publisher` smoke passed with
  `direct_inventory_seed_count=1`; non-interactive eval passed at
  `.local-lab/evals/codex-skill/20260702T205202Z`.
- Pre-demo gate proof after the latest Goal 005 slices:
  `rtk scripts/pre_demo_gate.sh` passed on 2026-07-02. It verified the managed
  local stack, API health, live contracts, dashboard usefulness, source fact
  coverage, Claim Ledger gate, skill eval coverage, language guard, shared
  schemas, 13 dashboard route smokes and WILQ skill smoke contracts. It was
  rerun after adding `draft_package_claim_outside_ledger`, and the Claim Ledger
  gate now passes 13/13 checks including `missing_evidence` for unsourced
  service claims and `missing_product_evidence` for product claims without
  Merchant/shop evidence. This is review/demo readiness proof, not Goal 005
  completion or real Wilku UAT proof.
- Daily Command usefulness proof: non-interactive eval for
  `wilq-daily-command` passed with `operator_usefulness_score=5`, 20 evidence
  IDs, eight source connectors and four validated daily actions. The first safe
  step is Merchant review from `primary_next_step`; GA4 and Ads claims stay
  blocked where proof/contracts are missing.
- Merchant Operator usefulness proof: non-interactive eval for
  `wilq-merchant-feed-operator` passed at
  `.local-lab/evals/codex-skill/20260702T171333Z` with
  `operator_usefulness_score=5`. It validates
  `act_review_merchant_feed_issues`, treats Merchant counts as reported issue
  occurrences rather than unique SKUs, separates `required_read_contracts` from
  `missing_read_contracts`, and now lists literal missing contracts for product
  performance and price-impact readiness instead of broadening all requirements
  into "missing" blockers. It blocks product ROAS, recovered revenue,
  price-impact, reapproval and feed-write claims.
- GA4 Analyst usefulness proof: non-interactive eval for `wilq-ga4-analyst`
  passed with `operator_usefulness_score=5`. It treats `(not set)` rows as
  `fix_measurement` blockers before traffic-quality review, validates
  `act_review_ga4_tracking_quality`, and blocks revenue, ROAS, conversion-drop,
  conversion-rate, GA4-write and "measurement fixed" claims.
- Ads Doctor usefulness proof: non-interactive eval for `wilq-ads-doctor`
  passed with `operator_usefulness_score=5`. It orders Ads review by campaigns/
  budgets, recommendations, search terms/negative keywords, custom segments and
  change history; validates four review actions; and blocks CPA, ROAS, wasted
  budget, budget writes, recommendation apply and negative keyword writes
  without preview, human confirmation and audit.
- Content Operator usefulness proof: non-interactive eval for
  `wilq-content-operator` passed with `operator_usefulness_score=5` and
  `blocked=true`. It selects the refresh work item
  `content_work_item_content_decision_https___www_ekologus_pl`, keeps the queue
  honest as blocked, and requires enrichment, preflight, Sales Brief, Claim
  Ledger, draft package, quality review, human review, WordPress draft-only and
  measurement window before any final article, publication or success claim.
- Content Operator was re-tested after making the selected content-workflow
  queue step action-backed and after hardening the eval harness against
  marker-dump operator copy. The latest eval artifact is
  `.local-lab/evals/codex-skill/20260702T230541Z`, still
  `operator_usefulness_score=5`, `blocked=true`, six evidence IDs, four source
  connectors and all hard gates true. The selected work item validates
  `act_prepare_content_refresh_queue`; visible next-step copy stays normal
  Polish while technical markers stay in `notes`. The eval now also proves the
  dry-run WordPress ACF/`elementy` authoring preview: `row_candidate_count=8`,
  first row `review_required`, mapped fields `tresc`, `opis`, `podtytul`,
  `tytul`, and `publish_allowed=false`,
  `destructive_update_allowed=false`, `external_write_attempted=false`.
- Content workflow Claim Ledger and homepage Sales Brief now produce a useful
  review-required plan for the selected homepage refresh item. WILQ added
  commit-safe public source facts for homepage service overview and contact CTA,
  matches them only for the exact root URL, and returns public-facing H1/H2/CTA:
  `Ekologus - doradztwo i outsourcing środowiskowy dla firm`, `W czym pomaga
  Ekologus`, `Kiedy warto skonsultować obowiązki środowiskowe`, `Jak
  przygotować się do rozmowy`, plus contact CTA without outcome promises. Live
  API proof: brief exists, `signal_quality.status=review_required`,
  `draft_allowed=false`, no `missing_required_knowledge_card` blockers,
  structured generation remains `publish_ready=false`, WordPress handoff is
  blocked by `missing_human_review` and `missing_audit`, and measurement success
  remains blocked by `measurement_window_not_ready`.
- WordPress authoring discovery slice is implemented as read-only API
  contract. `/api/content/wordpress/authoring-profile` exposes REST readiness,
  ACF/Flexible Content layout readiness, WP-CLI/helper fallback readiness and a
  draft-only write boundary. `/api/content/work-items/wordpress-authoring-
  payload-preview` maps an approved handoff plus draft package to an ACF
  Flexible Content payload preview when a field-group export/layout contract is
  available; it never publishes, never performs a vendor write and keeps
  ActionObject review/audit as the required write contract. Live SSH proof on
  2026-07-02: SSH login works and main docroot is
  `/var/www/vhosts/ekologus.pl/httpdocs`. The hosting `/usr/local/bin/wp` was a
  broken placeholder, so WILQ installed user-scoped WP-CLI under the SSH user
  and created `~/.local/bin/wilq-wp-readonly`, a read-only wrapper outside the
  WordPress docroot. The wrapper uses Plesk PHP 8.3 with `mysqli`, blocks
  write-capable commands such as `post create`, and allows only selected
  discovery commands for the configured docroot. A local ignored ACF export was
  generated from read-only `acf-field-group`/`acf-field` metadata and wired to
  `.env`; live API now reports WP-CLI fallback as `configured`, ACF Pro active,
  `acf.layouts_discovered=true`, 21 layout-like ACF sections and no authoring
  blockers. Live payload preview maps the current homepage draft package to the
  real `podstrona` ACF layout with `external_write_attempted=false`, leaves the
  `elementy` repeater empty instead of pretending a flat text value is safe, and
  still requires the normal WordPress draft-only review/audit path before any
  write.
- `/content-workflow` now renders WordPress authoring readiness directly from
  `/api/content/wordpress/authoring-profile`: REST status, ACF layout discovery,
  read-only WP-CLI fallback and publish/write blockers. Live proof on
  2026-07-02 showed `rest=configured`, `wp_cli=configured`, 21 ACF sections,
  `publish_allowed=false` and `external_write_attempted=false`; the dashboard
  panel says no external write happened and every WordPress write still requires
  review, preview, human decision and audit. The route can now also trigger the
  existing dry-run ACF payload preview after a handoff exists. The UI shows the
  selected layout and mapped fields under "Mapowanie ACF", while keeping
  publication, destructive updates and external writes blocked. Live HTTP proof
  on 2026-07-02: the endpoint correctly blocks preview when the current snapshot
  has no handoff, and with a matching synthetic handoff returns
  `status=ready`, `mode=dry_run`, layout `podstrona`,
  `publish_allowed=false`, `destructive_update_allowed=false` and
  `external_write_attempted=false`. The preview now also exposes nested ACF
  field previews for the real `podstrona` layout: `glowny_opis` is shown as a
  group with `lead`/`opis`, and `elementy` is shown as `flexible_content` with
  a clear note that layout/row choice still needs separate review instead of a
  fake flat value. The `elementy` preview now also returns one dry-run
  `row_candidate` for manual review with mapped text fields
  (`tresc`, `opis`, `podtytul`, `tytul`) and source evidence IDs, while
  `publish_allowed=false`, `destructive_update_allowed=false` and
  `external_write_attempted=false`.
- Content Strategist usefulness proof: replayed non-interactive eval for
  `wilq-content-strategist` passed at
  `.local-lab/evals/codex-skill/20260702T162005Z` with
  `operator_usefulness_score=5` and `blocked=true`. It uses
  `content_diagnostics.decision_queue` as canonical, treats BDO as a
  refresh/merge path for the existing URL, blocks Zielony Ład until WILQ has
  source evidence plus inventory/canonical/duplicate checks, and keeps final
  draft/WordPress/ranking/lead/revenue claims blocked.
- GSC Content Doctor usefulness proof: replayed non-interactive eval for
  `wilq-gsc-content-doctor` passed at
  `.local-lab/evals/codex-skill/20260702T160528Z` with
  `operator_usefulness_score=5`. It gives one safe `refresh_or_merge` content
  decision for `https://www.ekologus.pl/`, validates
  `act_prepare_content_refresh_queue`, and keeps `partial_possible` GSC
  query/page data from becoming ranking, lead, publication or full-traffic
  claims.
- Ahrefs Gap Finder usefulness proof: replayed non-interactive eval for
  `wilq-ahrefs-gap-finder` passed at
  `.local-lab/evals/codex-skill/20260702T161306Z` with
  `operator_usefulness_score=5`. It treats `gap_read_contract.status=ready`
  and `gap_record_count=8` as a review-only Ahrefs gap queue, keeps
  `action_count=0` honest instead of inventing an ActionObject, and blocks
  traffic-growth/authority-growth claims.
- Localo Operator usefulness proof: replayed non-interactive eval for
  `wilq-localo-operator` passed at
  `.local-lab/evals/codex-skill/20260702T161619Z` with
  `operator_usefulness_score=5`. It validates
  `act_review_localo_visibility_facts`, uses two Localo evidence IDs, treats
  aggregate visibility/GBP/review facts as review-only, and keeps local-task,
  profile-write and local-visibility improvement claims blocked.
- Campaign Builder usefulness proof: replayed non-interactive eval for
  `wilq-campaign-builder` passed at
  `.local-lab/evals/codex-skill/20260702T162535Z` with
  `operator_usefulness_score=5`. It validates
  `act_prepare_ads_campaign_review_queue` and
  `act_prepare_google_ads_recommendation_review_queue`, uses the GSC/WordPress
  landing candidate only as review context, and blocks campaign writes, budget
  changes, conversion uplift and ranking guarantees.
- Custom Segments usefulness proof: replayed non-interactive eval for
  `wilq-custom-segments` passed at
  `.local-lab/evals/codex-skill/20260702T162911Z` with
  `operator_usefulness_score=5`. It validates
  `act_prepare_custom_segments_from_search_terms`, keeps one source-backed
  segment candidate with 10 `source_terms`, and blocks audience-size,
  Keyword Planner enrichment, targeting-write and performance claims until the
  missing contracts exist.
- Social Publisher usefulness proof: non-interactive eval replay passed at
  `.local-lab/evals/codex-skill/20260702T160931Z` with
  `operator_usefulness_score=5`. It stays review-only with
  `publish_allowed=false`, missing LinkedIn/Facebook credentials,
  metadata-only `social_history_inventory_v1`, and duplicate-free claims blocked
  until historical social metadata exists. The smoke now also requires the
  social history import contract to include `format` and `source_evidence_id`,
  so WILQ can trace dedupe decisions without storing raw post bodies.
- Latest Goal 005 Service Profile slice: review actions expose API-owned
  `review_requirements` aligned with
  `scripts/record_service_profile_review_result.py`. Dashboard and UAT packets
  now show required review fields plus the `follow_up_beads` rule for blocking
  decisions. Live proof after `scripts/local_stack.sh restart` showed 12 review
  actions with those requirements.
- Second-opinion follow-up after Goal 005 activation: the reported loose
  `unknown` request typing for core content POSTs is stale in the current repo;
  `api.ts` validates preflight, Sales Brief, draft package, human review and
  measurement-window requests through shared Zod schemas. The still-valid risk
  is measurement provenance: `wilq-seo-708` tracks whether measurement outcome
  interpretation is tied to metric_store facts, connector refresh/JobRun
  lineage, evidence IDs and the original content decision before any broader
  usefulness claim.
- Claim gate schema hardening: `ContentClaimReferenceSchema` now reuses the
  typed Claim Ledger claim type/status enums, so Sales Brief forbidden/removed
  claim references cannot carry arbitrary model-owned labels. Focused proof:
  shared-schema tests, dashboard API/content workflow tests, dashboard
  typecheck and `git diff --check`.
- Backend Sales Brief claim gate hardening: `ContentSalesBriefForbiddenClaim`
  now uses the backend Claim Ledger claim type/status literals, with regression
  proof that forged labels such as `marketing_vibe_claim` and
  `approved_by_prompt` are rejected before generation gates consume them.
- Structured draft generation now blocks draft-package claims that are not in
  publish-ready Claim Ledger entries before they can enter `claims_allowed` in
  the model contract. The Claim Ledger gate audit now proves
  `draft_package_claim_outside_ledger`, so preview validation is no longer the
  first line of defense for foreign/unsafe draft claims.
- Claim Ledger now has a typed `product_claim` and blocks product/offering
  claims without Merchant or shop evidence through `missing_product_evidence`.
  Product intent from public content or SEO evidence is not enough to put a
  product CTA into generated draft language.
- Claim Ledger now also blocks `allowed_general` service claims without
  evidence through `missing_evidence`, so the model contract cannot receive
  generic Ekologus service language that has no source trace.
- Service Profile private proposal governance now exposes `freshness_status`
  and `audience` from ekologus-ai/private source proposals through backend API
  models and shared Zod schemas, so owner review can see source currency and
  access scope before any source fact promotion.
- `/service-profile` now renders private proposal freshness and audience chips
  on proposal cards, so those governance fields are visible to Wilku/reviewer,
  not only present in the raw API contract.
- Private proposal review actions now require explicit confirmation of
  `freshness_status` and audience/scope before any source fact promotion path,
  keeping ekologus-ai proposals review-only until source currency and access
  scope are checked.
- Prepare-only private proposal promotion previews now carry the same
  `freshness_status` and `audience` governance context and render it in preview
  cards, so a reviewer sees source currency and access scope inside the
  ActionObject review path, not only on the Service Profile proposal card.
- The `wilq-content-operator` UAT packet private proposal details now preserve
  `freshness_status` and `audience` for Wilku-facing review.
- Dashboard usefulness readiness is now API-audited before demo. New script:
  `scripts/dashboard_usefulness_audit.py`. It scores live surfaces for endpoint
  reachability, decision/proof/action/blocker/next-step coverage and marks
  surfaces as `demo_ready`, `review_ready` or `blocked` without asserting exact
  metric values. Proof on 2026-07-02:
  `rtk uv run python scripts/dashboard_usefulness_audit.py --api-base http://127.0.0.1:8000 --format markdown`
  returned 15 checked surfaces, 13 `demo_ready`, 2 `review_ready` (Demand Gen
  and Social Publisher, experimental), 0 `blocked`, `pass=true`. The audit now
  includes `/content-workflow` and the social context-pack, with social scoped
  to `social_draft_context` so historical-post blockers are measured without
  counting unrelated context-pack actions. `scripts/pre_demo_gate.sh` now runs
  this audit after the live contract smoke. Current per-screen snapshot is
  stored in `docs/evals/dashboard-usefulness-audit.md`; reference surfaces
  such as Actions, Opportunities and Knowledge now show safe operator use
  instead of an empty next-step cell.
- The dashboard usefulness audit now also checks `/content-workflow` against
  the read-only WordPress authoring profile at
  `/api/content/wordpress/authoring-profile`. Live proof on 2026-07-02:
  `REST=configured`, `WP-CLI=configured`, `ACF layouts=21`,
  `writes blocked=True`. If ACF layout discovery or the write boundary regresses,
  `/content-workflow` becomes blocked in the readiness report.
- Source fact / Service Profile coverage is now auditable as a concise Wilku
  readiness report through `scripts/source_fact_coverage_audit.py`. Proof on
  2026-07-02: 14 source facts, 14 review actions, 5 private `ekologus-ai`
  proposals requiring review, 0% production-depth service readiness, 0%
  approved source facts and `ready_for_daily_content=false`. The next review
  order is claim policy first, then evidence policy, then private service
  proposals. `scripts/pre_demo_gate.sh` now runs this audit before demos, so
  WILQ cannot present the current knowledge layer as production-depth by
  accident.
- The same source-fact audit now renders a concrete Service Profile
  `review_action_queue` with ActionObject IDs, review scope, target card and
  decision options. Wilku can see not only that source facts require review, but
  which `service_profile_review_*` action to check next.
- Claim Ledger / structured generation gates are now auditable through
  `scripts/claim_ledger_gate_audit.py`. Current proof on 2026-07-02: 13/13
  checks passed. WILQ blocks guarantees, legal claims without human review,
  business outcome claims without a completed measurement window, evidence
  claims without source connectors, missing Claim Ledger input, ledger blockers,
  full drafts from review-required knowledge, unsourced service claims and
  product claims without Merchant/shop evidence. Valid section generation
  remains review-only: the contract is strict and `publish_ready=false`.
  `scripts/pre_demo_gate.sh` now runs this audit before context-pack language
  checks, so stakeholder-demo proof covers both dashboard usefulness and content
  generation safety.
- Goal 005 completion guard now includes pre-demo gate summaries in every
  completion report: source-fact coverage, Claim Ledger generation gate and
  strict skill eval coverage. It still returns
  `blocked_missing_goal_005_uat_proof` without a real UAT result or explicit
  owner defer, but the blocker now also shows that source facts are
  `source_backed_review_required`, production-depth is 0%, Claim Ledger has
  13/13 checks and skill eval coverage has 13/13 cases with 0 hard gaps.
- `docs/handoffs/2026-07-02-co-pokazac-wilkowi.md` now starts with the current
  pre-demo truth in plain Polish: dashboard readiness, source facts still
  review-required, Claim Ledger 13/13, skill eval coverage 13/13 and Goal 005
  still blocked without UAT/defer. This is the short artifact to show Wilku
  before walking through detailed BDO, Eko-Opieka, policy and gate materials.
- Social Publisher usefulness proof now confirms the historical-post rule from
  the WILQ product contract: WILQ can prepare LinkedIn/Facebook draft directions
  for manual review, but cannot claim a topic is new, non-duplicated or safe to
  repeat until metadata-only LinkedIn/Facebook history exists. Passing proof:
  `.local-lab/evals/codex-skill/20260702T145613Z/wilq-social-publisher/result.json`.
- Daily Command eval now has a stricter first-action clarity gate: the result
  must state what to do first, why now, the proof, the blocker and the next safe
  step. Passing proof:
  `.local-lab/evals/codex-skill/20260702T150140Z/wilq-daily-command/result.json`
  selected `/merchant` first from `daily_decisions`/`primary_next_step`,
  validated four daily actions and kept Localo/social out of the primary day
  queue when they are not in the command-center decisions.
- Eko-Opieka usefulness review now has a short Wilku-facing decision card at
  `docs/handoffs/2026-07-02-wilku-eko-opieka-start-card.md`. Reviewer scores:
  7-8/10 as review material, 6.5/10 as marketer work saved, 3/10 as production
  SEO readiness. The main learning is that `ekologus-ai` private/reviewed
  knowledge improves specificity, but WILQ must still block production content
  until Wilku/owner review, WordPress/GSC duplicate checks and claim ledger are
  complete.
- Ads Doctor usefulness review now has a short Wilku-facing decision card at
  `docs/handoffs/2026-07-02-wilku-ads-doctor-start-card.md`. Reviewers scored
  the surface 7/10 overall, 7.5/10 as marketer review material, 5.5/10 as
  safe-change readiness and 8.5/10 for blocking unsupported Ads claims. The
  dashboard first screen now leads with `Ads Doctor: co dziś zrobić` and
  `Kolejność pracy`; the remaining next gap is clearer per-action preview
  detail.
- Ads Doctor now exposes API-owned top blocked claim labels through
  `operator_summary.top_blocked_claim_labels` and renders them on the first
  screen instead of only showing a count. Live proof after stack restart:
  `/api/ads/diagnostics?view=summary` returned top blocked claims for
  `zmarnowany budżet`, `opłacalność`, `skalowanie budżetu`, `zmiana budżetu`
  and `zapis rekomendacji`.
- Ads Doctor action cards now render a concise `Co obejmuje akcja` summary from
  existing ActionObject payload fields before the technical JSON toggle. Google
  Ads campaign and recommendation review actions can show campaign/recommendation
  scope, API-owned required validation labels and blocked claim labels without
  exposing raw enums as marketer copy.
- `wilq-ads-doctor` passed deterministic smoke and non-interactive eval after
  action-summary hardening; artifact:
  `.local-lab/evals/codex-skill/20260702T132226Z`. Score 5,
  `failure_tags=[]`. The useful output gives five review priorities across
  campaign/budget context, recommendations, search terms with 90-day safety,
  custom segments and change-history/impression-share audit, while blocking
  budget scaling, recommendation apply, negative keyword apply, targeting
  writes, ROAS, waste, CPA, margin and change-impact claims.
- `wilq-custom-segments` had a useful eval failure and fix: the first run
  `.local-lab/evals/codex-skill/20260702T132550Z` failed because operator-facing
  notes leaked the technical term `payload`. The smoke helper now exposes
  `change_preview_count` while still validating the underlying preview
  contract. Passing artifact:
  `.local-lab/evals/codex-skill/20260702T132835Z`. Score 5,
  `failure_tags=[]`; output uses one source-backed segment candidate and blocks
  audience size, ROAS, targeting write, campaign-effectiveness and
  conversion-growth claims until Keyword Planner enrichment and forecast/size
  proof exist.
- `wilq-demand-gen-operator` passed deterministic smoke and the latest
  non-interactive eval as a useful blocker; artifact:
  `.local-lab/evals/codex-skill/20260702T174521Z`. Score 5, `blocked=true`,
  `failure_tags=[]`. WILQ evaluated 18 Ads campaign rows and saw 0 Demand Gen/
  Discovery campaign rows, 0 ads, 0 creative assets and 0 Demand Gen landing-
  quality rows. The API-owned next step now tells the operator to first open
  `act_review_demand_gen_readiness`, confirm the zero-campaign/read-contract
  state, and not judge creative or traffic quality before there is a Demand Gen
  campaign to compare. Launch/readiness/creative-quality/effectiveness claims
  stay blocked.
- `docs/evals/skill-coverage-audit.md` is now generated from the latest passing
  non-interactive eval artifacts by
  `scripts/render_skill_coverage_audit.py`, so the recovery audit does not
  drift after skill replay runs.
- Goal 005 completion check now includes artifact-based latest skill eval
  results in pre-demo gates, not only static case coverage. Current proof:
  `passing=13/13`, `minimum_score=5`, `blocked_correctly=3`; completion still
  remains blocked without real Wilku UAT or explicit owner defer.
- `wilq-campaign-builder` passed deterministic smoke and non-interactive eval
  as a review-only campaign planning workflow; artifact:
  `.local-lab/evals/codex-skill/20260702T133636Z`. Score 5,
  `failure_tags=[]`. It validates `act_prepare_ads_campaign_review_queue` and
  `act_prepare_google_ads_recommendation_review_queue`, uses
  `ads_diagnostics` plus `content_landing_context`, and blocks campaign launch,
  write, performance, conversion-growth and ranking-guarantee claims without
  WILQ confirmation. The eval harness also now forbids runtime cache/retry/
  sandbox noise in operator-facing JSON.
- `wilq-social-publisher` passed deterministic smoke and non-interactive eval
  after one language fix. Initial artifact
  `.local-lab/evals/codex-skill/20260702T133931Z` failed on the awkward phrase
  `tylko do sprawdzenia`; the skill contract now prefers `do ręcznego
  przeglądu`, `bez publikacji` and similar normal wording. Passing artifact:
  `.local-lab/evals/codex-skill/20260702T134213Z`. Score 5,
  `failure_tags=[]`. LinkedIn/Facebook credentials and historical post
  inventory are missing, so publication and duplicate-free claims stay blocked;
  required social history is metadata-only: channel, published date, topic,
  service, claim, CTA, format, post URL/ID and source evidence ID.
- GA4 usefulness review now has a short Wilku-facing decision card at
  `docs/handoffs/2026-07-02-wilku-ga4-start-card.md`. Reviewers scored the
  surface 8/10 for measurement-vs-marketing separation, 7-7.5/10 for marketer
  usefulness and 9/10 for claim blocking. The dashboard first screen now leads
  with `GA4: co dziś zrobić`, `Kolejność pracy` and `Najpierw pomiar` cards for
  `(not set)` rows before traffic-quality decisions.
- `wilq-ga4-analyst` passed deterministic smoke and non-interactive eval after
  the latest lineage/dashboard hardening; artifact:
  `.local-lab/evals/codex-skill/20260702T131857Z`. Score 5,
  `failure_tags=[]`. The useful output orders the work as measurement
  blockers first, landing-page/WordPress mapping second and traffic-quality
  review third, while blocking ROAS, revenue, conversion-drop, GA4-write and
  "measurement fixed" claims.
- Merchant usefulness review now has a short Wilku-facing decision card at
  `docs/handoffs/2026-07-02-wilku-merchant-start-card.md`. Live Merchant data is
  fresh (`refresh_google_merchant_center_a04a45a6e6fd`, about 12.8h,
  `metrics_persisted=true`) with 10476 products, 15 issues and 6 decisions.
  The surface scores 8/10 as a feed-review queue, 5.5/10 for product
  performance/revenue decisions and 9/10 for claim blocking. The dashboard first
  screen now leads with `Merchant: co dziś zrobić`, `Kolejność pracy` and
  `Czego nie obiecywać`.
- `wilq-merchant-feed-operator` passed deterministic smoke and non-interactive
  eval; artifact: `.local-lab/evals/codex-skill/20260702T131438Z`. Score 5,
  `failure_tags=[]`. The useful output starts from `decision_queue`, validates
  `act_review_merchant_feed_issues`, treats problem counts as reported issue
  occurrences rather than unique SKUs, uses product samples only as review
  material and blocks reapproval, revenue, product ROAS, price impact and feed
  write claims.
- Command Center usefulness review now has a short Wilku-facing decision card at
  `docs/handoffs/2026-07-02-wilku-command-center-start-card.md`. Live
  `/api/dashboard/command-center` returns Merchant as the primary next step,
  4 daily decisions, 2 blockers and 24 tactical items. The surface scores
  8.5/10 for the morning daily loop, 8.5/10 for evidence/claim-blocking clarity
  and 7.5/10 as a full BDOS-style daily command. The dashboard first screen now
  shows `Plan dnia w kolejności` and `Blokady dnia` before detailed cards.
- Command Center now exposes top-level lineage aggregated from daily decisions:
  `source_connectors`, `source_connector_labels`, `evidence_ids`,
  `evidence_summary`, `action_ids` and `action_summary`. Live proof after stack
  restart returned 20 evidence IDs, 8 action IDs and sources across Merchant,
  Ahrefs, GSC, WordPress, GA4 and Google Ads, so daily Codex/dashboard flows no
  longer need to infer proof only from nested cards.
- `wilq-daily-command` was re-evaluated after Command Center lineage hardening.
  The first eval correctly failed because the content recommendation used a GA4
  evidence ID without `google_analytics_4` in recommendation source connectors;
  Command Center now derives source connectors from merged evidence IDs. Passing
  eval artifact: `.local-lab/evals/codex-skill/20260702T125722Z`, score 5,
  `failure_tags=[]`, 20 evidence IDs and 4 validated daily actions.
- `/command-center` dashboard first screen now renders API-owned top-level
  proof summaries: source labels, evidence summary and action summary. Wilku no
  longer has to infer daily proof from nested decision cards before trusting the
  morning plan.
- Content Planner usefulness review now has a short Wilku-facing decision card
  at `docs/handoffs/2026-07-02-wilku-content-planner-start-card.md`. Live
  `/api/content/diagnostics` returns 3 decisions, 16 evidence IDs and 5 actions
  across GSC, GA4, Ahrefs and WordPress. The surface scores 8/10 as a content
  decision queue, 5.5/10 as production draft readiness and 8.5/10 for blocking
  unsupported content/result claims. The dashboard first screen now shows
  `Treści: co dziś zrobić`, `Kolejność pracy` and `Czego nie obiecywać` before
  preflight and detailed review sections.
- `wilq-gsc-content-doctor` passed deterministic smoke and non-interactive eval
  after the Command Center lineage work; artifact:
  `.local-lab/evals/codex-skill/20260702T130502Z`. Score 5,
  `failure_tags=[]`. The useful output is a concrete `refresh_or_merge`
  decision for `https://www.ekologus.pl/`, with GSC partial-data limits and
  `act_prepare_content_refresh_queue` validated as review-only.
- `wilq-ahrefs-gap-finder` passed deterministic smoke and non-interactive eval;
  artifact: `.local-lab/evals/codex-skill/20260702T130834Z`. Score 5,
  `failure_tags=[]`. Ahrefs has `gap_read_contract.status=ready`,
  `gap_record_count=8` in the compact contract and 298 gap facts; output treats
  gap record omission as context-pack compaction, not a workflow blocker, while
  keeping traffic/authority/effect claims blocked.
- `wilq-localo-operator` passed deterministic smoke and non-interactive eval;
  artifact: `.local-lab/evals/codex-skill/20260702T131128Z`. Score 5,
  `failure_tags=[]`. Localo access is ready, latest refresh completed, and
  `act_review_localo_visibility_facts` validates as review-only; output uses
  Localo aggregates but keeps local-task completion, profile writes and local
  visibility improvement claims blocked.
- Service Profile usefulness review now has a short Wilku-facing decision card
  at `docs/handoffs/2026-07-02-wilku-service-profile-start-card.md`. Live
  `/api/content/service-profile` returns 10 cards, 7 service cards,
  7 source-backed review-required cards, 0 approved-current cards, 0
  production-depth cards, 5 private ekologus-ai proposals and 13 review
  actions. The surface scores 8/10 as a knowledge-review screen, 4/10 as
  production knowledge and 8/10 for ekologus-ai reviewed source value. The
  dashboard first screen now shows `Wiedza Ekologus: co dziś sprawdzić`,
  review order and production blockers before detailed card/proposal lists.
- Content Workflow usefulness review now has a short Wilku-facing decision card
  at `docs/handoffs/2026-07-02-wilku-content-workflow-start-card.md`. Live
  `/api/content/work-items/queue` returns 3 candidates, but only 1 actionable
  candidate; the active `ekologus` refresh/merge work item has GSC and
  WordPress evidence and `plan_allowed` preflight, while Sales Brief, draft
  package, structured generation, human review and WordPress handoff remain
  blocked. The surface scores 7.5/10 as an honest workflow gate, 4.5/10 as
  production draft readiness and 8.5/10 for write/claim blocking. The dashboard
  first screen now shows `Workflow treści: co dziś zrobić`, the active topic,
  proof count and blocked workflow steps.
- Content Workflow now exposes Claim Ledger as a visible draft gate. Snapshot
  API responses include `claim_ledger`, `/content-workflow` renders
  `Claim Ledger: co wolno powiedzieć`, and dashboard quality review requests
  pass the snapshot ledger instead of `null`. Live proof after local stack
  restart showed
  `claim_ledger_content_work_item_content_decision_https___www_ekologus_pl`
  with one `allowed_with_evidence` claim backed by
  `ev_refresh_refresh_google_search_console_9b25d4143bea`. Wilku-facing handoff:
  `docs/handoffs/2026-07-02-wilku-claim-ledger-gate.md`.
- `wilq-content-operator` was re-evaluated after the Claim Ledger workflow
  slice. Deterministic smoke and non-interactive Codex eval passed; artifact:
  `.local-lab/evals/codex-skill/20260702T120524Z`. Score:
  `operator_usefulness_score=5`, all hard gates true, `failure_tags=[]`. The
  useful output is still a guided blocker/repair workflow, not production
  writing proof, because `queue_status=blocked`, `workflow_blocked=true` and
  only 1 of 3 candidates is actionable.
- `wilq-social-publisher` social-history blocker review passed deterministic
  smoke and non-interactive Codex eval; artifact:
  `.local-lab/evals/codex-skill/20260702T120859Z`. Score:
  `operator_usefulness_score=5`, all hard gates true, `failure_tags=[]`.
  Review-only LinkedIn/Facebook draft actions validate, but publication and
  duplicate-free claims remain blocked because LinkedIn/Facebook credentials
  are missing and `historical_social_inventory_status=missing`. Wilku-facing
  handoff: `docs/handoffs/2026-07-02-wilku-social-history-blocker.md`.
- Social history dedupe now has a typed metadata-only contract in
  `wilq/social/history.py`. `social_history_inventory_v1` is read-only,
  requires only channel/date/topic/service/claim/CTA/format/post ID/source
  evidence metadata, forbids raw post-body requirements and keeps duplicate-free
  social claims blocked until LinkedIn/Facebook history evidence exists.
- `/social-publisher` now has a dedicated dashboard surface over
  `wilq-social-publisher` context-pack. It shows the review-only decision,
  missing LinkedIn/Facebook history blocker and required metadata-only fields in
  Polish, without exposing raw evidence/action IDs or requiring raw post bodies.
- Strict skill eval coverage audit passed on 2026-07-02:
  `case_count=13`, `skill_dir_count=13`, `hard_gap_count=0`,
  `warning_count=0`, `pass=true`. This proves eval coverage structure, not
  perfect output quality for every future prompt. `scripts/pre_demo_gate.sh`
  now runs this audit with `--strict`, so any new WILQ skill without a
  production-like eval case or required output schema field blocks the demo
  gate.
- `wilq-gsc-content-doctor` usefulness eval passed on 2026-07-02; artifact:
  `.local-lab/evals/codex-skill/20260702T123010Z`. Score:
  `operator_usefulness_score=5`, all hard gates true, `failure_tags=[]`.
  It used configured GSC/WordPress evidence, validated
  `act_prepare_content_refresh_queue`, and treated GSC query/page rows as
  latest-available partial data instead of full traffic proof.
- `wilq-content-strategist` usefulness eval passed on 2026-07-02; artifact:
  `.local-lab/evals/codex-skill/20260702T123356Z`. Score:
  `operator_usefulness_score=5`, all hard gates true, `failure_tags=[]`.
  It used GSC, GA4, Ahrefs and WordPress evidence to treat BDO as an
  existing-content refresh/merge candidate, block Zielony Ład until stronger
  source evidence exists and keep GA4 tracking gaps as measurement work rather
  than content topics.
- `wilq-content-strategist` was re-evaluated after pre-demo source coverage and
  Claim Ledger gates were wired in; artifact:
  `.local-lab/evals/codex-skill/20260702T144102Z`. Score:
  `operator_usefulness_score=5`, all hard gates true, `failure_tags=[]`. The
  output again treats BDO as a refresh/merge candidate for an existing
  ekologus.pl URL, blocks Zielony Ład without inventory/canonical/duplicate and
  source evidence, validates `act_prepare_content_refresh_queue`, and blocks
  WordPress/draft/publishing claims.
- `scripts/record_service_profile_review_result.py` and the content-operator
  UAT packet helper now require the same private governance confirmations, so
  recorded review proof cannot omit freshness or audience/scope while the live
  Service Profile action requires them.
- Service Profile private review result reports now also record live private
  proposal provenance from the API: proposal/source IDs, freshness, audience,
  retention, risk, support, redaction and promotion allowance. The markdown
  report renders those fields under live provenance.
- Shared frontend schemas now reject weak private proposal sections with blank
  required text or empty governance lists, matching the backend
  `PrivateSourceProposal` guard before dashboard/API parsing can show them to
  Wilku.
- Wilku handoff examples for private ekologus-ai proposal review now include
  those governance confirmations, so copied review JSON matches the current
  recorder contract.
- Private review contract drift is now guarded: tests compare Service Profile
  private review requirements, recorder private boolean fields and
  `wilq-content-operator` minimal private payload fields.
- Source fact input quality is now guarded before Service Profile/source fact
  compilation: required source fact text fields cannot be blank, and trace/
  governance lists such as connectors, evidence IDs, blocked claims, evidence
  requirements and usage notes cannot contain blank entries. Focused proof:
  `rtk uv run pytest tests/content/test_content_knowledge_cards.py -q`, ruff,
  mypy and `git diff --check`.
- Approved private source proposals now require reviewer provenance at model
  validation time, matching the approved source-fact rule and preventing future
  ekologus-ai/private proposal states from looking approved without a named
  human review.
- Approved private source proposals also require resolved retention and known
  freshness, so an ekologus-ai/private proposal cannot look approved while
  owner retention or source currency remains undecided.
- The approved private proposal state now also rejects `do_not_retain`
  retention and `stale` freshness, so approval cannot represent a source that
  the governance model says should not be retained or is out of date.
- Knowledge-card depth audit is recorded in
  `docs/audits/005-2026-07-01-knowledge-depth-audit.md`. Result: the current
  three cards are typed Goal 004 seeds and useful anti-slop guardrails, but they
  are too broad and internally sourced to prove production-depth Ekologus
  knowledge. Follow-ups: collect source-backed service/claim source pack
  `wilq-seo-ciz`, expand reviewed typed cards `wilq-seo-lt1`, and add
  production-depth guard tests `wilq-seo-t13`. Focused proof passed:
  `rtk uv run pytest tests/content/test_content_knowledge_cards.py -q`.
- Daily Command BDOS-class eval proof on 2026-07-02:
  `.local-lab/evals/codex-skill/20260702T024250Z`. The non-interactive eval
  passed with `operator_usefulness_score=5`, 20 evidence IDs, four
  recommendations, four validated daily actions and all hard gates true. The
  final answer kept the daily loop to Merchant, Content, GA4 and Google Ads via
  `command_center.daily_decisions`, used `primary_next_step`, and did not
  promote Localo or social drafts as main daily work.
- Ads Doctor BDOS-class eval proof on 2026-07-02:
  `.local-lab/evals/codex-skill/20260702T025015Z`. The non-interactive eval
  passed with `operator_usefulness_score=5`, two Ads evidence IDs, five
  prioritized review recommendations, five action candidates and all hard gates
  true. It used full Ads diagnostics/full context, validated four review
  actions, kept Keyword Planner/forecast blockers explicit, and blocked
  CPA/ROAS, wasted-budget, budget scaling, negative-keyword apply and write
  claims without human review, confirmation, write contract and audit.
- Merchant Feed Operator BDOS-class eval proof on 2026-07-02:
  `.local-lab/evals/codex-skill/20260702T025422Z`. The non-interactive eval
  passed with `operator_usefulness_score=5`, four evidence IDs, two
  recommendations, two action candidates and all hard gates true. It kept the
  final work grouped by `decision_queue`, treated `product_count` as reported
  issue occurrences rather than unique SKUs, validated
  `act_review_merchant_feed_issues`, used `sample_product_ids` only as review
  samples, and blocked product-level ROAS/revenue, price-impact, product
  reapproval and product-feed write claims without missing contracts and audit.
- Content Operator review-recorder eval guard on 2026-07-02:
  `.local-lab/evals/codex-skill/20260702T040247Z`. The eval contract now fails
  unless `wilq-content-operator` shows the Service Profile review recorder
  path and prepare-only promotion-preview markers in the actionable output:
  `review_result_recorders`, `record_service_profile_review_result.py`,
  public/private result report types, `private_source_proposals` and
  `promotion preview`.
- Content Operator review-requirements eval guard on 2026-07-02:
  `.local-lab/evals/codex-skill/20260702T043747Z`. The eval contract now also
  requires `review_requirements`, `source_trace_clear`,
  `blocked_claims_reviewed` and `follow_up_beads` in actionable output. The
  live eval passed with `operator_usefulness_score=4`, `blocked=true`,
  `failure_tags=[]` and all hard gates true.
- Content Operator live-review-requirements authority guard on 2026-07-02:
  `.local-lab/evals/codex-skill/20260702T090533Z`. The eval contract now
  requires `live_review_requirements_authoritative`,
  `API-owned review_requirements` and `minimal field lists are a floor` in
  actionable output. The smoke contract also emits `knowledge_card_count=10`
  even when the queue is blocked, so the non-interactive eval has stable
  API-owned markers for Service Profile review authority.
- Content Operator UAT markdown on 2026-07-02 now renders Service Profile
  review requirements for public/private review actions: required fields
  `action_id,target_card_id,decision,source_trace_clear,blocked_claims_reviewed,notes`
  and the `follow_up_beads` blocking rule.
- Service Profile private proposals now expose governance metadata through the
  same API/dashboard/UAT path: `data_classes`, `source_block_refs`,
  `retention_decision`, `deletion_path` and `eval_case_ids`. Live proof after
  stack restart showed the fields on `/api/content/service-profile`, the
  private proposal promotion preview action and the UAT packet without exposing
  raw private content.
- Service Profile private proposal scope counts on 2026-07-02: live
  `/api/content/service-profile` and the UAT packet now expose
  `proposal_count=5`, `service_proposal_count=2`,
  `claim_policy_proposal_count=2`, `evidence_requirement_proposal_count=1` and
  `promotion_ready=false`, and `/service-profile` renders those counts for
  Wilku without exposing raw private content.
- Service Profile review-action summary on 2026-07-02: live API now owns the
  review-action breakdown consumed by dashboard and UAT packet:
  `total_count=13`, `review_request_count=12`, `prepare_count=1`,
  `public_service_review_count=6`, `private_review_count=5`,
  `private_service_review_count=2`, `private_policy_review_count=3`.
- Service Profile review actions now expose `review_scope` and `priority`.
  Live private `ekologus-ai` actions split service proposals as
  `private_service_proposal` / `medium` and claim-policy proposals as
  `private_claim_policy_proposal` / `high`; dashboard and UAT packet render the
  typed fields directly.
- Service Profile review actions now also expose `decision_options` aligned
  with the review recorder: `approve`, `needs_changes`, `stale`, `reject`.
  Live API and UAT packet both return those options on private service and
  claim-policy review actions.
- `ekologus-ai` source facts now have model-level governance validation before
  they can appear as private proposals. Any fact using
  `ekologus_ai_private_source_catalog` must be a private/reviewed source type,
  `redacted_only`, `review_required`, and carry blocked claims, evidence
  requirements and usage notes. Focused proof loaded 11 source facts, including
  4 private `ekologus-ai` facts, all redacted and review-required.
- Source-fact registry lineage is now guarded at the registry level: duplicate
  `source_id` values and mismatched `fact_count` are invalid before knowledge
  cards, Service Profile or review actions can compile ambiguous source
  handles. Focused proof:
  `rtk uv run pytest tests/content/test_content_knowledge_cards.py -q`.
- Private source proposal registry handles are guarded the same way: duplicate
  `proposal_id` values and mismatched `proposal_count` are invalid before
  redacted `ekologus-ai` proposals reach Service Profile review actions.
- Approved source facts now also require `reviewer`, `evidence_ids` and
  `source_connectors` at the model layer. This prevents a future
  `approved_current` knowledge card from being unlocked by reviewed prose
  without traceable evidence lineage.
- Sales Brief knowledge constraints and structured draft model input now carry
  knowledge-card `evidence_ids`. This extends source-fact/card lineage into the
  actual generation contract, so review-required constraints can point to WILQ
  evidence instead of only card IDs.
- Connector status no longer treats `completed` refresh runs with
  `metrics_persisted=false` as successful vendor reads. If no usable earlier
  success exists, freshness becomes unknown with an explicit incomplete-read
  note instead of a normal fresh/green state.
- Content Workflow now renders Sales Brief knowledge constraints with their
  WILQ evidence IDs in the operator-facing proof panel. Wilku can see why a
  brief is review-required and which proof handle supports that constraint
  without opening raw JSON.
- `wilq-content-operator` UAT packet now includes `sales_brief_trace` per
  item. When a Sales Brief exists, it lists shown knowledge constraints and
  their evidence IDs; when the workflow is blocked earlier, it records the
  blocker/missing snapshot state instead of hiding the gap.
- The UAT markdown packet now also renders blocked/missing Sales Brief trace in
  Polish. Current live top candidates show `Sales Brief: zablokowany albo
  niedostępny (snapshot nie zawiera sales_brief)`, which makes the lack of a
  brief visible during Wilku review instead of silently omitting it.
- Goal 005 UAT result recorder now persists live Sales Brief trace for the
  selected work item in `live_provenance`. Current live proof for
  `content_work_item_content_decision_https___www_ekologus_pl` records
  `selected_sales_brief_status=blocked` with blockers `Brakuje karty usługi`
  and `Brakuje karty CTA`, so the saved UAT report preserves what Wilku saw.
- Goal 005 completion guard now keeps that Sales Brief provenance when a UAT
  result is valid but still needs follow-up. Live proof with `--api-base`
  remains `blocked_missing_goal_005_uat_proof` and renders the same Sales Brief
  blockers, so the completion audit cannot lose the gate that blocked the
  selected item.
- The Wilku-ready content UAT handoff now matches that live state: it explains
  the current Sales Brief blocker for the selected actionable item, asks Wilku
  whether the blocker is understandable, and points the post-session check to
  `goal_005_completion_check.py` without claiming completion.
- A Wilku-ready review handoff now exists for the two private `ekologus-ai`
  claim-policy proposals: `docs/handoffs/2026-07-02-wilku-ekologus-ai-policy-review.md`.
  Live recorder proof validates their action IDs as private proposal review and
  keeps the result at `needs_follow_up_before_promotion_request` with
  `promotion_allowed=false`.
- A plain-language "what to show Wilku first" guide now lives at
  `docs/handoffs/2026-07-02-co-pokazac-wilkowi.md`. Use it as the first
  conversation script; the longer UAT handoff remains the detailed backing
  material and result format.
- A plain-language WILQ marketing/content model now lives at
  `docs/handoffs/2026-07-02-wilq-marketing-content-model.md`. It explains WILQ
  as a BDOS-class operating system for Ekologus marketing, not a content
  generator: daily queue, content decisions, Sales Brief, Claim Ledger, draft
  review, social repurpose review, measurement loop and explicit blocked
  claims. The "what to show Wilku first" guide starts with this model.
- Goal 005 UAT result reports now also warn when the WILQ marketing/content
  model handoff is not listed in `pokazane_materialy_review`. A real Wilku
  review should start from the plain-language operating model before detailed
  BDO/private-source/Service Profile handoffs.
- Goal 005 completion guard now treats those missing plain-language review
  artifacts as a completion blocker. A UAT result can remain valid evidence,
  but it cannot close Goal 005 if Wilku was not shown the WILQ marketing/content
  model and the "co pokazać Wilkowi" guide first.
- Informal Wilku feedback on 2026-07-02 is recorded in
  `docs/handoffs/2026-07-02-wilku-informal-positive-feedback.md`: the user
  reported that Wilku said the current WILQ direction/materials are very good.
  Treat this as a strong positive direction signal, not as structured Goal 005
  UAT completion proof.
- Service Profile review recorder now validates live API-owned
  `review_requirements` per action. Private `ekologus-ai` proposal review
  results must satisfy the required governance fields currently exposed by
  `/api/content/service-profile`, and live provenance records those required
  fields without promoting source facts or unlocking production-depth.
- The `wilq-content-operator` UAT packet now marks live
  `review_requirements` as authoritative for Service Profile review recorder
  payloads. Static minimal payload field lists are only a floor; the recorder
  validates the current API-owned requirements for each live action ID.
- Goal 005 UAT result reports now warn when
  `docs/handoffs/2026-07-02-co-pokazac-wilkowi.md` is not listed in
  `pokazane_materialy_review`. This is non-blocking, but it protects Wilku
  review from starting with only technical handoffs.
- `AGENTS.md` now defines WILQ as a BDOS-class Marketing Operating System for
  the full Ekologus marketing loop: SEO, content, Ads, GA4, Merchant, Localo,
  WordPress, social readiness, knowledge, safe actions, measurement and
  learning. Do not narrow WILQ to "marketing copy/content generation" in future
  sessions.
- `AGENTS.md` now also lists BDOS-style WILQ workflows in marketing/content
  language: daily command, content doctor, Sales Brief, Claim Ledger, draft
  review, GSC opportunities, GA4 quality split, Ads Doctor, Merchant review,
  social review and measurement loop.
- Social publishing readiness now has an explicit historical-post blocker in
  the API-owned `social_draft_context`: historical LinkedIn/Facebook inventory
  is `missing`, duplicate-risk is `blocked_until_social_history_review`, and
  the claim `brak powtórzeń historycznych postów` is blocked until prior posts
  are reviewed.
- Social history now has a versioned read-only inventory contract inside
  `social_draft_context.social_history_inventory`. Live `wilq-social-publisher`
  smoke after stack restart on 2026-07-02 shows
  `contract=social_history_inventory_v1`, required sources `linkedin` and
  `facebook`, missing evidence IDs `linkedin_historical_posts` and
  `facebook_historical_posts`, metadata-only required fields
  `channel,published_at,topic,service,claim,cta,format,post_url_or_id,source_evidence_id`,
  `raw_post_body_allowed=false` and duplicate-free claims blocked until history
  review. This is still not a social connector/import; it is the typed contract
  for what WILQ must collect before dedupe/reuse claims.
- Social Publisher history/duplication eval proof was hardened on 2026-07-02:
  `.local-lab/evals/codex-skill/20260702T083900Z`. The non-interactive eval now
  requires actionable output to mention `social_history_inventory`,
  `social_history_inventory_v1`, `metadata-only`, `source_evidence_id` and
  `brak powtórzeń historycznych postów`. It passed with
  `operator_usefulness_score=4`, five evidence IDs, one recommendation, two
  validated LinkedIn/Facebook draft actions and explicit blocking of
  duplicate-free social claims until `linkedin_historical_posts` and
  `facebook_historical_posts` evidence exists.
- The approved source-fact happy path is regression-tested too: a reviewed fact
  with evidence IDs and source connectors compiles to `approved_current`,
  preserves source lineage/connectors, keeps blocked claims, and is the only
  isolated source-fact path that unlocks production-depth readiness.
- Compiled knowledge cards and Service Profile service sections now carry
  `evidence_ids` from source facts. This closes the traceability gap where
  approved facts required evidence IDs but downstream cards only exposed source
  fact IDs and connectors.
- Mixed source-fact lifecycle is regression-tested: if an approved fact and a
  review-required fact compile into the same card, the card remains
  `source_backed_review_required` and cannot unlock production-depth readiness.
- Review-required source facts without their own evidence IDs now compile with
  fallback evidence `ev_content_service_profile_source_facts`, which proves
  Service Profile/source-fact lineage exists without implying human approval.
- Dashboard Service Profile service cards now render those WILQ evidence IDs in
  the operator-facing source/review block, so Wilku can see the proof handle
  without opening raw JSON.
- Goal 005 completion is now guarded by
  `scripts/goal_005_completion_check.py`. It fails closed unless given a
  validated real UAT result from `scripts/record_goal_005_content_uat_result.py`
  or an explicit owner defer JSON with residual risk and blocked claims. This
  prevents claiming Goal 005 completion, Wilku usefulness, production-depth
  readiness or final draft/publish readiness without proof.
- Goal 005 owner defer proof now must include `nastepny_input_uat`, not only
  residual risk and `nastepny_przeglad`. The completion guard returns and
  renders the exact next UAT material/input so an owner defer cannot be a vague
  postponement.
- Goal 005 owner defer proof now must also explicitly keep the core completion
  claims blocked: `ukończony Goal 005`,
  `realny dowód użyteczności dla Wilka`, `production-depth readiness` and
  `gotowość finalnego draftu albo publikacji`. A generic or softer
  `czego_nie_wolno_twierdzic` list no longer passes the guard.
- Goal 005 UAT-result proof now distinguishes a valid session record from a
  completion-ready session. A result with
  `needs_follow_up_before_full_content_uat` remains valid evidence, but
  `scripts/goal_005_completion_check.py` returns blocked status and exit code
  `1` until the UAT status is `ready_for_full_content_uat` or the owner records
  an explicit defer.
- Runtime import audit follow-up on 2026-07-02 found that `wilq/credentials`
  existed locally but was ignored by `.gitignore`, which explained the
  GitHub-visible `wilq.credentials.runtime` 404 risk. The package is now
  intended to be committed and protected by `tests/test_runtime_imports.py`.
- Connector/job refresh hardening from the same audit now exposes
  `ConnectorRefreshRun.metrics_persisted`. If metric persistence fails after a
  connector run is created, WILQ rewrites the run as `failed` with a sanitized
  `metric_persistence_failed:<ErrorType>` marker. Manual jobs also isolate
  per-connector exceptions and always persist a `JobRun`; job-run API calls now
  clear API view-model caches like direct connector refreshes.
- Connector refresh trust hardening on 2026-07-02 now also treats historical
  `completed` runs with `metrics_persisted=false` as incomplete in
  operator-facing labels: `odczyt niepełny - metryki nieutrwalone`. GA4,
  Merchant, Ads, Localo, Ahrefs and content diagnostics inherit the label, and
  the dashboard refresh-run list shows metric persistence directly instead of a
  normal green refresh.
- Follow-up trust gate hardening now also requires persisted metrics before a
  completed vendor read can unlock `live_data_available`, trusted facts,
  command-center/brief blocker clearance or content vendor-read preflight. This
  prevents a hard-crash edge case from reusing old metric facts as current
  evidence.
- Connector scope clarity slice on 2026-07-02 adds API-owned
  `product_scope`, `product_scope_label` and `active_for_daily_work` to
  connector status. Live `/api/connectors` now marks Google Ads and other core
  data sources as `production`, Google Sheets as `optional_disabled`,
  LinkedIn/Facebook as `experimental`, and OpenAI Codex as `runtime` rather
  than a marketing data source. Dashboard connector access summary uses these
  fields so placeholder/review-only surfaces do not look like daily-production
  evidence.
- Dashboard surface registry slice on 2026-07-02 adds
  `apps/dashboard/src/routes/surfaceRegistry.ts` as the single typed source for
  route path, nav visibility, family and status. `App.tsx` now generates
  operating routes from `generatedSurfaceRoutes`, while `Shell.tsx` renders nav
  from `primarySurfaceRoutes`. Placeholder/experimental routes remain routable
  only when deliberately classified, not by accidental hidden arrays.
- Diagnostic UI dedupe proof on 2026-07-02 adds shared
  `DiagnosticPage<TData>` in `DiagnosticSurfaceShell.tsx` and migrates
  `LocaloDiagnosticSurface` plus `Ga4DiagnosticSurface` to it. The routes keep
  domain-specific decision, proof and safety content, while
  loading/error/shell behavior now lives in one reusable component. Merchant or
  Content should be the next candidate only if the diff keeps domain copy clear.
- Diagnostic UI dedupe proof now also covers `DemandGenDiagnosticSurface`.
  Demand Gen uses the shared `DiagnosticPage<TData>` for loading/error/shell
  behavior while keeping its readiness contract, preview cards, Ads/GA4 proof
  and blocked claims domain-specific.
- GA4 Analyst measurement-vs-marketing eval proof on 2026-07-02:
  `.local-lab/evals/codex-skill/20260702T025826Z`. The non-interactive eval
  passed with `operator_usefulness_score=4`, 12 evidence IDs, three
  recommendations, three action candidates and all hard gates true. It
  separated `fix_measurement` rows with `(not set)` from `review_traffic_quality`
  rows for `google / cpc`, validated `act_review_ga4_tracking_quality`, did not
  invent `review_landing_mapping` as a real queue item, and blocked
  profitability, revenue, conversion-rate, ROAS, GA4 write and "measurement
  fixed" claims without separate contracts.
- Skill coverage audit is refreshed in `docs/evals/skill-coverage-audit.md`
  after the July 2 BDOS-class evals. It now records 13 skills, current fresh
  artifacts where available, live API connector context (`12` connectors, `9`
  configured, `2` missing credentials) and the current strongest operator paths
  instead of the old June 24 12-skill snapshot.
- Ahrefs Gap Finder eval proof on 2026-07-02:
  `.local-lab/evals/codex-skill/20260702T030715Z`. The non-interactive eval
  passed with `operator_usefulness_score=4`, eight Ahrefs evidence IDs, two
  recommendations, three review-only action candidates and all hard gates true.
  It kept lineage scoped to `ahrefs`, handled `gap_records_omitted=true` as
  context compaction rather than a blocker, avoided unrelated action IDs, and
  blocked traffic/autorytet growth promises. The eval harness now also tells
  Codex not to use technical runtime names such as `ActionObject` in
  operator-facing text.
- GSC Search Analytics proof on 2026-07-02:
  `refresh_google_search_console_9b25d4143bea` completed after the adapter
  changed query/page detail reads from `rowLimit=250` to `rowLimit=1000` while
  keeping WILQ's operational max rows at `1000`. The public API contract still
  exposes the official GSC pattern: latest available single day, typical 2-3
  day delay, `api_recommended_page_size=25000`,
  `api_daily_row_cap_per_search_type=50000`, `partial_possible` query/page
  detail and labels that warn this is not a full Search Analytics export.
  Non-interactive proof passed at
  `.local-lab/evals/codex-skill/20260702T031401Z` with
  `operator_usefulness_score=5`, source connectors scoped to
  `google_search_console`, `wordpress_ekologus`, `wordpress_sklep`, and no
  Ahrefs leakage in the operator lineage.
- Claim Ledger / Generation Gate gap audit on 2026-07-02 found that the core
  safety gates were already implemented, but the ledger still lacked explicit
  typed metadata for weak and required claims. `ContentClaimLedgerEntry` and
  structured draft claim markers now carry `strength=strong|weak` and
  `required=true|false`. Structured preview and Quality Review block
  `required_claim_missing` when a required allowed claim is omitted from the
  output, while shared schemas preserve the new marker fields. Focused proof:
  `rtk uv run pytest tests/content -q`, `rtk pnpm --filter @wilq/shared-schemas
  test`, and `rtk pnpm typecheck` in `packages/shared-schemas`.
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
- BDO Wilku UAT review artifact now lives at
  `docs/handoffs/2026-07-02-wilku-bdo-uat-review.md`. It uses live WILQ
  Service Profile and content queue evidence to separate BDO review value from
  the current live queue state: BDO is a source-backed review-required service
  card and historical strong UAT topic, but it is not a live work item on
  2026-07-02 and does not authorize a final draft.
- Goal 005 UAT result recorder now requires `pokazane_materialy_review`: a
  real UAT result must list existing repo-relative `docs/handoffs/` artifacts
  shown to Wilku. Live proof with `--api-base http://127.0.0.1:8000` validates
  the current queue, Service Profile, review action counts and shown BDO,
  Eko-Opieka and Audyt zgodności handoffs without claiming UAT completion.
- Goal 005 UAT result recorder now also requires `punkty_niezrozumienia`.
  The report renders explicit confusion points next to source-trace questions,
  off-brand/generic findings and follow-ups. Live proof on 2026-07-02 with
  `--api-base http://127.0.0.1:8000` passed against the current blocked queue,
  3 candidates, 1 actionable candidate and read-only Service Profile.
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
- Service Profile review actions now include non-persistent per-service review
  requests for source-backed public service cards. Live proof after stack
  restart on 2026-07-02: `review_action_count=10`,
  `public_card_review_count=6`, targets include
  `ekologus_service_operat_wodnoprawny`, and `can_promote_facts=false` remains.
  These actions tell Wilku what to review without promoting facts or cards.
  The dashboard Service Profile service cards now render visible source trace:
  source connectors, source fact IDs, source lineage URLs and review hints, so
  public service-card review can happen from the UI rather than raw API output.
  Focused proof passed: `rtk pnpm --filter @wilq/dashboard test --
  ServiceProfileSurface.test.tsx --runInBand` and
  `rtk pnpm --dir apps/dashboard typecheck`.
- Public service-card review results now have a deterministic fail-closed
  recorder: `scripts/record_service_profile_review_result.py`. It validates
  reviewer/date/scope, live Service Profile action/card IDs, source-trace
  clarity, blocked-claim review and follow-up Beads for blocking decisions. It
  renders a report only; it does not edit `source_facts.json`, change lifecycle
  status, set `approved_current` or unlock production-depth. Live proof on
  2026-07-02 accepted BDO review action/card IDs with
  `live_public_review_action_count=6`, `promotion_allowed=false` and
  `production_depth_ready=false`.
- The same recorder now supports private `ekologus-ai` proposal review results
  with `review_type=private_source_proposals`. It validates live
  `service_profile_review_private_proposal_*` action IDs against
  `private_source_proposals`, records redacted review feedback, and still keeps
  `promotion_allowed=false`. Live proof on 2026-07-02 accepted
  `service_profile_review_private_proposal_ekologus_ai_kb001_eko_opieka_review_candidate_2026_07_01`
  with `live_private_review_action_count=4`,
  `private_proposal_promotion_ready=false` and
  `production_depth_ready=false`.
- Service Profile review results now also validate approved decisions against
  the matching prepare-only promotion ActionObject preview. A public approve
  must exist in `act_prepare_service_profile_knowledge_promotion`, while a
  private approve must exist in
  `act_prepare_service_profile_private_proposal_promotion`; otherwise the
  recorder refuses to claim readiness for a promotion request. Live proof on
  2026-07-02 saw 4 private review actions and 4 private promotion preview rows,
  still with `promotion_allowed=false`.
- Service Profile review now has a central prepare-only ActionObject for the
  next promotion gate: `act_prepare_service_profile_knowledge_promotion`.
  It exposes 6 public service-card promotion-preview rows from source facts,
  validates with `valid=true`, uses evidence
  `ev_content_service_profile_source_facts`, and returns marketer preview cards
  with `kind=service_profile_knowledge_promotion_review`. Live API proof after
  stack restart on 2026-07-02: `preview_status=blocked`,
  `preview_contract=service_profile_knowledge_promotion_preview_v1`,
  `apply_allowed=false`, `api_mutation_ready=false`. This prepares the audited
  promotion request path without editing `source_facts.json`, changing
  lifecycle status, setting `approved_current` or unlocking production-depth.
- The `wilq-content-operator` context-pack now has a focused regression guard
  for both Service Profile promotion review actions. Live proof after stack
  restart on 2026-07-02 confirmed that
  `act_prepare_service_profile_knowledge_promotion` and
  `act_prepare_service_profile_private_proposal_promotion` are exposed through
  `active_action_objects`, omit raw payloads, keep
  `ev_content_service_profile_source_facts`, and use distinct preview card
  kinds for public knowledge promotion vs private proposal review.
- The `wilq-content-operator` UAT packet now carries the fail-closed Service
  Profile review-result recorder contract directly, not only in handoff docs.
  Live proof on 2026-07-02 returned
  `service_profile_public_card_review_result_v1` with 6 public promotion
  preview rows and `service_profile_private_proposal_review_result_v1` with 4
  private promotion preview rows; both still state that recorder output does
  not promote source facts or knowledge cards.
- The `wilq-content-operator` UAT packet now includes live Service Profile
  evidence instead of only queue/enrichment items. Live proof on 2026-07-01:
  `uat_readiness.status=blocked_for_full_uat`,
  `recommended_scope=review/blokady i traceability`, gaps
  `gap_service_operat_wodnoprawny` and `gap_no_approved_current_cards`,
  `private_review_action_count=2`. It now also carries private proposal
  `promotion_ready=false`, the promotion blocked reason and the 5-item
  promotion checklist from Service Profile. Live proof on 2026-07-02 added
  `private_proposal_details`: 2 redacted details with support/risk/blocked
  claims and `promotion_allowed=false`. A later 2026-07-02 proof now also
  separates `public_service_review_actions` from `private_review_actions`:
  6 public service-card reviews, 2 private proposal reviews, 10 review actions
  total, and UAT blockers for public service review, private proposal review
  and non-production-depth Service Profile. This prepares Goal 005 UAT without
  claiming that Wilku completed the session.
- Goal 005 dashboard verification gate is restored: stale dashboard test
  fixtures now satisfy the current `ContentWorkItem` and structured draft
  generation contracts, including typed inventory/canonical/duplicate statuses
  and `knowledge_constraints`. Focused proof passed:
  `rtk pnpm --dir apps/dashboard typecheck`,
  `rtk pnpm --filter @wilq/dashboard test -- api.test.ts --runInBand` and
  `rtk pnpm --filter @wilq/dashboard test -- ContentWorkflowSurface.test.tsx --runInBand`.
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
- Non-interactive skill evals now have OpenAI-aligned hard gates and failure
  tags in addition to `operator_usefulness_score`. The result schema requires
  `eval_rubric` and `failure_tags`; the harness caps usefulness at 3 when any
  hard gate fails and requires matching failure tags. First live proof:
  `.local-lab/evals/codex-skill/20260702T001627Z` for
  `wilq-gsc-content-doctor` passed with score 4, six evidence IDs, one
  validated action, empty failure tags and all hard gates true.
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
  the current content-operator packet. It now states that full UAT remains
  blocked by non-production-depth Service Profile, public service-card review,
  private proposal review and blocked queue state, not by stale
  Merchant/content sources.
- Goal 005 content UAT result proof now has a deterministic checker:
  `scripts/record_goal_005_content_uat_result.py`. It validates the filled
  session result fields for selected work item, blocker understanding, Service
  Profile readability, public and private review actions, source-trace
  questions, generic/off-brand findings, largest product gap and follow-up
  Beads when full UAT remains blocked. It renders a review report only; it does
  not promote private proposals, approve service cards, unlock publishing or
  close Goal 005.
- The same UAT result checker now supports live WILQ provenance with
  `--api-base`: selected work item must exist in the current content UAT queue,
  and the report records queue status, selected evidence/source connectors,
  Service Profile read-only state, production-depth readiness, public/private
  review action counts and private proposal promotion state. Live proof on
  2026-07-02 accepted
  `content_work_item_content_decision_https___www_ekologus_pl` with GSC and
  WordPress evidence, `queue_status=blocked`, `production_depth_ready=false`
  `public_service_review_action_count=6` and `private_review_action_count=2`.
  It now refuses to validate a result when public service review feedback is
  missing.
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
  non-interactive threshold `operator_usefulness_score >= 5`. Freshness handling
  is part of the gate: stale connector snapshots require refresh, repair path or
  blocker before recommendation.
- `scripts/codex_skill_eval.sh` now uses the same score-five default when an
  eval case does not declare `minimum_operator_usefulness_score`, and
  `tests/test_codex_skill_eval_cases.py` blocks regressions back to score 4.
- `wilq-merchant-feed-operator` now has a fresh live non-interactive usefulness
  proof at `.local-lab/evals/codex-skill/20260702T012547Z/summary.json`.
  Result: `operator_usefulness_score=4`, all hard gates true, no failure tags,
  4 evidence IDs, 2 recommendations and validated
  `act_review_merchant_feed_issues`. The eval case now uses Polish-inflected
  route markers (`produktów`, `pliku produktowego`) after two false failures,
  while still requiring Merchant/product intent, freshness, missing read
  contracts and blocked product ROAS/revenue/price-impact/feed-write claims.
- `wilq-ads-doctor` now has a fresh live non-interactive usefulness proof at
  `.local-lab/evals/codex-skill/20260702T013936Z/summary.json`. Result:
  `operator_usefulness_score=4`, all hard gates true, no failure tags,
  12 evidence IDs, 5 recommendations and 4 validated action candidates:
  `act_prepare_ads_campaign_review_queue`,
  `act_prepare_google_ads_recommendation_review_queue`,
  `act_prepare_custom_segments_from_search_terms` and
  `act_prepare_negative_keyword_review_queue`. The eval harness now also fails
  recommendation-level evidence IDs or source connectors that are absent from
  top-level lineage, after an earlier Ads run exposed an evidence ID typo.
- `wilq-ga4-analyst` now has a tightened live non-interactive usefulness proof
  at `.local-lab/evals/codex-skill/20260702T014440Z/summary.json`. Result:
  `operator_usefulness_score=4`, all hard gates true, no failure tags,
  12 evidence IDs, 5 recommendations and validated
  `act_review_ga4_tracking_quality`. The GA4 eval case now includes
  GA4-specific `blocked_claim_terms` for opłacalność/ROI/przychód/konwersje
  and measurement-repair claims, while still requiring the skill to separate
  measurement blockers from traffic-quality review candidates through
  `ga4_diagnostics.decision_queue`.
- `wilq-custom-segments` now has a tightened live non-interactive usefulness
  proof at `.local-lab/evals/codex-skill/20260702T015121Z/summary.json`.
  Result: `operator_usefulness_score=4`, all hard gates true, no failure tags,
  2 evidence IDs, 1 recommendation and validated
  `act_prepare_custom_segments_from_search_terms`. The eval now explicitly
  requires the Keyword Planner blocker `keyword_planner_enrichment` and blocks
  `wzrost konwersji`; an intermediate failed run caught blocked claim terms in
  a non-blocked recommendation label, so the skill output contract now keeps
  audience/return/performance/write claims in blocker fields instead of segment
  recommendation copy.
- `wilq-demand-gen-operator` now has a live non-interactive blocker proof at
  `.local-lab/evals/codex-skill/20260702T174521Z/wilq-demand-gen-operator/result.json`.
  Result: `operator_usefulness_score=5`, `blocked=true`, all hard gates true,
  no failure tags, 20 evidence IDs and validated `act_review_demand_gen_readiness`.
  Manual inspection of an earlier passing run found a malformed top-level
  evidence ID with whitespace, so `scripts/codex_skill_eval.sh` rejects
  whitespace/empty identifiers in top-level lineage IDs and action IDs.
- `wilq-ahrefs-gap-finder` now has a live non-interactive review-only proof at
  `.local-lab/evals/codex-skill/20260702T020118Z/summary.json`. Result:
  `operator_usefulness_score=4`, `blocked=false`, all hard gates true, no
  failure tags, 8 evidence IDs, 2 recommendations and no action IDs. The Ahrefs
  smoke now respects `gap_read_contract.gap_record_count` when
  `gap_records_omitted=true` in compact context-pack payloads, and the skill
  contract treats compaction as review-ready evidence rather than missing
  records while still blocking `wzrost ruchu` and `wzrost autorytetu` claims.
- `wilq-localo-operator` now has a live non-interactive review-only proof at
  `.local-lab/evals/codex-skill/20260702T020751Z/summary.json`. Result:
  `operator_usefulness_score=4`, `blocked=false`, all hard gates true, no
  failure tags, 2 evidence IDs, 2 recommendations and validated
  `act_review_localo_visibility_facts`. The Localo contract now separates
  access-ready diagnostics/review from blocked local task/write/uplift claims,
  and the smoke now exposes the full action preview contract
  `local_visibility_review_preview_v1`.
- `wilq-campaign-builder` now has a live non-interactive prepare-only proof at
  `.local-lab/evals/codex-skill/20260702T021145Z/summary.json`. Result:
  `operator_usefulness_score=4`, `blocked=false`, all hard gates true, no
  failure tags, 16 evidence IDs, 2 recommendations and validated
  `act_prepare_ads_campaign_review_queue` plus
  `act_prepare_google_ads_recommendation_review_queue`. Manual inspection of an
  earlier passing run found an evidence ID typo, so the eval prompt now tells
  Codex to copy IDs exactly from smoke/API output and never reconstruct similar
  identifiers.
- `wilq-social-publisher` now has a live non-interactive review-only proof at
  `.local-lab/evals/codex-skill/20260702T083900Z/summary.json`. Result:
  `operator_usefulness_score=4`, `blocked=false`, all hard gates true, no
  failure tags, 5 evidence IDs, 1 recommendation and validated
  `act_prepare_linkedin_social_drafts` plus
  `act_prepare_facebook_social_drafts`. LinkedIn/Facebook publication remains
  blocked by `missing_publish_access`; the useful behavior is draft-review
  action preparation plus explicit `social_history_inventory_v1` /
  metadata-only history requirements, not social publishing or performance
  claims. The eval prompt now requires exact dashboard route markers in `notes`
  so route-specific
  coverage is deterministic instead of relying on incidental wording.
- `wilq-gsc-content-doctor` now has a fresh live non-interactive Search
  Analytics proof at
  `.local-lab/evals/codex-skill/20260702T022132Z/summary.json`. Result:
  `operator_usefulness_score=4`, `blocked=false`, all hard gates true, no
  failure tags, 10 evidence IDs, 1 recommendation and validated
  `act_prepare_content_refresh_queue`. The output names the latest available
  detail day, `data_availability_checked=true`, `search_type=web`,
  `detail_dimensions=query,page`, `detail_data_completeness=partial_possible`,
  `rowLimit`/`startRow`, 25k/50k official paging limits and the operator-facing
  caveat that query/page evidence is partial Search Analytics signal, not a full
  traffic export. The eval/test marker terms now allow Polish inflection while
  keeping the exact partial-data decision marker.
- `wilq-content-strategist` now has a fresh live anti-slop planning proof at
  `.local-lab/evals/codex-skill/20260702T023811Z/summary.json`. Result:
  `operator_usefulness_score=4`, `blocked=true`, all hard gates true, no
  failure tags, 17 evidence IDs, 2 recommendations and validated
  `act_prepare_content_refresh_queue`. The output treats BDO and `art 400`
  topics as refresh/merge of existing WordPress URLs, blocks `zielony ład` until
  evidence and inventory are present, surfaces the GA4 measurement issue as
  `problem pomiaru, nie temat treści`, and keeps WordPress draft/publish,
  ranking/lead/revenue and duplicate-free claims blocked. The content strategist
  smoke now exposes brief-preview `obiekcje`, source-fact labels, exact
  `ekologus.pl` and gate markers; the eval harness also rejects recommendation
  evidence IDs whose connector is missing from the same recommendation.
  The Ads case blocks CPA, ROAS, budget scaling, recommendation writes,
  campaign writes and negative-keyword writes without full review/audit while
  avoiding brittle exact wording for areas already proven by validated actions.
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
- Claim Ledger now also requires evidence for reviewed legal, risk and
  environmental claims. Human review alone no longer lets a high-risk claim
  become `allowed_general`/publish-ready; missing proof blocks with
  `missing_evidence` and the claim stays outside draft readiness.
- Sales Brief now blocks product or purchase CTA when WILQ has no Merchant or
  shop evidence. Product-intent GSC/source facts alone cannot produce a product
  offer; `missing_product_evidence` tells the operator to connect Merchant/shop
  proof or change CTA back to consultation.
- Draft Package tests are realigned with the Claim Ledger source-connector
  contract: allowed evidence-backed fixture claims now carry source connectors,
  so the focused draft/claim/structured-generation chain passes under the same
  no-source-no-recommendation rule.
- Structured draft generation now carries `knowledge_constraints` from Sales
  Brief into `contract.model_input` and shared schemas. The runtime receives
  typed evidence requirements, blocked/review-required claim constraints and
  card lineage as contract data, not only prose in the system instruction.
- Structured draft generation now blocks `full_draft` when Sales Brief still
  contains review-required, blocked, stale or measurement-blocked knowledge
  constraints. `section_draft` remains available for UAT/analysis, but a full
  production-depth draft must wait for reviewed knowledge and claim policy.
- Structured draft preview now blocks
  `missing_forbidden_claim_acknowledgement` when model output does not list all
  `claims_removed_or_blocked` from the generation contract in
  `forbidden_claims_avoided`. This prevents the runtime from silently ignoring
  forbidden/removed claims while still passing preview.
- Quality Review now mirrors that same forbidden-claim acknowledgement gate, so
  direct quality-review calls cannot bypass preview by omitting
  `forbidden_claims_avoided` for claims removed or blocked by the draft package.
- Draft Package now carries forbidden claims already recorded in Sales Brief
  into `claims_removed_or_blocked`, even when the active Claim Ledger is
  resolved enough to draft. Structured generation therefore receives the same
  avoided-claim list in `model_input` and the existing preview/quality gates
  still require `forbidden_claims_avoided` before human-review readiness.
- Structured draft generation now also exposes typed
  `removed_or_blocked_claim_markers` beside text-only
  `claims_removed_or_blocked`. Blocked or removed claims keep claim ID, type,
  status, evidence IDs, source connectors and reviewer lineage from Claim
  Ledger/Sales Brief, so avoided claims no longer reach runtime as plain
  strings only.
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
- Goal 005 UAT recorder now requires a plain Polish scorecard for every shown
  review artifact: decision plus 1-5 ratings for clarity, usefulness, Ekologus
  voice, blocker trust and CTA fit. This turns Wilku feedback into concrete
  product follow-up instead of only free-text notes.
- The same UAT recorder now extracts `review_follow_up_suggestions` from that
  scorecard. Any non-approved material or rating at 3/5 or below becomes a
  plain follow-up suggestion with the material path, decision, weak score and
  requested fix, so Wilku's review can feed the next product/code slice without
  manually rereading the whole report.
- Goal 005 completion guard now consumes those scorecard follow-ups. A valid
  UAT result with all boolean gates set to yes still cannot return
  `complete_with_uat` when Wilku's material scorecard contains non-approved
  decisions or weak ratings; it blocks as
  `goal_005_review_scorecard_follow_up` and renders the exact weak scores.
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
- Quality Review now enforces Sales Brief signal quality: `review_required`
  produces `needs_changes` with `sales_brief_signal_review_required`, while
  `thin` blocks with `sales_brief_signal_thin`. Live HTTP proof after stack
  restart on 2026-07-02 confirmed both states on
  `/api/content/work-items/quality-review`. Shared Zod schema now also accepts
  those finding codes plus existing backend code `required_claim_missing`, so
  the dashboard/API client boundary stays aligned with Quality Review.
- Goal 005 waste-storage knowledge slice `wilq-seo-nlz` added
  `ekologus_public_waste_packaging_obligations_2026_07_01` as a commit-safe
  source fact compiled into `ekologus_service_waste_packaging_obligations`
  (`source_backed_review_required`). Live proof after stack restart:
  `magazynowanie odpadów` builds a Sales Brief with no blockers and
  `draft_allowed=false`.
- Goal 005 water-permit knowledge slice `wilq-seo-d0m` added
  `ekologus_public_water_permit_documentation_2026_07_02` as a commit-safe
  public source fact compiled into
  `ekologus_service_operat_wodnoprawny`
  (`source_backed_review_required`). Live Service Profile proof after stack
  restart on 2026-07-02: `service_card_count=7`,
  `water_status=source_backed_review_required`, source connector
  `public_site`, 4 forbidden legal/guarantee claims and only
  `gap_no_approved_current_cards` remains. Sales Brief can analyze the topic
  with evidence but still keeps `draft_allowed=false`.
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
- Goal 005 completion evidence audit on 2026-07-02 is recorded in
  `docs/audits/005-2026-07-02-completion-evidence-audit.md`. Verdict: not
  complete. Live WILQ API is reachable, Service Profile is read-only and
  review-gated, `7` service sections are source-backed review-required, direct
  edit/promotion is blocked, and the content queue has `candidate_count=3` but
  only `actionable_candidate_count=1`, so `queue_status=blocked`. Remaining hard
  blockers are still Goal 005 Wilku UAT or explicit owner defer with residual
  risk, plus full `rtk scripts/verify.sh` before any completion claim.
- Service Profile now exposes all redacted `ekologus-ai` reviewed-internal
  private proposals from source facts, not only service-scope proposals. Live
  proof after stack restart on 2026-07-02 later advanced to `proposal_count=5`,
  `review_required_count=5`, scopes `claim_policy`, `service` and
  `evidence_requirement`, policy targets `ekologus_claim_policy_brand_voice`,
  `ekologus_claim_policy_legal_safety` and
  `ekologus_evidence_policy_source_trace`, dedicated review actions for those
  review targets, `promotion_ready=false`, `can_promote_facts=false` and
  `ready_for_daily_content=false`. This gives Wilku review targets for
  brand/legal-safety/source-trace rules without turning them into
  production-depth cards or automatic quality gates.
- Service Profile private proposal review recorder now requires the private
  governance checks exposed by the review actions:
  `data_classes_confirmed`, `source_block_refs_confirmed`,
  `freshness_status_confirmed`, `audience_scope_confirmed`,
  `retention_decision_confirmed`, `deletion_path_confirmed` and
  `eval_gates_confirmed`. Earlier live proof on 2026-07-02 accepted a real
  `service_profile_review_private_proposal_*` action with those booleans and
  still returned `promotion_allowed=false`.
- The `wilq-content-operator` UAT packet now exposes the same private
  governance fields in
  `review_result_recorders.private_review.minimal_payload_required_fields`.
  Live packet proof on 2026-07-02 later advanced to those fields with 5 private
  promotion preview rows and `apply_allowed=false`.
- Goal 005 UAT proof now separates private service proposals from private
  policy proposals. Live `wilq-content-operator` UAT packet on 2026-07-02 shows
  `public_service_review_count=6`, `private_review_count=5`,
  `private_service_review_count=2`, `private_policy_review_count=3`, policy
  targets `ekologus_claim_policy_brand_voice`,
  `ekologus_claim_policy_legal_safety` and
  `ekologus_evidence_policy_source_trace`, and `queue_status=blocked`.
  `scripts/record_goal_005_content_uat_result.py` now requires
  `private_policy_review_actions_czytelne` and records separate live provenance
  counts, so a future Wilku result cannot collapse service fit and brand/legal
  safety into one vague "private review" answer.
- Private `ekologus-ai` proposals now have the same prepare-only action surface
  as public service-card promotion review. Live proof after stack restart on
  2026-07-02: `/api/actions/act_prepare_service_profile_private_proposal_promotion`
  validates with `valid=true`, exposes `private_source_proposal_promotion_preview_v1`,
  `row_count=4`, scopes `claim_policy` and `service`, targets Eko-Opieka,
  Audyt zgodności, brand voice and legal safety, `preview_card_count=4`,
  `apply_allowed=false` and `api_mutation_ready=false`. This is still only
  review preparation; it does not edit `source_facts.json` or unlock
  production-depth.
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
- GSC vendor reads now also persist a separate Search Analytics aggregate
  without `query/page` dimensions (`aggregate_dimensions=country,device`,
  `aggregate_aggregation_type=byProperty`,
  `aggregate_data_completeness=aggregate_without_query_page_dimensions`).
  `/api/content/diagnostics` exposes those aggregate fields beside the partial
  detail contract, so skills can distinguish general traffic volume from
  query/page content opportunity rows. Live proof
  `refresh_google_search_console_a9578df29c2f` completed on 2026-07-02 with
  703 query/page rows, aggregate 18 clicks and 2755 impressions for
  2026-06-29.
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
