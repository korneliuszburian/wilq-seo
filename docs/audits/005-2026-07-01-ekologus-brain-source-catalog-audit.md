# Goal 005 Private `krn-ekologus-brain` Source Catalog Audit

Date: 2026-07-01
Local source catalog: `/home/krn/coding/krn/active/krn-ekologus-brain`
HEAD: `69028ba feat(decision-compliance): support multipack coverage audit`
Git state during audit: clean, `main...origin/main [ahead 2]`
Beads task: `wilq-seo-409`

## Scope

This audit evaluates whether the private `krn-ekologus-brain` project can help
Goal 005 without turning WILQ into a second RAG demo or importing private
materials into this repository.

Inspected safely:

- top-level project docs: `README.md`, `GOAL.md`, `PLAN.md`, `AGENTS.md`;
- knowledge curation contracts under `ops/eco-intelligence-knowledge-curation/`;
- Decision Compliance product docs under `ops/decision-compliance-goals/`;
- source-code names and selected schema/gate modules in
  `apps/decision-compliance/backend/decision_compliance/`;
- directory/file inventories at shallow depth.

Not inspected or imported:

- `creds/`;
- raw client documents, attachments, spreadsheets, PDFs, emails or mount
  contents;
- generated private XLSX/JSON outputs with raw client values;
- full private source paths or filenames.

## Executive Readout

`krn-ekologus-brain` is useful for WILQ, but not as a source to connect
automatically. It contains two mature patterns WILQ should absorb:

```text
metadata-only source intake
-> owner/risk/audience decision
-> local extraction or no extraction
-> schema-gated condensation
-> owner review
-> import proof / eval / feedback
```

and:

```text
input registry + evidence pack + legal matrix
-> row-by-row evidence accounting
-> explicit unsupported/review statuses
-> expert review XLSX
```

For WILQ content work, the breakthrough is not "use all materials". The
breakthrough is a governed private-source path that can eventually produce
local-only or redacted source facts with lineage, freshness, risk, audience,
review status and deletion/retention rules.

## Reusable Patterns

### 1. Metadata-Only Intake Before Content Reading

The knowledge curation goal explicitly separates source discovery from content
reading. Allowed discovery is limited to source IDs, counts, extensions, risk
tier, owner decisions and coarse metadata. Raw text, full paths, file names and
private snippets stay out of repo artifacts.

WILQ mapping:

- Add a private source catalog/import protocol before any private source fact
  compiler.
- The first WILQ step should be a local-only metadata inventory, not a RAG
  index or committed source-fact dump.
- Source facts derived from this catalog should default to
  `privacy_class=redacted_only`, `source_type=private_candidate` and
  `review_status=review_required`.

### 2. Owner, Audience And Risk As Required Fields

`source-categories.json` models source posture with `source_id`, domain,
target KB, risk tier, batch strategy and shared-KB posture. It also sets
defaults that disallow source content reading, source-folder modification,
external AI and repo storage of condensed real content.

WILQ mapping:

- Extend the private source-fact proposal shape with owner/audience/risk fields
  before allowing facts to influence Service Profile or drafts.
- Do not merge company-wide, domain-specific, legal and client/project sources
  into one content knowledge layer.
- Legal/expert opinions and client/project materials should stay blocked from
  shared marketing knowledge unless a separate owner/IOD path exists.

### 3. Schema-Gated Condensation

The condensed-document schema is strict: explicit status enum, risk tier,
audience, data classes, owner review, retention, deletion path, source refs and
booleans proving no source paths/raw excerpts were emitted.

WILQ mapping:

- Private source condensation should be a typed local artifact, not free-form
  notes.
- A WILQ private source proposal should include:
  `source_id`, `source_block_id`, `support_level`, `data_classes`,
  `audience`, `risk_tier`, `freshness`, `owner_review`, `retention`,
  `deletion_path`, `blocked_claims`.
- No condensed private source should unlock `approved_current` until reviewed
  inside WILQ.

### 4. Evidence-First Row Accounting

Decision Compliance defines useful statuses such as `supported`,
`weak_support`, `missing_evidence`, `legal_review_required`, `out_of_scope` and
`needs_source`. Its `RuleUnit` schema blocks confirmed/reviewed output without
evidence and prevents confirmed dates/deadlines without specific sources.

WILQ mapping:

- Claim Ledger should use the same mindset: every claim is allowed, weak,
  forbidden, missing evidence or human-review required.
- Draft quality review should fail if a draft uses a claim outside the ledger
  or if legal/current-law/product/penalty language appears without review.
- Measurement, freshness and legal status should remain separate fields, not
  prose hidden inside a brief.

### 5. Eval Gate Before Expansion

The curation flow has golden questions, validate scripts and feedback summaries
before a knowledge batch expands. Decision Compliance has retrieval eval,
label gate and benchmark tests.

WILQ mapping:

- Non-interactive Codex skill evals should be paired with domain eval cases:
  source trace, forbidden claim, stale source, unsupported service match and
  operator usefulness.
- Adding private source facts should require at least one deterministic eval
  proving they do not unlock production-depth readiness prematurely.

## Concrete Source Areas That May Help Later

These are not imports. They are candidate source classes for a later private,
local-only proposal flow:

- onboarding/shared internal guidance;
- internal training materials;
- Eko-technologie domain knowledge;
- IKZ instructions and patterns;
- Sorbenty domain knowledge;
- ZBIE domain knowledge;
- approved/reviewed legal or expert material only in a separate restricted
  legal stream.

For WILQ marketing content, the safest first private-source use is not
client-case compliance. It is sanitized service profile enrichment:

- what Ekologus actually offers;
- how services are packaged;
- safe CTA wording;
- brand/tone rules;
- forbidden legal/guarantee claims;
- questions Wilku should answer before publication.

## Strict Exclusions

Do not use `krn-ekologus-brain` to:

- auto-connect private folders to WILQ;
- commit raw private facts, file names, full paths, emails, phone numbers,
  attachments, client spreadsheets, decisions or PDFs;
- treat local Open WebUI/RAG as WILQ's product brain;
- let private review-required material unlock daily-content readiness;
- use legal/expert opinions as public marketing claims;
- bypass WILQ evidence IDs, source connectors, ActionObjects or audit paths;
- run external AI on protected data without a separate owner/IOD decision.

## Recommended WILQ Import Protocol

Future slice, not implemented in this audit:

```text
1. Local private source catalog metadata inventory
2. Source owner/audience/risk decision
3. Local-only extraction for approved candidates
4. Schema-gated condensation into private source proposals
5. WILQ review screen or markdown handoff for Wilku/owner
6. Promotion to reviewed source facts only after approval
7. Compilation into cards only when lifecycle permits it
8. Eval proving no unsupported production-depth unlock
```

Initial target should be read-only Service Profile enrichment, not draft
generation.

Tracked follow-up: `wilq-seo-wtf` - Design private source proposal protocol for
WILQ.

## Impact On Goal 005

This audit upgrades the `krn-ekologus-brain` finding from vague "maybe useful
materials" to a concrete guarded source-catalog pattern:

- private source facts are possible, but only as reviewed/redacted proposals;
- WILQ should continue to use public source facts for commit-safe service
  expansion;
- private source context can help Wilku-facing handoffs and UAT questions now;
- production-depth cards still require WILQ review and typed lifecycle status;
- the next best development slice is a read-only Service Profile/review surface
  or a private source proposal schema, not an endpoint for special "packs".
