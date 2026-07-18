# Second-opinion review: Ads to content demand lineage

## Claim under review

Exact Google Ads search terms with a resolved, redacted landing identity may enter
the content planning demand contract even when the same term is absent from GSC.
Such rows must remain page-only, carry exact service/page lineage and freshness,
and must never be assigned to a content section by guesswork.

## Fixed scope

Review only the changed contract and its callers:

- `wilq/content/workflow/demand_evidence.py`
- `wilq/schemas/ads.py`
- `packages/shared-schemas/src/ads_search_terms.ts`
- `tests/content/test_search_demand_evidence.py`
- `tests/content/test_ads_landing_lineage_surface.py`

Check whether the change preserves:

1. exact landing identity and service-card binding;
2. fresh, complete Ads batch requirements and evidence IDs;
3. `page_only` section mapping when no GSC overlap exists;
4. rejection of wrong, ambiguous, stale, sensitive or foreign landings;
5. no raw URL exposure and no vendor write or auto-approval;
6. v1/shared-schema compatibility and digest/lineage safety.

## Local proof already run

- `uv run --extra dev pytest -q tests/content/test_search_demand_evidence.py` — 9 passed.
- `uv run --extra dev pytest -q tests/content/test_dynamic_planning_input_sources.py -k 'ads or source'` — 9 passed.
- `uv run ruff check wilq/content/workflow/demand_evidence.py tests/content/test_search_demand_evidence.py` — passed.
- `uv run --extra dev pytest -q tests/content/test_ads_landing_lineage_surface.py` — passed.
- `pnpm --dir packages/shared-schemas exec vitest run src/index.test.ts` — 42 passed.

## Boundaries

Do not claim that either live BDO or consulting/outsourcing pilot currently has
Ads rows: their current live planning proposals correctly report
`optional_ads_status=not_exactly_mapped` because no exact GSC/Ads term overlap is
present. Do not claim marketer UAT, semantic-review persistence, WordPress
publication, campaign mutation or Keyword Planner availability.

Return only schema-compatible findings. Be strict and identify any lineage,
freshness, privacy, section-mapping, compatibility or safety defect. Do not
declare the claim complete.

Citation discipline: every finding must cite exactly one repository-relative
path and a single line or a range of at most 5 consecutive lines from the
excerpts below. Never cite a whole function or a range longer than 5 lines.

The current implementation additionally keys GSC joins by `(row.page, row.term)`
and uses `_fact_page(facts[0])` for page-only Ads rows. The mapped fallback keeps
`mapped_allowed_page` and sets `final_url` to the validated allowed page. It sets
`review_required=True` when there is no same-page GSC row and explicitly filters
the landing-identity loop to `source_connector == "google_ads"`.

The direct service-scoped path is intentionally a separate contract: it requires
an explicit service-card and allowed-page scope; the batch and clicked-landing
gates apply to identity-resolved fallback rows. The mapped fallback now also
sets `page` and `landing_page` to the validated allowed page.

`_fact_page` precedence in the current fixed point is `page`, `landing_page`,
`mapped_allowed_page`, then `final_url`; the fallback always writes the validated
allowed page to both mapped and final dimensions.

## Current evidence excerpts

```text
wilq/content/workflow/demand_evidence.py:304-332
def _build_exact_ads_rows(...):
    for (_, term), facts in ads_groups.items():
        gsc_row = gsc_by_page_term.get((ads_page, term))
        ...
        row = _ads_row(gsc_row=gsc_row, facts=facts,
                       final_canonical_url=final_canonical_url,
                       service_card_id=service_card_id, freshness=freshness)
        if row is not None:
            (planner_rows if source_kind == "keyword_planner" else ads_rows).append(row)

wilq/content/workflow/demand_evidence.py:444-490
def _ads_row(..., gsc_row: ContentSearchDemandRow | None, ...):
    landing_match_tiers = _landing_match_tiers(facts, final_canonical_url)
    if not landing_match_tiers:
        return None
    page = gsc_row.page if gsc_row is not None else _fact_page(facts[0])
    if page is None:
        return None
    section_headings = gsc_row.section_headings if gsc_row is not None else []
    section_mapping_status = (
        gsc_row.section_mapping_status if gsc_row is not None else "page_only"
    )
    return ContentSearchDemandRow(
        source_kind=source_kind, source_connector="google_ads", term=term,
        page=page, landing_match_tiers=landing_match_tiers,
        service_card_id=service_card_id,
        alignment_basis=("same_window_search_term_landing"
                         if any(ADS_LANDING_IDENTITY in fact.dimensions for fact in facts)
                         else "direct_page_service_scope"),
        review_required=gsc_row is None, section_headings=section_headings,
        section_mapping_status=section_mapping_status,
        period=facts[0].period, freshness=_connector_freshness_state(...),
        evidence_ids=list(dict.fromkeys(fact.evidence_id for fact in facts)), ...

wilq/content/workflow/demand_evidence.py:521-579
def _strict_ads_scope_matches(...):
    return bool(service_card_id
        and fact.dimensions.get("service_card_id") == service_card_id
        and _page_matches_allowed(_fact_page(fact), allowed_pages)
        and (fact.dimensions.get("search_term")
             or fact.dimensions.get("keyword_idea_text")))

def _exact_ads_groups(...):
    direct_groups = _group_facts(fact for fact in metric_facts
        if fact.source_connector == "google_ads"
        and _strict_ads_scope_matches(...))
    if not service_card_id:
        return direct_groups
    ready_evidence_ids = _ready_ads_batch_evidence_ids(metric_facts)
    for (_scope, term, landing_identity), term_facts in _group_ads_term_facts(metric_facts):
        if not _clicked_landing_batch_is_complete(term_facts, ready_evidence_ids) \
           or not _clicked_landing_lineage_is_valid(term_facts):
            continue
        landing_page = _allowed_page_for_landing_identity(landing_identity, allowed_pages)
        if landing_page is None:
            continue
        page_scoped_facts = [fact.model_copy(update={
            "dimensions": {**fact.dimensions,
                "mapped_allowed_page": landing_page,
                "final_url": landing_page}})
            for fact in term_facts]
        direct_groups.setdefault((landing_page, term), []).extend(page_scoped_facts)

wilq/schemas/ads.py:1062-1082
class AdsSearchTermMetricRow(BaseModel):
    search_term: str
    ...
    landing_mapping_status: str | None = None
    landing_identity_sha256: str | None = None
    ...

packages/shared-schemas/src/ads_search_terms.ts:5-25
export const AdsSearchTermMetricRowSchema = z.object({
  search_term: z.string(), ...
  landing_mapping_status: z.string().nullable().optional(),
  landing_identity_sha256: z.string().nullable().optional(), ...
});

tests/content/test_search_demand_evidence.py:124-181
def test_search_demand_keeps_exact_ads_term_without_gsc_overlap_as_page_only():
    ... exact resolved landing identity, fresh five-metric batch and payload status ...
    assert row.page == page
    assert row.section_mapping_status == "page_only"
    assert row.section_headings == []
    assert row.alignment_basis == "same_window_search_term_landing"
```
