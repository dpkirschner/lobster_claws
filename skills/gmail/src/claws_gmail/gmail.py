"""Gmail API client module.

Handles token acquisition, message listing, reading with MIME parsing,
sending with base64url encoding, searching, and error handling.
"""

import base64
from email.mime.text import MIMEText

import httpx

from claws_common.client import ClawsClient
from claws_common.output import crash, fail

AUTH_PORT = 8301
GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.modify"
GMAIL_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


def get_access_token(as_user: str | None = None) -> str:
    """Get Gmail access token from auth server."""
    client = ClawsClient(service="google-auth", port=8301)
    body: dict = {"scopes": [GMAIL_SCOPE]}
    if as_user:
        body["subject"] = as_user
    resp = client.post_json("/token", body)
    return resp["access_token"]


def get_header(headers: list[dict], name: str) -> str:
    """Extract header value by name (case-insensitive).

    Gmail headers are [{\"name\": \"From\", \"value\": \"...\"}] format.
    """
    name_lower = name.lower()
    for h in headers:
        if h["name"].lower() == name_lower:
            return h["value"]
    return ""


def extract_body(payload: dict) -> str:
    """Extract plain-text body from Gmail MIME payload.

    Recursively walks nested multipart structures to find text/plain.
    Returns empty string if no text/plain found.
    """
    # Simple message: text/plain at current level
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

    # Multipart: walk parts tree
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
        # Recursive for nested multipart
        if part.get("parts"):
            body = extract_body(part)
            if body:
                return body

    return ""


def build_raw_message(
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
    bcc: str | None = None,
) -> str:
    """Build base64url-encoded RFC 2822 message for Gmail send API.

    Uses email.mime.text.MIMEText for proper MIME construction.
    Returns base64url string with padding stripped.
    """
    msg = MIMEText(body)
    msg["To"] = to
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc
    if bcc:
        msg["Bcc"] = bcc
    raw_bytes = msg.as_bytes()
    return base64.urlsafe_b64encode(raw_bytes).decode("ascii").rstrip("=")


def _gmail_headers(token: str) -> dict:
    """Build authorization headers for Gmail API calls."""
    return {"Authorization": f"Bearer {token}"}


def _gmail_get(path: str, token: str, params: dict | None = None) -> dict:
    """GET request to Gmail API."""
    resp = httpx.get(
        f"{GMAIL_BASE}{path}",
        params=params,
        headers=_gmail_headers(token),
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


def _gmail_post(path: str, token: str, json_data: dict) -> dict:
    """POST request to Gmail API."""
    resp = httpx.post(
        f"{GMAIL_BASE}{path}",
        json=json_data,
        headers=_gmail_headers(token),
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


def _fetch_message_metadata(msg_id: str, token: str) -> dict:
    """Fetch message metadata (headers + snippet) by ID."""
    data = _gmail_get(
        f"/messages/{msg_id}",
        token,
        params={
            "format": "metadata",
            "metadataHeaders": ["From", "Subject", "Date"],
        },
    )
    hdrs = data.get("payload", {}).get("headers", [])
    return {
        "id": data["id"],
        "thread_id": data["threadId"],
        "from": get_header(hdrs, "From"),
        "subject": get_header(hdrs, "Subject"),
        "date": get_header(hdrs, "Date"),
        "snippet": data.get("snippet", ""),
    }


def list_inbox(max_results: int = 10, as_user: str | None = None) -> list[dict]:
    """List inbox messages with metadata.

    Two-step fetch: get message IDs, then metadata for each.
    """
    token = get_access_token(as_user=as_user)
    data = _gmail_get(
        "/messages",
        token,
        params={"q": "in:inbox", "maxResults": max_results},
    )
    message_refs = data.get("messages", [])

    messages = []
    for ref in message_refs:
        messages.append(_fetch_message_metadata(ref["id"], token))
    return messages


def read_message(msg_id: str, as_user: str | None = None) -> dict:
    """Read a message with full body extracted from MIME payload."""
    token = get_access_token(as_user=as_user)
    data = _gmail_get(f"/messages/{msg_id}", token, params={"format": "full"})
    hdrs = data.get("payload", {}).get("headers", [])

    body = extract_body(data["payload"])
    if not body:
        body = data.get("snippet", "")

    return {
        "id": data["id"],
        "thread_id": data["threadId"],
        "from": get_header(hdrs, "From"),
        "subject": get_header(hdrs, "Subject"),
        "date": get_header(hdrs, "Date"),
        "body": body,
        "snippet": data.get("snippet", ""),
    }


def send_message(
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
    bcc: str | None = None,
    as_user: str | None = None,
) -> dict:
    """Send an email via Gmail API.

    Builds RFC 2822 message, base64url encodes it, and POSTs to messages/send.
    """
    token = get_access_token(as_user=as_user)
    raw = build_raw_message(to, subject, body, cc=cc, bcc=bcc)
    resp = _gmail_post("/messages/send", token, {"raw": raw})
    return {
        "message_id": resp["id"],
        "thread_id": resp["threadId"],
    }


def search_messages(query: str, max_results: int = 10, as_user: str | None = None) -> list[dict]:
    """Search messages using Gmail query syntax.

    Same two-step fetch pattern as list_inbox.
    """
    token = get_access_token(as_user=as_user)
    data = _gmail_get(
        "/messages",
        token,
        params={"q": query, "maxResults": max_results},
    )
    message_refs = data.get("messages", [])

    messages = []
    for ref in message_refs:
        messages.append(_fetch_message_metadata(ref["id"], token))
    return messages


def handle_gmail_error(e: httpx.HTTPStatusError) -> None:
    """Translate Gmail API errors to user-friendly messages."""
    try:
        error_data = e.response.json()
        message = error_data.get("error", {}).get("message", str(e))
    except Exception:
        message = str(e)

    status = e.response.status_code
    if status == 401:
        crash(
            "Gmail authentication failed. Token may be expired or delegation misconfigured."
        )
    elif status == 403:
        fail(f"Gmail access denied: {message}")
    elif status == 404:
        fail(f"Message not found: {message}")
    elif status == 429:
        fail("Gmail rate limit exceeded. Try again later.")
    else:
        crash(f"Gmail API error ({status}): {message}")
