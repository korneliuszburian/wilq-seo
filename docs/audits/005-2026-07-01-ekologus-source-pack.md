# Goal 005 Ekologus Source Pack - 2026-07-01

## Verdict

Public, commit-safe Ekologus source material exists for the next knowledge-card
slice. It is enough to stop treating BDO, waste/reporting, environmental
consulting, training, remediation/monitoring and sorbent/product topics as
memory-derived guesses.

It is not enough to mark production-depth knowledge as done. Public website
copy must be converted into typed cards only with conservative claim policy and
owner/Wilku review, because several topics involve legal, environmental,
deadline, penalty or product-availability claims.

## Scope

This pack collects source-backed candidates for Goal 005 knowledge-card
expansion. It does not change product behavior, add cards, generate drafts or
claim that WILQ fully understands Ekologus.

WILQ API was not used for live metrics in this slice. The current task was
source collection and classification.

## Source Classes

### Commit-Safe Public Sources

These sources are public Ekologus pages and can be referenced from committed
docs and future source lineage:

| Source | URL | Safe Use |
| --- | --- | --- |
| Ekologus home page | `https://www.ekologus.pl/` | High-level service taxonomy: environmental documentation/expertise, outsourcing, reporting, consulting, eco-reviews, measurements, remediation, emergency kits/sorbents and training. |
| Doradztwo środowiskowe i EKO-consulting | `https://www.ekologus.pl/oferta/doradztwo-i-outsourcing-ekologiczny/` | Source for outsourcing/ecological consulting, BDO/KOBIZE/environmental-fee reporting, waste and packaging obligations and formal documentation support. |
| BDO FAQ article | `https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/` | Educational source for BDO topics and typical obligation questions. Do not use for final legal determination without review. |
| EKO checklist article | `https://www.ekologus.pl/eko-check-lista-na-koniec-2023/` | Source for environmental reporting, KOBIZE and BDO evidence requirements. Dated content; do not copy deadlines/rates into current cards without fresher review. |
| BDO/KOBIZE training page | `https://www.ekologus.pl/szkolenie/warsztaty-oplaty-srodowiskowe-kobize-i-bdo/` | Source for training/workshop audience, topics and practical learning outcomes around BDO, KOBIZE, emissions and fees. Training dates are not stable content evidence. |
| Training offer page | `https://www.ekologus.pl/oferta/szkolenia/` | Source for broad environmental training areas: air, permits, emissions, waste and packaging, water/sewage, investment processes, soil/water environment, KOBIZE, fees, reporting, REACH/CLP, management systems and BHP. |
| Zielony Ład article | `https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/` | Source that Zielony Ład is a real Ekologus knowledge-base topic. Treat as educational/regulatory context, not as proof of a service package without owner review. |
| Remediation offer page | `https://www.ekologus.pl/oferta/rekultywacje-i-remediacje/` | Source for remediation/rekultywacja, soil/groundwater sampling, accredited lab analysis and remediation plans. |
| Radon article | `https://www.ekologus.pl/badania-obecnosci-radonu/` | Source for radon educational topic. Needs owner review before becoming a core service card. |
| Sorbent article | `https://www.ekologus.pl/sorbenty-czym-sa-jak-dzialaja-i-dlaczego-warto-je-stosowac/` | Source for sorbent education/product-intent topics. Requires Merchant/shop evidence before product availability or purchase recommendations. |

### Internal WILQ Sources

These are useful for product behavior and anti-slop rules, but they are not
Ekologus service truth:

- `wilq/content/knowledge/cards.py`
- `wilq/actions/content_refresh.py`
- `docs/audits/005-2026-07-01-knowledge-depth-audit.md`
- Goal 004 and Goal 005 docs

Use them to preserve gates and language constraints. Do not use them as the
only source lineage for production-depth service cards.

### Private Or Local Sources

Repo-local `.env`, `.local-lab/`, access-pack files and live connector payloads
are not commit-safe source material. They may support private proof or UAT
packets, but committed cards must store only sanitized source lineage, evidence
IDs and review metadata.

The owner also noted that a separate local project, `krn-ekologus-brain`, and
internal Ekologus shared-drive knowledge bases exist for decision-compliance,
historical documentation, obligations, schedules, expert-legal opinions,
sorbents and onboarding. Treat this as a potential private source catalog, not
as WILQ SEO input by default. Do not copy customer documents, attachments,
emails, phone numbers, private paths or unreviewed client examples into
`wilq-seo`. Future use requires a separate sanitized review path and explicit
Goal 005 promotion.

This slice did not inspect or commit private credential/source contents, client
attachments or customer documents.

## Source-Backed Card Candidates

### 1. Environmental Consulting And Outsourcing

Candidate card:

- `ekologus_service_environmental_consulting_outsourcing`

Source-backed scope:

- ongoing environmental consulting/outsourcing,
- support for environmental documentation and formal obligations,
- BDO/KOBIZE/environmental-fee reporting,
- waste and packaging obligations,
- technical/legal environmental consulting.

Claim policy:

- Allowed after source review: Ekologus offers consulting/outsourcing and helps
  with documentation/reporting areas named on public pages.
- Needs human review: legal obligation interpretation, exact compliance status,
  deadline/rate/current-law statements.
- Blocked: guarantees of avoiding penalties, complete legal certainty,
  regulatory compliance or business outcome.

CTA candidates:

- "Skonsultuj obowiązki środowiskowe dla swojej firmy."
- "Przygotuj dokumenty do sprawdzenia przez eksperta."

### 2. BDO And Environmental Reporting

Candidate cards:

- `ekologus_service_bdo_reporting`
- `ekologus_evidence_bdo_reporting_requirements`

Source-backed scope:

- BDO registration/records/reporting education,
- waste and packaging reporting,
- KOBIZE and environmental-fee reporting,
- annual reporting preparation and documentation review.

Claim policy:

- Allowed after review: educational description of what to check before BDO or
  reporting work.
- Needs human review: who exactly is obligated, current reporting deadline,
  penalty risk, legal interpretation for a specific company.
- Blocked: "na pewno musisz", "unikniesz kary", "gwarantujemy zgodność".

Evidence requirements:

- public Ekologus source URL,
- WordPress inventory/canonical source,
- GSC query/page evidence for content demand,
- owner/legal review for current-law phrasing.

### 3. Waste And Packaging Obligations

Candidate cards:

- `ekologus_service_waste_packaging_obligations`
- `ekologus_buyer_problem_waste_records_uncertainty`

Source-backed scope:

- waste records,
- packaging and packaging-waste obligations,
- BDO cards/records/reporting,
- document preparation and supervision.

Claim policy:

- Allowed after review: waste/packaging obligations are an Ekologus support
  area.
- Needs human review: exact obligation by company type, waste code decisions,
  penalty/current-law statements.
- Blocked: guarantee that a specific company has no risk or all records are
  correct.

### 4. Environmental Training

Candidate cards:

- `ekologus_service_environmental_training`
- `ekologus_cta_training_signup_or_inquiry`

Source-backed scope:

- training in air, permits/emissions, waste and packaging, water/sewage,
  investment processes, soil/water environment, KOBIZE, fees, reporting,
  REACH/CLP, management systems and BHP,
- BDO/KOBIZE/environmental-fee workshops.

Claim policy:

- Allowed after source review: training topic and audience descriptions.
- Needs human review: current dates, prices, availability, certificates and
  exact programme details.
- Blocked: claiming a person becomes legally safe or guaranteed compliant after
  training.

### 5. Remediation, Monitoring And Environmental Measurements

Candidate cards:

- `ekologus_service_remediation_monitoring`
- `ekologus_buyer_problem_soil_water_risk`

Source-backed scope:

- remediation/rekultywacja,
- soil/groundwater sampling and lab analysis,
- remediation plans,
- monitoring/environmental measurements,
- radon topic as educational/source candidate pending owner review.

Claim policy:

- Allowed after review: Ekologus offers remediation and monitoring-related
  services named on public pages.
- Needs human review: method selection, accredited scope, exact legal
  requirement, technical feasibility and project outcome.
- Blocked: guaranteed cleanup result, guaranteed authority decision or
  guaranteed safety conclusion.

### 6. Sorbents, Emergency Kits And Product/Shop Content

Candidate cards:

- `ekologus_service_sorbents_emergency_kits`
- `ekologus_evidence_product_shop_requirements`

Source-backed scope:

- emergency kits and technical products for securing and removing oil,
  petroleum-product and chemical leaks,
- sorbent education by use case.

Claim policy:

- Allowed after review: educational explanation of sorbent types and typical
  use cases.
- Needs human review: product availability, price, stock, exact compatibility,
  safety claims.
- Blocked: product recommendation without Merchant/shop evidence or claim that a
  product guarantees compliance/safety.

Evidence requirements:

- public source URL,
- Merchant/shop connector evidence for product claims,
- WordPress inventory/canonical source,
- human review for safety/technical compatibility.

### 7. Zielony Ład And Regulatory Education

Candidate cards:

- `ekologus_topic_green_deal_regulatory_education`
- `ekologus_claim_policy_regulatory_education`

Source-backed scope:

- Zielony Ład is present in Ekologus knowledge-base/webinar content,
- useful as regulatory education and buyer-problem context.

Claim policy:

- Allowed after review: educational explanation and "what to check" framing.
- Needs human review: company-specific consequences, current grant/funding
  availability, legal obligations, financial impact.
- Blocked: promise of funding, revenue, compliance or regulatory outcome.

Do not treat Zielony Ład as a service card unless owner review confirms the
commercial offer it should map to.

## Cross-Cutting Claim Rules

Future cards should carry these rules explicitly:

- Legal, environmental and risk/penalty claims require human review.
- Current-law deadlines, rates, forms and authority procedures require fresh
  source review.
- Product/availability/pricing claims require Merchant/shop source evidence.
- SEO, lead, conversion and business-outcome claims require measurement window
  readiness and remain blocked for normal knowledge cards.
- Do not copy strong public-site marketing wording as a WILQ guarantee. WILQ
  should phrase it as a source-backed capability plus review constraint.

## Source-Pack Coverage Result

| Area | Result |
| --- | --- |
| BDO/reporting | Source-backed candidate exists. |
| Waste/packaging | Source-backed candidate exists. |
| Environmental consulting/outsourcing | Source-backed candidate exists. |
| Training | Source-backed candidate exists. |
| Remediation/monitoring | Source-backed candidate exists. |
| Sorbents/product/shop | Source-backed candidate exists, but product claims need Merchant/shop evidence. |
| Zielony Ład | Source-backed topic exists, but service mapping needs owner review. |
| Allowed/blocked claims | Cross-cutting rules can be seeded conservatively; service-specific claim approval still needs owner review. |
| CTA preferences | Candidate CTA patterns exist; final CTA wording needs Wilku review. |

## Implementation Guidance For `wilq-seo-lt1`

The next code slice may add typed cards from this pack only if each card:

- stores public source URLs in `source_lineage`,
- uses freshness such as `public_site_review_required_2026-07-01` or a later
  reviewed status,
- keeps legal/environmental/risk/product claims behind review gates,
- does not grant production-depth status by default,
- does not replace live evidence IDs/source connectors,
- does not add RAG/vector memory,
- adds tests proving missing service/claim/evidence cards still block Sales
  Brief/draft work.

If owner review is unavailable, cards may be added only as low-confidence or
review-required source-backed cards, not as fully approved production cards.

## UAT Implication

Wilku UAT can now include a concrete source-review step:

- "Czy te publiczne źródła dobrze opisują realną ofertę Ekologus?"
- "Które usługi są core, a które tylko edukacyjne lub produktowe?"
- "Które claimy wymagają eksperta prawnego/środowiskowego?"
- "Które CTA są handlowo akceptowalne?"
- "Czy Zielony Ład ma mapować do usługi, czy tylko do edukacji?"
- "Czy sorbenty mają wejść do content operations dopiero po Merchant/shop
  evidence?"

Without that review, WILQ may use this pack as source-backed preparation, but
must not claim deep, approved Ekologus knowledge.

## Verification

Docs-only slice:

```bash
rtk git diff --check
```

No product tests are required for this source-pack document. Run knowledge-card
tests when `wilq/content/knowledge/cards.py` changes.
