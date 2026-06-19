import pytest
from fastapi.testclient import TestClient
from main import app
from api.routes import active_task

client = TestClient(app)

def test_pause_endpoint_no_active_task():
    active_task["task_id"] = None
    response = client.post("/api/pause")
    assert response.status_code == 400
    assert "Không có tiến trình dịch thuật nào đang chạy" in response.json()["detail"]

def test_pause_endpoint_success():
    active_task["task_id"] = "test_task"
    active_task["is_paused"] = False
    response = client.post("/api/pause")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert active_task["is_paused"] is True

def test_resume_endpoint_no_active_task():
    active_task["task_id"] = None
    response = client.post("/api/resume")
    assert response.status_code == 400
    assert "Không có tiến trình nào để tiếp tục" in response.json()["detail"]

def test_resume_endpoint_already_running():
    active_task["task_id"] = "test_task"
    active_task["is_paused"] = False
    response = client.post("/api/resume")
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
