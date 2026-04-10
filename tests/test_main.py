# tests/test_main.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


def test_health_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "budget_remaining" in data


def test_health_budget_remaining_is_int(client):
    resp = client.get("/health")
    assert isinstance(resp.json()["budget_remaining"], int)


def test_chat_rejects_message_over_500_chars(client):
    resp = client.post(
        "/chat",
        json={"message": "x" * 501, "recaptcha_v3_token": "tok"},
        headers={"user-agent": "pytest"},
    )
    assert resp.status_code == 422


def test_chat_rejects_invalid_personality(client):
    resp = client.post(
        "/chat",
        json={"message": "hi", "personality": "evil_mode", "recaptcha_v3_token": "tok"},
        headers={"user-agent": "pytest"},
    )
    assert resp.status_code == 422


def test_chat_returns_challenge_on_low_v3_score(client):
    with patch("app.main.verify_recaptcha_v3", new_callable=AsyncMock, return_value=0.3):
        resp = client.post(
            "/chat",
            json={"message": "hello", "recaptcha_v3_token": "low-score"},
            headers={"user-agent": "pytest"},
        )
    assert resp.status_code == 200
    assert resp.json() == {"challenge": True}


def test_chat_returns_403_when_v2_fails(client):
    with patch("app.main.verify_recaptcha_v3", new_callable=AsyncMock, return_value=0.2):
        with patch("app.main.verify_recaptcha_v2", new_callable=AsyncMock, return_value=False):
            resp = client.post(
                "/chat",
                json={
                    "message": "hello",
                    "recaptcha_v3_token": "low",
                    "recaptcha_v2_token": "bad-v2",
                },
                headers={"user-agent": "pytest"},
            )
    assert resp.status_code == 403


def test_chat_rejects_missing_user_agent(client):
    resp = client.post(
        "/chat",
        json={"message": "hi", "recaptcha_v3_token": "tok"},
        headers={"user-agent": ""},
    )
    assert resp.status_code == 400


def test_chat_returns_429_when_budget_exhausted(client):
    with patch("app.main.verify_recaptcha_v3", new_callable=AsyncMock, return_value=0.9):
        with patch("app.main.get_budget_remaining", return_value=0):
            resp = client.post(
                "/chat",
                json={"message": "hello", "recaptcha_v3_token": "good"},
                headers={"user-agent": "pytest"},
            )
    assert resp.status_code == 429
