"""Integration tests for the Talend Health Analyzer API."""

import io
import zipfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.analysis_service import analysis_service


@pytest.fixture(autouse=True)
def _cleanup_analysis_service():
    analysis_service._records.clear()
    analysis_service._task_index.clear()
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def minimal_talend_zip():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(".project", '<?xml version="1.0" encoding="UTF-8"?><projectDescription><name>TestProject</name></projectDescription>')
        zf.writestr(
            "TestProject/process/test_job.item",
            '<?xml version="1.0" encoding="UTF-8"?><process><parameters><parameter name="PROCESS_TYPE" value="JOB_DESIGN"/></parameters><node componentName="tLogRow"><elementParameter name="NAME" value="tLogRow_1"/></node></process>',
        )
    buf.seek(0)
    return buf


class TestApiHealth:
    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_health_endpoint(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_timing_header_present(self, client):
        response = client.get("/")
        assert "X-Process-Time" in response.headers
        process_time = int(response.headers["X-Process-Time"])
        assert process_time >= 0


class TestUploadEndpoint:
    def test_upload_zip_missing_file(self, client):
        response = client.post("/api/v1/uploads/zip")
        assert response.status_code == 422

    def test_upload_zip_invalid_content_type(self, client):
        response = client.post(
            "/api/v1/uploads/zip",
            files={"file": ("test.txt", b"not a zip", "text/plain")},
        )
        assert response.status_code == 400

    def test_upload_zip_success(self, client, minimal_talend_zip):
        response = client.post(
            "/api/v1/uploads/zip",
            files={"file": ("test.zip", minimal_talend_zip.read(), "application/zip")},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["filename"].endswith(".zip")
        assert data["size_bytes"] > 0
        assert data["path"]

    def test_upload_zip_plain_bytes(self, client):
        response = client.post(
            "/api/v1/uploads/zip",
            files={"file": ("notazip.zip", b"not a real zip content", "application/zip")},
        )
        assert response.status_code == 400


class TestAnalysisStatus:
    def test_get_analysis_status_not_found(self, client):
        response = client.get("/api/v1/analysis/nonexistent/status")
        assert response.status_code == 404

    def test_get_analysis_status_found(self, client):
        record = analysis_service.create_analysis("/fake/path.zip", "test.zip")
        response = client.get(f"/api/v1/analysis/{record.analysis_id}/status")
        assert response.status_code == 200
        data = response.json()
        assert data["analysis_id"] == record.analysis_id
        assert data["status"] == "queued"

    def test_get_analysis_status_follows_create(self, client):
        record_a = analysis_service.create_analysis("/a.zip", "a.zip")
        record_b = analysis_service.create_analysis("/b.zip", "b.zip")
        resp_a = client.get(f"/api/v1/analysis/{record_a.analysis_id}/status")
        resp_b = client.get(f"/api/v1/analysis/{record_b.analysis_id}/status")
        assert resp_a.status_code == 200
        assert resp_b.status_code == 200
        assert resp_a.json()["analysis_id"] == record_a.analysis_id
        assert resp_b.json()["analysis_id"] == record_b.analysis_id


class TestDashboard:
    def test_get_dashboard_not_found(self, client):
        response = client.get("/api/v1/analysis/nonexistent/dashboard")
        assert response.status_code == 404

    def test_get_dashboard_not_ready(self, client):
        record = analysis_service.create_analysis("/fake/path.zip", "test.zip")
        response = client.get(f"/api/v1/analysis/{record.analysis_id}/dashboard")
        assert response.status_code == 202


class TestAnalysisEndpoints:
    """Test analysis execution with mocked workflow."""

    @patch("backend.services.analysis_service.AgentWorkflow")
    def test_execute_analysis_success(self, mock_workflow_cls, client, minimal_talend_zip):
        state = MagicMock()
        state.status.value = "completed"
        state.model_dump.return_value = {
            "status": "completed",
            "current_agent": None,
            "active_agents": [],
            "execution_order": [],
            "node_statuses": {},
            "errors": [],
            "skipped_nodes": [],
            "progress": 100,
        }
        state.results = []
        state.errors = []

        mock_workflow = MagicMock()
        mock_workflow.run = AsyncMock(return_value=state)
        mock_workflow_cls.return_value = mock_workflow

        response = client.post(
            "/api/v1/uploads/zip/execute",
            files={"file": ("test.zip", minimal_talend_zip.read(), "application/zip")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"].startswith("task_")
        assert data["analysis_id"].startswith("analysis_")

    @patch("backend.services.analysis_service.AgentWorkflow")
    def test_upload_and_analyze_queues(self, mock_workflow_cls, client, minimal_talend_zip):
        mock_workflow = MagicMock()
        mock_workflow_cls.return_value = mock_workflow

        response = client.post(
            "/api/v1/uploads/zip/analyze",
            files={"file": ("test.zip", minimal_talend_zip.read(), "application/zip")},
        )
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "queued"
        assert data["task_status_url"]
        assert data["dashboard_url"]
