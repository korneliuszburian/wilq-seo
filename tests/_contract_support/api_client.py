"""Shared FastAPI test client for API contract suites."""

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app

client = TestClient(app)
