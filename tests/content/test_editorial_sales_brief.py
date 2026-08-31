from tests.content.test_sales_brief import (
    _claim_ledger,
    _enrichment,
    _inventory,
    _item,
    _seed,
)
from wilq.content.briefs.sales import build_content_sales_brief
from wilq.content.inventory.records import resolve_content_inventory
from wilq.content.preflight.workflow import build_content_preflight_verdict


def test_editorial_sales_brief_does_not_require_service_knowledge_card() -> None:
    work_item = _item().model_copy(
        update={"wordpress_content_type": "post", "content_kind": "editorial"}
    )
    inventory = resolve_content_inventory([_inventory()], duplicate_risk="clear")
    preflight = build_content_preflight_verdict(work_item, inventory)

    result = build_content_sales_brief(
        item=work_item,
        preflight=preflight,
        inventory=inventory,
        claim_ledger=_claim_ledger(),
        seed=_seed(),
        enrichment=_enrichment(),
        knowledge_match=None,
    )

    assert result.brief is not None
    assert "missing_required_knowledge_card" not in [
        blocker.code for blocker in result.blockers
    ]
