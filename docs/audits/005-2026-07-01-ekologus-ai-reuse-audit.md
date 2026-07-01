# Goal 005 `ekologus-ai` Reuse Audit

Date: 2026-07-01
Repo audited: `https://github.com/rekurencja/ekologus-ai`
Audited checkout: `/tmp/ekologus-ai-audit`
HEAD: `8ee3cb237306bd4e8bc6eba674fcb64a607379a6`
Beads task: `wilq-seo-5fd`

## Executive Readout

`ekologus-ai` is useful, but not as a product to revive. It is useful as a
source of proven contracts and Ekologus-specific reviewed content patterns.

The breakthrough pattern is:

```text
source manifest
-> approved/cleaned material
-> evidence pack
-> strategy brief
-> source claim markers
-> generation gate
-> prompt/provider input
-> quarantine
-> post-output validation
-> operator review
-> marketer usefulness report
```

WILQ already has the stronger product shell: API-first contracts, dashboard,
skills, ActionObjects, connector evidence and content workflow. `ekologus-ai`
has deeper content safety contracts. The right move is to port selected
contracts into WILQ API, not to run the old CLI beside WILQ.

## Repository Shape

Important directories:

- `src/ekologus_brain/content`: content planning, evidence pack, generation
  gate, prompt package, provider runner, quarantine, post-output validation,
  marketer reports and usefulness scoring.
- `src/ekologus_brain/guardian`: deterministic claim-risk rules and report.
- `src/ekologus_brain/strategy`: master strategy schema, retrieval, evidence
  hydration, validation and approval checks.
- `src/ekologus_brain/ingest`: manifest approval and markdown chunking.
- `src/ekologus_brain/rag`: Qdrant/embedding retrieval layer.
- `src/ekologus_brain/evals`: retrieval and Guardian behavior evals.
- `src/ekologus_brain/policy`: model-call, provider, data-egress, local runtime
  and operator approval contracts.
- `materials_clean/approved`: approved internal knowledge files.
- `master_strategy/master_strategy.yaml`: promoted strategy with evidence refs.
- `deliverables/`: historical demo/review packets.

## Most Valuable Patterns To Reuse

### 1. Evidence Pack

File: `src/ekologus_brain/content/evidence_pack.py`

Why it matters:

- Separates sources, claims, constraints, persona signals, objections, coverage
  and limitations.
- Forbids final copy fields inside evidence preparation.
- Tracks support status and generation allowance per claim.
- Forces limitations such as "does not prove legal correctness" and "does not
  replace operator review".

WILQ mapping:

- Use as design input for WILQ Claim Ledger and Sales Brief proof sections.
- Do not copy the old schema wholesale. WILQ already has source facts, evidence
  IDs, connectors and content work items; the WILQ version should reference
  those IDs directly.

### 2. Source Claim Markers

File: `src/ekologus_brain/content/source_claim_markers.py`

Why it matters:

- Converts evidence into allowed/required/forbidden claims.
- Has snippets, source classification, output requirements and validation flags.
- Blocks "approved for use", CMS and final-copy semantics from leaking into a
  provider input.

WILQ mapping:

- This is the clearest candidate for Goal 006.
- WILQ should expose a per-work-item claim ledger:
  `allowed_claims`, `weak_claims_requiring_review`,
  `forbidden_claims`, `required_evidence_mentions`, `blocked_claims`.
- Quality Review should fail when a draft uses a claim outside that ledger.

### 3. Generation Gate

File: `src/ekologus_brain/content/generation_gate.py`

Why it matters:

- Explicitly decides `allowed`, `blocked` or `needs_review`.
- Ties generation permission to evidence pack, strategy brief, identity match
  and source-bound claim counts.
- Forbids final copy and model-use flags in the gate artifact.

WILQ mapping:

- Add a WILQ content generation gate before structured draft runtime.
- Gate must block production-depth drafting when only review-required knowledge
  exists.
- Gate should name exact blocked/review reasons in Polish for Wilku.

### 4. Quarantine And Post-Output Validation

Files:

- `src/ekologus_brain/content/output_quarantine.py`
- `src/ekologus_brain/content/quarantine_store.py`
- `src/ekologus_brain/content/quarantined_candidate.py`
- `src/ekologus_brain/content/post_output_validation.py`

Why it matters:

- Treats model output as quarantined by default.
- Blocks CMS/final-copy/publication paths.
- Requires Guardian, completeness, traceability and operator review after
  output.

WILQ mapping:

- WILQ already has draft preview, quality review, human review and WordPress
  handoff. The missing part is stronger "output is quarantined until checks
  pass" semantics.
- Add tests proving structured draft output cannot be represented as publish
  ready or CMS write allowed.

### 5. Guardian Rules

Files:

- `src/ekologus_brain/guardian/rules.py`
- `src/ekologus_brain/guardian/validator.py`
- `src/ekologus_brain/evals/guardian_behavior.py`

Why it matters:

- Has concrete environmental/compliance copy risks: guarantees, legal
  interpretation, penalty/risk elimination, delay avoidance, frictionless
  process, time-bound events, absolute safety, tone anti-patterns.
- Has a reviewed behavior dataset/eval pattern.

WILQ mapping:

- Port the rule families into WILQ expert rules or content quality checks.
- Do not keep them only in Codex skill prompts.
- Use WILQ source facts/cards to decide whether a claim can be softened,
  review-required or blocked.

### 6. Strategy Schema And Evidence Hydration

Files:

- `src/ekologus_brain/strategy/schema.py`
- `src/ekologus_brain/strategy/builder.py`
- `src/ekologus_brain/strategy/approval.py`
- `master_strategy/master_strategy.yaml`

Why it matters:

- The old strategy model requires evidence per claim/USP/tone/pillar.
- Structured generation only returns evidence IDs; Python hydrates quotes/source
  details deterministically.
- Promotion requires explicit human approval.

WILQ mapping:

- Useful for evolving WILQ knowledge lifecycle:
  review-required -> approved-current.
- WILQ should preserve the "LLM returns IDs, code hydrates source details"
  pattern.
- This can prevent generated strategy/briefs from inventing source lineage.

### 7. Approved Marketing Corpus

File: `src/ekologus_brain/content/marketing_corpus.py`

Why it matters:

- Later `ekologus-ai` versions tried to turn approved source snippets, proof
  points, forbidden claims and provider eligibility into a corpus that can feed
  task-specific provider input.

WILQ mapping:

- Treat this as an input model for future WILQ "approved marketing corpus" only
  after source facts/cards and claim ledger are stable.
- Useful idea: provider eligibility should be explicit and false by default for
  protected or review-required material.

### 8. Marketer Usefulness Report

File: `src/ekologus_brain/content/marketer_usefulness.py`

Why it matters:

- Scores not only quality, but usefulness for a marketer: actionability,
  clarity, specificity, evidence application, rewrite depth, strategic value,
  channel fit, decision support, edit effort and missing context.

WILQ mapping:

- Use as inspiration for Wilku UAT rubric.
- Do not turn it into a fake score on the dashboard. Prefer dimensions and
  blockers over magic percentages.

## Materials Worth Using As Reviewed Internal Source Context

Most useful approved files:

- `materials_clean/approved/KB_INDEX.cleaned.md`
- `materials_clean/approved/02_PORTFEL_USLUG_I_MODELE_PRZYCHODU.cleaned.md`
- `materials_clean/approved/KB_001_EKO_OPIEKA.cleaned.md`
- `materials_clean/approved/KB_003_AUDYT_ZGODNOSCI.cleaned.md`
- `materials_clean/approved/KB_013_REGULY_ZRODEL_I_STATUSOW.cleaned.md`
- `materials_clean/approved/KB_014_STYL_MARKI_JEZYK_EKOLOGUS.cleaned.md`
- `materials_clean/approved/KB_021_BEZPIECZENSTWO_PRAWNE_POUFNOSC_ZGODY.cleaned.md`

Use them as `reviewed_internal` / `redacted_only` source facts unless a human
explicitly approves promotion in WILQ. They are useful for handoffs, UAT,
questions for Wilku and review-required draft direction. They should not unlock
production-depth readiness by themselves.

## What Not To Copy

- Do not revive the old CLI as the active product.
- Do not add Qdrant/vector DB to WILQ before source facts, freshness, claim
  ledger and evals are stable.
- Do not copy raw private/internal materials into committed WILQ files.
- Do not represent old approved `ekologus-ai` material as live connector
  evidence.
- Do not copy provider-runner/model-call layers directly; WILQ has its own API,
  skill and ActionObject safety model.
- Do not add a separate endpoint/dashboard module for the same knowledge unless
  Wilku UAT proves that existing content workflow artifacts are insufficient.
- Do not import the old WordPress staging client as a bypass around WILQ
  WordPress draft-only contracts.

## Mapping To WILQ Gaps

| WILQ gap | `ekologus-ai` pattern | Recommended action |
| --- | --- | --- |
| Claims in draft can outrun evidence | Source claim markers | Add WILQ Claim Ledger before draft runtime |
| Review-required knowledge can look too polished | Generation gate | Gate production-depth drafting by lifecycle status |
| Draft output can be mistaken for final copy | Quarantine/post-output validation | Mark all generated candidates as quarantined until quality/human review |
| Legal/offer claims need deterministic checks | Guardian rules/evals | Port rule families into WILQ quality review/expert rules |
| Strategy/source lineage can be invented by LLM | Evidence hydration | LLM returns IDs; WILQ hydrates source details |
| UAT needs usefulness rubric | Marketer usefulness report | Use dimensions in Wilku UAT, not a magic dashboard score |
| Knowledge promotion needs owner approval | Strategy approval | Add reviewed source-fact promotion path later |

## New Goal Candidate After This Audit

Recommended next goal after current Goal 005 slice:

```text
Goal 006 - WILQ Claim Ledger And Generation Gate

Implement a typed per-work-item Claim Ledger and Generation Gate in WILQ API,
inspired by ekologus-ai evidence packs/source claim markers/generation gates.
The gate must block unsupported claims, review-required knowledge misuse,
legal/offer/product/penalty claims without human review, and publish/CMS-ready
semantics before human review.
```

Acceptance shape:

- API contract exposes allowed, weak, forbidden and required claims.
- Structured draft runtime consumes the claim ledger.
- Quality Review blocks claims outside the ledger.
- Tests cover public source exists but review missing, seed-only card, broad
  overmatch, product CTA without Merchant evidence, legal/current-law claim
  without review and draft claim not present in ledger.

## Immediate Practical Use

Use `ekologus-ai` now for:

- source-fact expansion proposals,
- Wilku review handoffs,
- claim-policy extraction,
- Guardian rule extraction,
- UAT rubric,
- future Claim Ledger design.

Do not use it now for:

- live metrics,
- production-ready recommendations,
- automatic knowledge approval,
- WordPress writes,
- separate product UI.
