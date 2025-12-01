"""Integration tests for monitoring API endpoints using a stub monitoring service."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints import monitoring as monitoring_module
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def stub_monitoring_service(tmp_path: Path):
    report_path = tmp_path / "stub_report.html"
    report_path.write_text("<html>report</html>")

    class StubService:
        def __init__(self) -> None:
            self.buffer = SimpleNamespace(stats=lambda: {"total_records": 3, "latest_timestamp": "2024-01-01T00:00:00"})
            self._report_path = report_path

        def summary(self):
            return {
                "buffer": self.buffer.stats(),
                "last_report": None,
                "reports_dir": str(tmp_path),
                "reference_data_loaded": True,
                "dashboard_url": "http://evidently.local",
            }

        def list_reports(self):
            return [{"name": "stub", "created_at": "now"}]

        def get_report_path(self, name: str):
            return self._report_path if name == "stub" else None

        def generate_report(self):
            return SimpleNamespace(to_dict=lambda: {"name": "stub"})

    return StubService()


def test_monitoring_summary_returns_buffer_stats(client: TestClient, stub_monitoring_service, monkeypatch):
    monkeypatch.setattr(monitoring_module, "get_monitoring_service", lambda: stub_monitoring_service)

    response = client.get("/v1/monitoring/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["buffer"]["total_records"] == 3
    assert payload["dashboard_url"] == "http://evidently.local"


def test_generate_report_uses_service_and_returns_payload(client: TestClient, stub_monitoring_service, monkeypatch):
    monkeypatch.setattr(monitoring_module, "get_monitoring_service", lambda: stub_monitoring_service)

    response = client.post("/v1/monitoring/generate")

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Report generated"
    assert body["report"]["name"] == "stub"


def test_fetch_report_file_serves_html(client: TestClient, stub_monitoring_service, monkeypatch):
    monkeypatch.setattr(monitoring_module, "get_monitoring_service", lambda: stub_monitoring_service)

    response = client.get("/v1/monitoring/reports/stub")

    assert response.status_code == 200
    assert b"report" in response.content


def test_fetch_missing_report_returns_404(client: TestClient, stub_monitoring_service, monkeypatch):
    monkeypatch.setattr(monitoring_module, "get_monitoring_service", lambda: stub_monitoring_service)

    response = client.get("/v1/monitoring/reports/unknown")

    assert response.status_code == 404
    assert response.json()["detail"] == "Report not found"


def test_fetch_report_rejects_path_traversal(client: TestClient, stub_monitoring_service, monkeypatch):
    monkeypatch.setattr(monitoring_module, "get_monitoring_service", lambda: stub_monitoring_service)

    response = client.get("/v1/monitoring/reports/../secret")

    assert response.status_code == 404
