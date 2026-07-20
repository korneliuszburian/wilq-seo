from __future__ import annotations

from tests._contract_support.api_client import client


def test_source_material_manifest_redacts_local_paths() -> None:
    manifest = client.get("/api/knowledge/source-materials")
    readiness = client.get("/api/knowledge/source-materials/readiness")

    assert manifest.status_code == 200
    assert readiness.status_code == 200
    assert manifest.json()
    assert all("source_path" not in item for item in manifest.json())

    payload = readiness.json()
    for key in ("imported_materials", "pending_materials", "excerpt_review_materials"):
        assert all("source_path" not in item for item in payload.get(key, []))
