# Goal 005 Sales Brief v2 Signal Quality Audit

Date: 2026-07-01

Beads task: `wilq-seo-n8r`

## Scope

Audit whether current Content Work Item -> Enrichment -> Sales Brief v2 inputs
are dense, fresh and Ekologus-specific enough for Wilku review. This is not a
claim that content is publication-ready.

Live endpoints used:

- `GET /api/content/diagnostics`
- `GET /api/content/work-items/queue`
- `GET /api/content/work-items/{work_item_id}/enrichment`
- `GET /api/content/work-items/{work_item_id}/snapshot`

Relevant fresh evidence from the current local API:

- GSC evidence includes `ev_refresh_refresh_google_search_console_27ca850b1fa4`
  and related GSC refresh evidence.
- WordPress evidence includes `ev_refresh_refresh_wordpress_ekologus_691cbe6ab27d`
  and related WordPress inventory evidence.

## Candidate Readout

| Candidate | State | Signal Quality | Main Cause |
| --- | --- | --- | --- |
| `beczki` / Ahrefs gap | blocked | typed blocked snapshot | Ahrefs gap has evidence, but no final canonical URL, unresolved duplicate/inventory risk and blocked measurement. Snapshot now returns `blocked_snapshot` with blockers instead of HTTP 404. |
| `bdo co to` | brief built | usable for review | GSC + WordPress evidence, existing URL, ready enrichment, measurement ready to plan, Sales Brief has 3 source facts and 15 knowledge constraints. |
| `zielony ład co to` | brief built | thin but reviewable | GSC + WordPress evidence and existing URL are present, but service fit is still generic: `sprawdzenie dopasowania do oferty Ekologus przed szkicem`. Needs Wilku/source review before strong service framing. |
| `operat wodnoprawny` | brief blocked | blocked by knowledge | GSC + WordPress evidence and enrichment are ready, but Sales Brief blocks with `missing_required_knowledge_card`. |
| `magazynowanie odpadów` | brief built for review | usable for review | GSC + WordPress evidence and enrichment are ready. A source-backed review-required waste/packaging service card now supports the brief, while draft remains not publish-ready. |

## Findings

1. Connector freshness is not the main blocker for current content candidates.
   The current queue has live GSC and WordPress evidence for four actionable
   refresh candidates.

2. Sales Brief v2 correctly blocks thin knowledge for `operat wodnoprawny`.
   `magazynowanie odpadów` now has a source-backed review-required card, so it
   can support brief review/UAT without becoming production-depth knowledge.
   This is desired behavior: WILQ should not turn GSC demand plus an existing
   page into a service-depth brief without a matching reviewed or
   review-required knowledge card.

3. `bdo co to` is the strongest UAT candidate. It has compliance-risk intent,
   GSC demand, WordPress inventory, existing canonical URL, measurement plan and
   reviewed-style BDO constraints.

4. `zielony ład co to` is reviewable but weaker. The data supports a
   preserve-first refresh, but the service mapping remains generic. Use this as
   a Wilku question, not as proof of production-depth service knowledge.

5. Traceability bug found and fixed during the audit: enrichment source facts
   were assigning mixed decision evidence IDs to source facts. GSC facts could
   inherit WordPress evidence IDs. `wilq/content/enrichment/opportunity.py` now
   filters source fact evidence by connector where the evidence IDs expose the
   connector lineage.

6. Blocked Ahrefs candidates now have a typed UAT surface. Queue and enrichment
   are typed and correctly blocked, and snapshot returns `blocked_snapshot`
   instead of HTTP 404. WILQ does not fabricate a full workflow snapshot for a
   candidate without inventory/canonical resolution.

## Exact Follow-Ups

- `wilq-seo-nlz`: added a source-backed review-required card for
  `magazynowanie odpadów`; `operat wodnoprawny` remains blocked until a direct
  public/reviewed service source exists.
- `wilq-seo-ad8`: completed. Blocked Ahrefs content candidates return typed
  `blocked_snapshot` responses without fake workflow fields.
- Use `bdo co to` as the safest first Wilku UAT candidate.
- Use `zielony ład co to` as a source-trace/service-fit review question for
  Wilku.

## Verification

Focused checks run:

```bash
rtk uv run pytest tests/content/test_content_opportunity_enrichment_api.py tests/content/test_sales_brief.py -q
rtk uv run ruff check wilq/content/enrichment/opportunity.py tests/content/test_content_opportunity_enrichment_api.py
rtk uv run mypy wilq/content/enrichment/opportunity.py
```

Live proof after API restart:

```text
google_search_console ev_refresh_refresh_google_search_console_c79da8c88e09 Zapytania GSC: bdo co to
google_search_console ev_refresh_refresh_google_search_console_615c887b0dac Zapytania GSC: bdo co to
wordpress_ekologus ev_refresh_refresh_wordpress_ekologus_25f9090bdfe6 Spis WordPress: potwierdzony
knowledge_card ekologus_service_waste_packaging_obligations source_backed_review_required
snapshot magazynowanie odpadów brief_built=True blockers=[]
snapshot operat wodnoprawny brief_built=False blockers=[missing_required_knowledge_card]
snapshot beczki response_type=blocked_snapshot blockers=[duplicate_risk_unresolved, missing_inventory_resolution, missing_final_canonical, duplicate_gate_not_checked]
```
