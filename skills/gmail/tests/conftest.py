"""Shared fixtures for Gmail skill tests."""

import base64
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_auth_client():
    """Patch ClawsClient in gmail module to return a test token."""
    with patch("claws_gmail.gmail.ClawsClient") as mock_cls:
        instance = MagicMock()
        instance.post_json.return_value = {
            "access_token": "test-token",
            "expires_in": 3300,
            "token_type": "Bearer",
        }
        mock_cls.return_value = instance
        yield instance


@pytest.fixture
def mock_httpx():
    """Patch httpx in gmail module."""
    with patch("claws_gmail.gmail.httpx") as mock:
        yield mock


@pytest.fixture
def sample_message_metadata():
    """Gmail API message response in format=metadata."""
    return {
        "id": "msg-001",
        "threadId": "thread-001",
        "snippet": "Hey, how are you?",
        "payload": {
            "headers": [
                {"name": "From", "value": "alice@example.com"},
                {"name": "Subject", "value": "Hello there"},
                {"name": "Date", "value": "Mon, 17 Mar 2026 10:00:00 -0700"},
            ]
        },
    }


@pytest.fixture
def sample_message_full():
    """Gmail API message response in format=full with nested MIME."""
    body_text = base64.urlsafe_b64encode(b"This is the plain text body.").decode("ascii")
    return {
        "id": "msg-002",
        "threadId": "thread-002",
        "snippet": "This is the plain text...",
        "payload": {
            "mimeType": "multipart/mixed",
            "parts": [
                {
                    "mimeType": "multipart/alternative",
                    "parts": [
                        {
                            "mimeType": "text/plain",
                            "body": {"data": body_text, "size": 28},
                        },
                        {
                            "mimeType": "text/html",
                            "body": {
                                "data": base64.urlsafe_b64encode(
                                    b"<p>This is the plain text body.</p>"
                                ).decode("ascii"),
                                "size": 40,
                            },
                        },
                    ],
                }
            ],
        },
    }
