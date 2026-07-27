from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers.content_workflow import router
from wilq.content.workflow.operator import ContentOperatorContext, content_operator_context


def test_content_operator_context_is_deterministic_read_only_route_metadata() -> None:
    assert content_operator_context() == content_operator_context()
    assert ContentOperatorContext.model_validate(content_operator_context()).model_dump() == {
        "display_label": "Wilku (lokalny pilot)",
        "request_label": "operator_local_dashboard",
        "principal_id": "local_operator",
        "trust_level": "local_unverified",
        "authentication_status": "not_configured",
    }
    assert [route.path for route in router.routes].count("/api/content/operator-context") == 1

    response = TestClient(app).get("/api/content/operator-context")

    assert response.status_code == 200
    assert ContentOperatorContext.model_validate(response.json()) == content_operator_context()
