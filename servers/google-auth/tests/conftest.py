"""Shared fixtures for google-auth server tests."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_creds():
    """Mock google-auth Credentials object."""
    creds = MagicMock()
    creds.token = "fake-access-token-123"
    creds.expiry = datetime.now(UTC) + timedelta(hours=1)
    creds.with_scopes.return_value = creds
    creds.with_subject.return_value = creds
    creds.refresh.return_value = None  # refresh mutates in place
    return creds


@pytest.fixture
def app_client(mock_creds, tmp_path):
    """TestClient with mocked credentials and env vars."""
    key_file = tmp_path / "service-account.json"
    key_file.write_text("{}")  # Dummy file -- mock bypasses actual loading

    env = {
        "GOOGLE_SERVICE_ACCOUNT_KEY": str(key_file),
        "GOOGLE_DELEGATED_USER": "agent@example.com",
    }
    with (
        patch.dict("os.environ", env),
        patch("google_auth_server.app.service_account.Credentials") as MockCreds,
        patch("google_auth_server.app.google_auth_transport.Request"),
    ):
        MockCreds.from_service_account_file.return_value = mock_creds
        # Must import after patching so lifespan uses mocks
        import importlib

        import google_auth_server.app as app_module

        importlib.reload(app_module)
        with TestClient(app_module.app) as tc:
            yield tc
