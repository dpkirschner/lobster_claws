"""Google Docs API client module.

Handles token acquisition, document listing via Drive API, reading with
plain text extraction from structural JSON, creating with optional body
insertion, appending text, and error handling.
"""

import httpx
from claws_common.client import ClawsClient
from claws_common.output import crash, fail

AUTH_PORT = 8301
DOCS_SCOPE = "https://www.googleapis.com/auth/documents"
DRIVE_READONLY_SCOPE = "https://www.googleapis.com/auth/drive.readonly"
DOCS_BASE = "https://docs.googleapis.com/v1/documents"
DRIVE_BASE = "https://www.googleapis.com/drive/v3"


def get_access_token(as_user: str | None = None) -> str:
    """Get Docs access token from auth server.

    Requests both documents and drive.readonly scopes so the token
    can be used for listing (Drive API) and reading/writing (Docs API).
    """
    client = ClawsClient(service="google-auth", port=AUTH_PORT)
    body: dict = {"scopes": [DOCS_SCOPE, DRIVE_READONLY_SCOPE]}
    if as_user:
        body["subject"] = as_user
    resp = client.post_json("/token", body)
    return resp["access_token"]


def _docs_headers(token: str) -> dict:
    """Build authorization headers for Docs/Drive API calls."""
    return {"Authorization": f"Bearer {token}"}


def _docs_get(url: str, token: str, params: dict | None = None) -> dict:
    """GET request returning JSON response."""
    resp = httpx.get(
        url,
        params=params,
        headers=_docs_headers(token),
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


def _docs_post(url: str, token: str, body: dict) -> dict:
    """POST request returning JSON response."""
    resp = httpx.post(
        url,
        json=body,
        headers=_docs_headers(token),
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


def extract_text(document: dict) -> str:
    """Extract plain text from Google Docs structural JSON.

    Walks body.content -> paragraph -> elements -> textRun -> content
    and concatenates all text strings.
    """
    content = document.get("body", {}).get("content", [])
    parts: list[str] = []
    for element in content:
        paragraph = element.get("paragraph")
        if paragraph:
            for elem in paragraph.get("elements", []):
                text_run = elem.get("textRun")
                if text_run:
                    parts.append(text_run.get("content", ""))
    return "".join(parts)


def list_documents(max_results: int = 100, as_user: str | None = None) -> list[dict]:
    """List Google Docs documents via Drive API.

    Filters by mimeType='application/vnd.google-apps.document'.
    """
    token = get_access_token(as_user=as_user)
    params = {
        "q": "mimeType='application/vnd.google-apps.document'",
        "pageSize": max_results,
        "fields": "files(id,name,modifiedTime)",
    }
    data = _docs_get(f"{DRIVE_BASE}/files", token, params=params)
    return data.get("files", [])


def read_document(doc_id: str, as_user: str | None = None) -> dict:
    """Read a Google Doc and extract plain text.

    Returns dict with documentId, title, and extracted text.
    """
    token = get_access_token(as_user=as_user)
    doc = _docs_get(f"{DOCS_BASE}/{doc_id}", token)
    return {
        "documentId": doc["documentId"],
        "title": doc["title"],
        "text": extract_text(doc),
    }


def create_document(
    title: str, body: str | None = None, as_user: str | None = None
) -> dict:
    """Create a new Google Doc.

    If body is provided, creates blank doc then inserts text via batchUpdate.
    Returns dict with documentId and title.
    """
    token = get_access_token(as_user=as_user)
    doc = _docs_post(DOCS_BASE, token, {"title": title})
    doc_id = doc["documentId"]

    if body:
        _docs_post(
            f"{DOCS_BASE}/{doc_id}:batchUpdate",
            token,
            {
                "requests": [
                    {
                        "insertText": {
                            "text": body,
                            "endOfSegmentLocation": {},
                        }
                    }
                ]
            },
        )

    return {"documentId": doc_id, "title": doc["title"]}


def append_text(doc_id: str, text: str, as_user: str | None = None) -> dict:
    """Append text to an existing Google Doc via batchUpdate.

    Uses InsertTextRequest with endOfSegmentLocation to append at the end.
    """
    token = get_access_token(as_user=as_user)
    return _docs_post(
        f"{DOCS_BASE}/{doc_id}:batchUpdate",
        token,
        {
            "requests": [
                {
                    "insertText": {
                        "text": text,
                        "endOfSegmentLocation": {},
                    }
                }
            ]
        },
    )


def handle_docs_error(e: httpx.HTTPStatusError) -> None:
    """Translate Docs API errors to user-friendly messages."""
    try:
        error_data = e.response.json()
        message = error_data.get("error", {}).get("message", str(e))
    except Exception:
        message = str(e)

    status = e.response.status_code
    if status == 401:
        crash(
            "Docs authentication failed. Token may be expired or delegation misconfigured."
        )
    elif status == 403:
        fail(f"Docs access denied: {message}")
    elif status == 404:
        fail(f"Document not found: {message}")
    elif status == 429:
        fail("Docs rate limit exceeded. Try again later.")
    else:
        crash(f"Docs API error ({status}): {message}")
