from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app


def test_section_map_review_is_always_api_owned() -> None:
    paths = TestClient(app).get("/openapi.json").json()["paths"]

    assert not any("section-map" in path for path in paths)
