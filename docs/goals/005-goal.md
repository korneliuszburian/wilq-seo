# Goal 005 - Ekologus Knowledge Depth And UAT Closure

Status: active.

Beads epic: `wilq-seo-1oa`.

Date: 2026-07-01

## Objective

Validate that the Goal 004 content operations loop is useful for Wilku with
real Ekologus knowledge, not only mechanically complete.

Goal 005 must deepen or truthfully block typed Ekologus knowledge, expose a
read-only Service Profile/review path, run or explicitly defer the first real
Wilku UAT, and audit whether Sales Brief v2 signals are strong enough to avoid
generic SEO content.

## Baseline

Goal 004 is complete and verified. It proves:

- content queue,
- opportunity enrichment,
- typed knowledge cards,
- Sales Brief v2,
- claim-gated draft variants,
- deterministic quality review,
- bounded revision,
- human review and audit,
- WordPress draft-only handoff,
- measurement window and conservative outcome interpreter,
- `wilq-content-operator` skill and UAT harness.

The remaining gap is product usefulness. Current knowledge-card implementation
contains three seeded cards:

- `ekologus_service_environmental_compliance`
- `ekologus_cta_consultation_without_guarantee`
- `ekologus_evidence_live_connector_requirement`

These prove the contract, not deep Ekologus coverage.

First Goal 005 source-pack proof:

- `docs/audits/005-2026-07-01-knowledge-depth-audit.md` classifies the current
  cards as typed seeds/thin production coverage.
- `docs/audits/005-2026-07-01-ekologus-source-pack.md` collects public
  `ekologus.pl` source candidates for environmental consulting/outsourcing,
  BDO/reporting, waste/packaging, training, remediation/monitoring, sorbent
  product content and Zielony Lad education. These are source inputs for
  reviewed cards, not automatic approval for production-depth claims.
- Content knowledge-card responses now expose `production_depth_readiness`.
  Seeded Goal 004 cards are explicitly `seeded_contract_proof` and
  `ready_for_daily_content=false`; public source-backed cards remain review
  required until owner/Wilku approval.
- Public source facts are now data-driven in
  `wilq/content/knowledge/source_facts.json` and validated by
  `wilq/content/knowledge/source_facts.py`. `cards.py` compiles commit-safe
  public facts into review-required cards with `source_fact_ids`,
  `source_connectors`, lifecycle status, blocked claims and human-review gates.
  This removes hardcoded public-service expansion from `cards.py`, but does not
  make those cards production-depth or replace live evidence IDs/source
  connectors.
- `ekologus-ai` can be used as a reviewed internal knowledge source for WILQ
  content work, especially `materials_clean/approved` and
  `master_strategy/master_strategy.yaml`. Use it to generate normal artifacts
  for Wilku/owner review: briefs, draft content, current-state summaries,
  questions and handoff markdowns. Do not create a special API/UI product layer
  for “packets” unless an artifact/UAT proves that the workflow needs it.
  Redacted review-required facts may support analysis and drafting, but they do
  not unlock production-depth readiness until reviewed in WILQ.
- `docs/roadmap/bdos-class-wilq-master-roadmap.md` records the current
  BDOS-class WILQ roadmap and estimates overall maturity at `35-45%`.
- `docs/audits/005-2026-07-01-ekologus-ai-reuse-audit.md` records the public
  `ekologus-ai` reuse audit. The strongest reusable contracts are evidence
  pack, source claim markers, generation gate, output quarantine,
  post-output validation, Guardian rules, strategy evidence hydration and
  marketer usefulness rubric. These should feed WILQ API/schema work, not a
  second product brain.
- `docs/audits/005-2026-07-01-sales-brief-signal-quality.md` records the Sales
  Brief v2 signal-quality audit. It identifies `bdo co to` as the safest first
  Wilku UAT candidate, `zielony ład co to` as a service-fit review question,
  `magazynowanie odpadów` as now supported by source-backed review-required
  waste/packaging knowledge, `operat wodnoprawny` as still blocked by missing
  direct service knowledge, and the Ahrefs `beczki` candidate as correctly
  blocked with a typed `blocked_snapshot` instead of HTTP 404. The audit also
  fixed source-fact connector/evidence lineage for enrichment facts.
- `docs/audits/005-2026-07-01-ekologus-brain-source-catalog-audit.md` records
  the private `krn-ekologus-brain` source-catalog audit. The useful part is not
  an automatic bridge or raw material import; it is a governed private-source
  protocol: metadata-only intake, owner/audience/risk, schema-gated
  condensation, owner review, import proof and eval. Any future facts from this
  catalog start as local-only/redacted `review_required` proposals and do not
  unlock `approved_current` cards or production-depth readiness without WILQ
  review.
- `docs/architecture/private-source-proposal-protocol.md` defines the WILQ
  private source proposal design. It reuses existing source-fact concepts
  (`private_candidate`, `reviewed_internal`, `private_local`, `redacted_only`,
  `review_required`, `approved`) and adds a fail-closed review protocol before
  any private proposal can become a reviewed source fact or appear in a
  read-only Service Profile.

## Non-Negotiable Rules

- WILQ API owns product logic.
- Dashboard renders API-owned view models.
- Codex skills consume WILQ API and do not become the writer.
- Typed knowledge cards do not replace live evidence/source connectors.
- No evidence ID means no recommendation.
- No source connector means no recommendation.
- Thin/stale evidence must be surfaced as a blocker or low-confidence state,
  not hidden behind polished copy.
- Knowledge-card updates require review/audit before they can affect content
  production.
- Initial Service Profile work is read-only plus flag/review request, not
  ungated self-service edits.
- No broad RAG/vector DB before typed cards, lineage, freshness, validators and
  evals are solid.
- No fake SEO score or magic content score.
- WordPress remains draft-only and review-gated.
- No success/failure claim before measurement readiness.

## In Scope

1. Audit knowledge-card depth against real Ekologus services, buyer problems,
   triggers, CTA patterns, claim constraints and evidence requirements.
2. Identify exact missing cards or stale/thin card areas.
3. Add or plan focused blockers/tests so missing required knowledge stops Sales
   Brief and draft work.
4. Design or implement a read-only Service Profile/review surface for Wilku.
5. Audit Sales Brief v2 signal quality across queue candidates and enrichment
   source facts.
6. Define evidence-based draft variant comparison without fake scores.
7. Run one real Wilku content UAT session or record explicit owner defer with
   residual risk.

## Out Of Scope

- automatic WordPress publish,
- destructive content updates,
- mass content generation,
- direct Codex-authored production drafts,
- direct OpenAI or WordPress calls outside WILQ API,
- broad RAG/vector memory,
- social publishing,
- multi-client SaaS,
- Ads/Merchant/Localo write automation,
- outcome claims before measurement readiness.

## Completion Definition

Goal 005 is complete only when:

1. Knowledge-card coverage is audited and classified as production-depth, thin,
   stale, blocked or placeholder-like.
2. Missing real Ekologus services/claims/triggers/CTA/evidence requirements are
   named with exact next actions.
3. Missing required knowledge produces typed blockers or a documented blocker
   explains why implementation needs owner/source input.
4. Service Profile read/review path is designed or implemented with no direct
   ungated card editing.
5. Sales Brief v2 signal quality is audited for current queue candidates and
   weak signal causes are assigned to connector freshness, sparse data or model
   interpretation.
6. Draft variant selection has evidence-based comparison rules and no fake
   score.
7. Real Wilku UAT is completed within 45 minutes or explicitly deferred by the
   owner with residual risk.
8. UAT proof records selected work item, time, blockers, confusion points,
   off-brand/generic SEO findings, source-trace questions and follow-ups.
9. `PLANS.md`, `docs/PROGRESS.md`, this file and Beads agree.
10. Focused checks pass for changed areas and full `rtk scripts/verify.sh`
    passes before completion.

## Verification

Docs-only slices:

```bash
rtk git diff --check
```

Content domain changes:

```bash
rtk uv run pytest tests/content -q
```

Dashboard changes:

```bash
rtk pnpm --filter @wilq/dashboard test
rtk pnpm --filter @wilq/dashboard typecheck
```

Broad completion gate:

```bash
rtk scripts/verify.sh
```

## Beads Recovery Index

Active Goal 005 epic:

- `wilq-seo-1oa` - Goal 005: Ekologus Knowledge Depth & UAT Closure.

Initial slices:

- `wilq-seo-9do` - recovery and plan alignment.
- `wilq-seo-3lk` - audit Ekologus knowledge-card depth.
- `wilq-seo-ciz` - collect source-backed Ekologus service and claim source
  pack.
- `wilq-seo-lt1` - expand typed Ekologus knowledge cards from reviewed sources.
- `wilq-seo-t13` - add knowledge-card production-depth guard tests.
- `wilq-seo-409` - evaluate private Ekologus Brain source catalog relevance
  without automatic integration.
- `wilq-seo-94k` - design read-only Ekologus Service Profile review surface.
- `wilq-seo-jst` - run first real Wilku content UAT or record explicit defer.
- `wilq-seo-n8r` - audit Sales Brief v2 signal quality.
- `wilq-seo-87i` - define evidence-based draft variant selection guard.

Use `bd ready --json` for operational status. Do not duplicate Beads tasks as
markdown TODOs.

## Stop Conditions

Stop and record a blocker if:

- cards are mostly seed/placeholder coverage and no trusted Ekologus source is
  available,
- Wilku cannot complete one content session within 45 minutes without developer
  intervention,
- variants sound like generic SEO despite formal gates,
- WordPress draft-only handoff times out or needs debugging during UAT,
- Wilku cannot trace a claim or recommendation back to a concrete source fact,
- a proposed knowledge endpoint allows ungated card edits,
- live Structured Outputs is enabled without a separate adapter-boundary audit.
