"""Tests for Google auth token vending server."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def test_health(app_client):
    """GET /health returns status, service, subject, and verified_scopes."""
    resp = app_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "google-auth-server"
    assert data["subject"] == "agent@example.com"
    assert "verified_scopes" in data
    assert isinstance(data["verified_scopes"], list)


def test_token_success(app_client, mock_creds):
    """POST /token with valid scopes returns access_token, expires_in, token_type."""
    resp = app_client.post(
        "/token", json={"scopes": ["https://www.googleapis.com/auth/gmail.readonly"]}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"] == "fake-access-token-123"
    assert "expires_in" in data
    assert data["expires_in"] > 0
    assert data["token_type"] == "Bearer"


def test_token_missing_scopes(app_client):
    """POST /token with empty scopes returns 400."""
    resp = app_client.post("/token", json={"scopes": []})
    assert resp.status_code == 400


def test_token_no_scopes_field(app_client):
    """POST /token without scopes field returns 422 (validation error)."""
    resp = app_client.post("/token", json={})
    assert resp.status_code == 422


def test_token_caching(app_client, mock_creds):
    """Two POST /token calls with same scopes -- credentials.refresh() called only once."""
    scopes = {"scopes": ["https://www.googleapis.com/auth/gmail.readonly"]}
    app_client.post("/token", json=scopes)
    app_client.post("/token", json=scopes)
    # refresh called once for startup validation + once for first token request = 2
    # Second token request should use cache, so still 2
    assert mock_creds.refresh.call_count == 2


def test_token_cache_expired(app_client, mock_creds):
    """Cached token with <60s remaining triggers new refresh."""
    scopes = {"scopes": ["https://www.googleapis.com/auth/gmail.readonly"]}

    # Set expiry to 30s from now so cached token is near-expired
    mock_creds.expiry = datetime.now(UTC) + timedelta(seconds=30)
    app_client.post("/token", json=scopes)
    initial_refresh_count = mock_creds.refresh.call_count

    # Second request should see <60s remaining and re-mint
    resp = app_client.post("/token", json=scopes)
    assert resp.status_code == 200
    # Should have called refresh again
    assert mock_creds.refresh.call_count == initial_refresh_count + 1


def test_token_different_scopes(app_client, mock_creds):
    """Different scope sets get different cached tokens."""
    app_client.post(
        "/token", json={"scopes": ["https://www.googleapis.com/auth/gmail.readonly"]}
    )
    app_client.post(
        "/token", json={"scopes": ["https://www.googleapis.com/auth/calendar.readonly"]}
    )
    # refresh: 1 startup + 1 first scopes + 1 different scopes = 3
    assert mock_creds.refresh.call_count == 3


def test_token_google_error_retry_success(app_client, mock_creds):
    """Transient google error retried once, succeeds on retry."""
    mock_creds.refresh.reset_mock()
    mock_creds.refresh.side_effect = [Exception("transient"), None]
    mock_creds.expiry = datetime.now(UTC) + timedelta(hours=1)

    resp = app_client.post(
        "/token",
        json={"scopes": ["https://www.googleapis.com/auth/gmail.readonly"]},
    )
    assert resp.status_code == 200


def test_token_google_error_retry_failure(app_client, mock_creds):
    """Two consecutive google errors result in 503."""
    mock_creds.refresh.reset_mock()
    mock_creds.refresh.side_effect = [Exception("fail1"), Exception("fail2")]

    resp = app_client.post(
        "/token",
        json={"scopes": ["https://www.googleapis.com/auth/drive.readonly"]},
    )
    assert resp.status_code == 503


def test_startup_loads_key(tmp_path):
    """Lifespan calls Credentials.from_service_account_file with path from env."""
    key_file = tmp_path / "service-account.json"
    key_file.write_text("{}")

    creds = MagicMock()
    creds.token = "fake-token"
    creds.expiry = datetime.now(UTC) + timedelta(hours=1)
    creds.with_scopes.return_value = creds
    creds.with_subject.return_value = creds
    creds.refresh.return_value = None

    env = {
        "GOOGLE_SERVICE_ACCOUNT_KEY": str(key_file),
        "GOOGLE_DELEGATED_USER": "test@example.com",
    }
    with (
        patch.dict("os.environ", env),
        patch("google_auth_server.app.service_account.Credentials") as MockCreds,
        patch("google_auth_server.app.google_auth_transport.Request"),
    ):
        MockCreds.from_service_account_file.return_value = creds
        import importlib

        import google_auth_server.app as app_module

        importlib.reload(app_module)
        with TestClient(app_module.app):
            MockCreds.from_service_account_file.assert_called_once_with(
                str(key_file), subject="test@example.com"
            )


def test_default_bind():
    """main() calls uvicorn.run with host='127.0.0.1', port=8301."""
    with patch("uvicorn.run") as mock_run:
        import importlib

        import google_auth_server.app as app_module

        importlib.reload(app_module)
        app_module.main()
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        assert call_kwargs.kwargs.get("host", call_kwargs[1].get("host")) == "127.0.0.1"
        assert call_kwargs.kwargs.get("port", call_kwargs[1].get("port")) == 8301
