import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from main import app
from api.routes import active_sessions, delete_session_state

client = TestClient(app)

@pytest.fixture
def mock_session():
    session_id = "test_session_id"
    # Setup
    active_sessions[session_id] = {
        "chunks": ["Chunk 1", "Chunk 2"],
        "translated_chunks": ["Bản dịch 1"],
        "current_chunk_idx": 1,
        "total_chunks": 2,
        "is_paused": False,
        "glossary": {},
        "model": "gemini-1.5-flash",
        "source_lang": "zh",
        "target_lang": "vi",
        "provider": "gemini",
        "api_key": "test_api_key",
        "queue": asyncio.Queue()
    }
    yield session_id
    # Teardown
    if session_id in active_sessions:
        del active_sessions[session_id]
    delete_session_state(session_id)

def test_pause_endpoint_missing_session_id():
    response = client.post("/api/pause")
    assert response.status_code == 422  # Missing query parameter

def test_pause_endpoint_not_found():
    response = client.post("/api/pause?session_id=nonexistent_id")
    assert response.status_code == 404
    assert "Không tìm thấy phiên dịch thuật này" in response.json()["detail"]

def test_pause_endpoint_success(mock_session):
    response = client.post(f"/api/pause?session_id={mock_session}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert active_sessions[mock_session]["is_paused"] is True

def test_resume_endpoint_not_found():
    response = client.post("/api/resume?session_id=nonexistent_id")
    assert response.status_code == 404
    assert "Không tìm thấy phiên dịch thuật để tiếp tục" in response.json()["detail"]

def test_resume_endpoint_already_running(mock_session):
    response = client.post(f"/api/resume?session_id={mock_session}")
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"

def test_resume_endpoint_success(mock_session):
    active_sessions[mock_session]["is_paused"] = True
    response = client.post(f"/api/resume?session_id={mock_session}", json={"api_key": "new_key"})
    assert response.status_code == 200
    assert response.json()["status"] == "resumed"
    assert active_sessions[mock_session]["is_paused"] is False
    assert active_sessions[mock_session]["api_key"] == "new_key"

def test_stream_endpoint_not_found():
    response = client.get("/api/stream?session_id=nonexistent_id")
    assert response.status_code == 404
    assert "Không tìm thấy phiên dịch thuật này" in response.json()["detail"]

def test_stream_endpoint_success(mock_session):
    active_sessions[mock_session]["queue"].put_nowait({"event": "completed"})
    with client.stream("GET", f"/api/stream?session_id={mock_session}") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

@patch("api.routes.novel_translator.translate_chunk", new_callable=AsyncMock)
def test_translate_chunk_endpoint_success(mock_translate_chunk):
    mock_translate_chunk.return_value = "Bản dịch cụ thể thành công."
    
    payload = {
        "source_text": "Hello world",
        "custom_prompt": "Dịch vui vẻ",
        "model_name": "gemini-1.5-flash",
        "api_key": "fake-api-key",
        "provider": "gemini",
        "source_lang": "Tiếng Anh",
        "target_lang": "Tiếng Việt"
    }
    
    response = client.post("/api/translate-chunk", json=payload)
    assert response.status_code == 200
    assert response.json() == {"translated_text": "Bản dịch cụ thể thành công."}
    
    mock_translate_chunk.assert_called_once_with(
        chunk="Hello world",
        glossary_dict={},
        api_key="fake-api-key",
        model_name="gemini-1.5-flash",
        source_lang="Tiếng Anh",
        target_lang="Tiếng Việt",
        provider="gemini",
        use_agentic=False,
        previous_context="",
        custom_prompt="Dịch vui vẻ",
        use_cache=False
    )

def test_state_endpoint_not_found():
    response = client.get("/api/state/nonexistent_id")
    assert response.status_code == 404
    assert "Không tìm thấy phiên dịch thuật này" in response.json()["detail"]

def test_state_endpoint_success(mock_session):
    response = client.get(f"/api/state/{mock_session}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["direction"] == "horizontal"
    assert response.json()["toc"] == []

