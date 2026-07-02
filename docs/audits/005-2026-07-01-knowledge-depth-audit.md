# Goal 005 Knowledge-Card Depth Audit - 2026-07-01

## Verdict

Current content knowledge cards are good enough as a Goal 004 contract proof, but
not deep enough to claim production-grade Ekologus content knowledge.

The system has typed cards, source lineage fields, confidence, freshness and
blockers. It does not yet have source-backed coverage of real Ekologus service
profiles, buyer triggers, CTA variants, claim policy by service or freshness
review. A real Wilku UAT can test workflow usability, but it must not be framed
as proof that WILQ already knows Ekologus deeply.

## Evidence Inspected

- `wilq/content/knowledge/cards.py`
- `wilq/content/briefs/sales.py`
- `wilq/content/enrichment/opportunity.py`
- `tests/content/test_content_knowledge_cards.py`
- `docs/goals/archive/005-goal.md`
- `PLANS.md`
- `docs/PROGRESS.md`
- `docs/handoffs/2026-06-29-marketer-uat-ready.md`

WILQ API was not used for live marketing metrics in this audit because the
current runtime notice says WILQ API is unreachable.

## Current Card Inventory

Current function: `ekologus_content_knowledge_cards()`.

Card count: 3.

Cards:

- `ekologus_service_environmental_compliance`
  - Type: `service`
  - Coverage: broad environmental compliance card.
  - Terms: BDO, odpady, środowisk, obowiązki, zgodność, Zielony Ład,
    sprawozdawczość.
  - Claim rules: environmental and legal claims need human review, guarantee
    claims are blocked, business outcome claims wait for measurement.
  - Source lineage: internal docs/code only.
  - Freshness: `seeded_goal_004`.

- `ekologus_cta_consultation_without_guarantee`
  - Type: `cta_pattern`
  - Coverage: generic consultation CTA without outcome guarantees.
  - Source lineage: internal Goal 004 docs and quality review code.
  - Freshness: `seeded_goal_004`.

- `ekologus_evidence_live_connector_requirement`
  - Type: `evidence_requirement`
  - Coverage: hard anti-slop rule that knowledge cards do not replace evidence
    IDs/source connectors.
  - Source lineage: `AGENTS.md`, Goal 004 docs and enrichment code.
  - Freshness: `seeded_goal_004`.

## Coverage Classification

| Area | Status | Reason |
| --- | --- | --- |
| Typed schema and strict fields | Good | Pydantic models use `extra="forbid"` and cards expose lineage, confidence and freshness. |
| Service coverage | Thin | One broad service card covers BDO, waste, Zielony Ład and environmental compliance together. |
| Buyer problems | Thin | Buyer problem terms exist inside the service card, but there are no standalone buyer-problem cards. |
| Buyer triggers | Thin | Triggers are generic and embedded in the broad service card. |
| CTA patterns | Thin | One defensive consultation CTA exists; no service-specific CTA matrix exists. |
| Claim policy | Partial | Claim rules exist, but there is no standalone claim-policy card by service/risk class. |
| Evidence requirements | Partial | The global evidence requirement is strong, but there are no source-specific evidence requirements by service/use case. |
| Source lineage | Weak | Current lineage is internal docs/code, not reviewed Ekologus service source material. |
| Freshness | Weak | All cards are `seeded_goal_004`, not reviewed/current source-backed cards. |
| Matching logic | Risky | Matching uses broad substring terms against topic/URL/evidence/source connector text. It can overmatch broad environmental topics. |

## Existing Guards

Current tests prove:

- cards are typed and seeded,
- response exposes lineage,
- BDO work item matches service, CTA, claim and evidence cards,
- unknown topic blocks service and CTA cards,
- the API endpoint exposes typed cards.

These tests are useful, but they mostly prove shape and basic blockers. They do
not prove deep Ekologus coverage.

## Gaps

### Service Cards

Needed source-backed cards:

- BDO obligations and consultation scope.
- Waste obligations / records / reporting.
- Environmental compliance audit or ongoing environmental support.
- Zielony Ład / regulatory-impact content only if source material confirms it is
  a real Ekologus service/topic.
- Product/shop-related content only if `sklep.ekologus.pl` evidence requires it.

Do not add these from memory. Each card needs source lineage and review status.

### Buyer Problems And Triggers

Needed cards:

- deadline/reporting anxiety,
- control/audit risk,
- uncertainty whether a company is subject to BDO or waste obligations,
- document preparation before consultation,
- regulatory change interpretation.

Each trigger must map to a service card and safe CTA.

### CTA Patterns

Needed cards:

- consultation of obligations,
- document review/preparation,
- compliance check request,
- service inquiry for ongoing environmental support,
- product/shop CTA only when product evidence exists.

Every CTA card must explicitly block guarantees of avoiding penalties, ranking
growth, lead growth or legal certainty.

### Claim Policy

Needed cards:

- legal/compliance claim policy,
- environmental claim policy,
- risk/penalty claim policy,
- SEO/performance/business outcome claim policy,
- pricing/product/availability claim policy if Merchant/shop content enters the
  workflow.

Current generic rules are correct but not specific enough for production-depth
briefing.

### Evidence Requirements

Needed cards:

- GSC query/page evidence requirements for refresh/create decisions,
- WordPress inventory requirements for preserve-first decisions,
- GA4 behavior requirements for engagement/CTA interpretation,
- Ahrefs gap requirements for competitor/gap claims,
- Merchant/shop evidence requirements if product content is used,
- Localo evidence requirements if local-intent content is used.

## UAT Implication

UAT may proceed only as a controlled workflow/usability session. It should not
be framed as proof that WILQ has complete Ekologus knowledge.

During UAT, explicitly ask Wilku:

- Czy ta karta usługi brzmi jak realny Ekologus?
- Czy problem kupującego jest trafny?
- Czy CTA pasuje do tego, co Ekologus faktycznie chce robić?
- Czy któryś claim brzmi zbyt prawnie, zbyt obiecująco albo zbyt generycznie?
- Czy w UI widać, skąd WILQ wziął dany fakt?

If Wilku says the card/brief sounds generic or off-brand, do not fix it with a
prompt. Add or correct typed cards with reviewed source lineage.

## Stop-Condition Result

The "<80% placeholder" stop condition is partially triggered for production
knowledge depth:

- The cards are not fake data.
- They are intentionally seeded and typed.
- They are too broad and internally sourced for production-depth Ekologus
  knowledge.

Result: do not claim daily content usefulness. Continue with source-backed card
expansion and/or controlled UAT with this risk stated.

## Exact Next Work

1. Collect a source-backed Ekologus service/claim source pack.
2. Add reviewed service cards for BDO, waste obligations and environmental
   support only where source material confirms scope.
3. Add service-specific CTA, buyer-problem and buyer-trigger cards.
4. Add service-specific claim-policy and evidence-requirement cards.
5. Add tests that reject production-depth status when cards have only
   `seeded_goal_004` freshness or internal-only lineage.
6. Keep `wilq-seo-jst` UAT controlled: it validates workflow and identifies
   knowledge gaps, not final content-readiness.

## Verification

Docs-only audit verification:

```bash
rtk git diff --check
```

Existing focused guard surface:

```bash
rtk uv run pytest tests/content/test_content_knowledge_cards.py -q
```

Run the focused guard when implementation changes knowledge cards. This audit
itself is docs-only.
