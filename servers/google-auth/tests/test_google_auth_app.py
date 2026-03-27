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


def test_token_with_subject(app_client, mock_creds):
    """POST /token with explicit subject uses that subject for delegation."""
    resp = app_client.post(
        "/token",
        json={
            "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
            "subject": "alice@example.com",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"] == "fake-access-token-123"
    mock_creds.with_subject.assert_called_with("alice@example.com")


def test_token_without_subject_uses_default(app_client, mock_creds):
    """POST /token without subject falls back to GOOGLE_DELEGATED_USER."""
    resp = app_client.post(
        "/token",
        json={"scopes": ["https://www.googleapis.com/auth/gmail.readonly"]},
    )
    assert resp.status_code == 200
    # The last with_subject call for a token request (not startup) should use default
    # Find the call that corresponds to the token request
    subject_calls = mock_creds.with_subject.call_args_list
    # At least one call should use the default subject "agent@example.com"
    default_calls = [c for c in subject_calls if c.args[0] == "agent@example.com"]
    assert len(default_calls) >= 1, f"Expected call with agent@example.com, got {subject_calls}"


def test_token_cache_different_subjects(app_client, mock_creds):
    """Same scopes but different subjects must NOT share cache."""
    scopes = ["https://www.googleapis.com/auth/gmail.readonly"]
    app_client.post("/token", json={"scopes": scopes, "subject": "alice@example.com"})
    app_client.post("/token", json={"scopes": scopes, "subject": "bob@example.com"})
    # refresh: 1 startup + 1 alice + 1 bob = 3 (different subjects = no cache hit)
    assert mock_creds.refresh.call_count == 3


def test_token_cache_same_subject(app_client, mock_creds):
    """Same scopes and same subject should use cache on second call."""
    scopes = ["https://www.googleapis.com/auth/gmail.readonly"]
    app_client.post("/token", json={"scopes": scopes, "subject": "alice@example.com"})
    app_client.post("/token", json={"scopes": scopes, "subject": "alice@example.com"})
    # refresh: 1 startup + 1 alice (first call) = 2 (second call hits cache)
    assert mock_creds.refresh.call_count == 2


def test_startup_stores_subject_free_creds(tmp_path):
    """Lifespan stores base_creds WITHOUT subject baked in."""
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
            # from_service_account_file should be called with ONLY the key path
            # (no subject= kwarg)
            MockCreds.from_service_account_file.assert_called_once_with(str(key_file))


def test_startup_stores_default_subject(tmp_path):
    """Lifespan stores default_subject in app.state from GOOGLE_DELEGATED_USER."""
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
        with TestClient(app_module.app) as tc:
            assert app_module.app.state.default_subject == "test@example.com"


def test_token_error_includes_subject(app_client, mock_creds):
    """Error message from failed token minting includes the subject email."""
    mock_creds.refresh.reset_mock()
    mock_creds.refresh.side_effect = [Exception("fail1"), Exception("fail2")]

    resp = app_client.post(
        "/token",
        json={
            "scopes": ["https://www.googleapis.com/auth/drive.readonly"],
            "subject": "bad@example.com",
        },
    )
    assert resp.status_code == 503
    assert "bad@example.com" in resp.json()["detail"]


def test_cache_clear_all(app_client, mock_creds):
    """DELETE /cache clears all cached tokens."""
    # Prime two different scope sets
    app_client.post("/token", json={"scopes": ["https://www.googleapis.com/auth/gmail.readonly"]})
    app_client.post("/token", json={"scopes": ["https://www.googleapis.com/auth/calendar"]})

    resp = app_client.delete("/cache")
    assert resp.status_code == 200
    data = resp.json()
    assert data["cleared"] == 2

    # Next token request should re-mint (refresh called again)
    count_before = mock_creds.refresh.call_count
    app_client.post("/token", json={"scopes": ["https://www.googleapis.com/auth/gmail.readonly"]})
    assert mock_creds.refresh.call_count == count_before + 1


def test_cache_clear_by_subject(app_client, mock_creds):
    """DELETE /cache?subject=... clears only entries for that subject."""
    app_client.post(
        "/token",
        json={"scopes": ["https://www.googleapis.com/auth/gmail.readonly"], "subject": "alice@example.com"},
    )
    app_client.post(
        "/token",
        json={"scopes": ["https://www.googleapis.com/auth/gmail.readonly"], "subject": "bob@example.com"},
    )

    resp = app_client.delete("/cache", params={"subject": "alice@example.com"})
    assert resp.status_code == 200
    assert resp.json()["cleared"] == 1

    # Bob's token should still be cached (no new refresh)
    count_before = mock_creds.refresh.call_count
    app_client.post(
        "/token",
        json={"scopes": ["https://www.googleapis.com/auth/gmail.readonly"], "subject": "bob@example.com"},
    )
    assert mock_creds.refresh.call_count == count_before  # cache hit


def test_cache_clear_empty(app_client):
    """DELETE /cache with no cached tokens returns cleared=0."""
    # Clear any startup-primed tokens first
    app_client.delete("/cache")

    resp = app_client.delete("/cache")
    assert resp.status_code == 200
    assert resp.json()["cleared"] == 0


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
