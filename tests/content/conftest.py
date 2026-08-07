from collections.abc import Iterator

import pytest

from tests._contract_support.action_candidate_seed import (
    save_action_candidate_metric_facts,
    save_content_workflow_service_page_metric_facts,
)

_SERVICE_PAGE_SEED_MODULES = frozenset(
    {
        "test_content_workflow_end_to_end.py",
        "test_content_workflow_adversarial_gates.py",
        "test_work_item_preflight_api.py",
        "test_content_workflow_snapshot_response.py",
        "test_structured_draft_generation.py",
        "test_wordpress_execution_api.py",
    }
)


@pytest.fixture(scope="module", autouse=True)
def content_workflow_service_page_seed(request: pytest.FixtureRequest) -> Iterator[None]:
    """Bind workflow fixtures to a reviewed service URL, not an argument page."""
    if request.path.name not in _SERVICE_PAGE_SEED_MODULES:
        yield
        return
    save_content_workflow_service_page_metric_facts()
    try:
        yield
    finally:
        save_action_candidate_metric_facts()
