"""Google Drive API client module.

Handles token acquisition, file listing, downloading with export support
for Google Workspace documents, uploading with multipart/related encoding,
and error handling.
"""

import json
import mimetypes
import uuid

import httpx

from claws_common.client import ClawsClient
from claws_common.output import crash, fail

AUTH_PORT = 8301
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"
DRIVE_BASE = "https://www.googleapis.com/drive/v3"
DRIVE_UPLOAD_BASE = "https://www.googleapis.com/upload/drive/v3"

EXPORT_MIME_TYPES = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "application/pdf",
    "application/vnd.google-apps.drawing": "image/png",
}


def get_access_token(as_user: str | None = None) -> str:
    """Get Drive access token from auth server."""
    client = ClawsClient(service="google-auth", port=AUTH_PORT)
    body: dict = {"scopes": [DRIVE_SCOPE]}
    if as_user:
        body["subject"] = as_user
    resp = client.post_json("/token", body)
    return resp["access_token"]


def _drive_headers(token: str) -> dict:
    """Build authorization headers for Drive API calls."""
    return {"Authorization": f"Bearer {token}"}


def _drive_get(path: str, token: str, params: dict | None = None) -> dict:
    """GET request to Drive API, returns JSON response."""
    resp = httpx.get(
        f"{DRIVE_BASE}{path}",
        params=params,
        headers=_drive_headers(token),
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


def list_files(
    max_results: int = 100,
    query: str | None = None,
    as_user: str | None = None,
) -> list[dict]:
    """List files in Google Drive.

    Args:
        max_results: Maximum number of files to return (default 100).
        query: Optional Drive search query string.
        as_user: Act as this Google Workspace user (email).

    Returns:
        List of file metadata dicts.
    """
    token = get_access_token(as_user=as_user)
    params: dict = {
        "pageSize": max_results,
        "fields": "files(id,name,mimeType,modifiedTime,size,parents)",
        "orderBy": "modifiedTime desc",
    }
    if query:
        params["q"] = query
    data = _drive_get("/files", token, params=params)
    return data.get("files", [])


def download_file(
    file_id: str,
    output_path: str,
    as_user: str | None = None,
) -> dict:
    """Download a file from Google Drive.

    For regular files, downloads binary content via alt=media.
    For Google Workspace documents, exports to a compatible format.

    Args:
        file_id: The Drive file ID.
        output_path: Local path to write the downloaded file.
        as_user: Act as this Google Workspace user (email).

    Returns:
        Dict with file_id, path, name, and size.
    """
    token = get_access_token(as_user=as_user)

    # Step 1: Fetch metadata
    metadata = _drive_get(
        f"/files/{file_id}",
        token,
        params={"fields": "id,name,mimeType,size"},
    )

    mime_type = metadata.get("mimeType", "")
    headers = _drive_headers(token)

    # Step 2: Download or export
    if mime_type.startswith("application/vnd.google-apps."):
        # Google Workspace document — use export
        export_mime = EXPORT_MIME_TYPES.get(mime_type)
        if not export_mime:
            fail(f"Unsupported Google Workspace document type: {mime_type}")
            return {}  # fail() exits, but satisfy type checker
        resp = httpx.get(
            f"{DRIVE_BASE}/files/{file_id}/export",
            params={"mimeType": export_mime},
            headers=headers,
            timeout=120.0,
        )
    else:
        # Regular file — download binary
        resp = httpx.get(
            f"{DRIVE_BASE}/files/{file_id}",
            params={"alt": "media"},
            headers=headers,
            timeout=120.0,
        )

    resp.raise_for_status()

    # Step 3: Write to disk
    with open(output_path, "wb") as f:
        f.write(resp.content)

    return {
        "file_id": file_id,
        "path": output_path,
        "name": metadata["name"],
        "size": len(resp.content),
    }


def upload_file(
    file_path: str,
    name: str,
    folder_id: str | None = None,
    as_user: str | None = None,
) -> dict:
    """Upload a file to Google Drive using multipart/related.

    Args:
        file_path: Local path of the file to upload.
        name: Name for the file in Drive.
        folder_id: Optional parent folder ID.
        as_user: Act as this Google Workspace user (email).

    Returns:
        Dict with id, name, and mimeType of the created file.
    """
    token = get_access_token(as_user=as_user)

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

    metadata: dict = {"name": name}
    if folder_id:
        metadata["parents"] = [folder_id]

    boundary = uuid.uuid4().hex
    body = (
        f"--{boundary}\r\n"
        f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{json.dumps(metadata)}\r\n"
        f"--{boundary}\r\n"
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--".encode("utf-8")

    resp = httpx.post(
        f"{DRIVE_UPLOAD_BASE}/files?uploadType=multipart",
        content=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/related; boundary={boundary}",
        },
        timeout=120.0,
    )
    resp.raise_for_status()
    resp_data = resp.json()

    return {
        "id": resp_data["id"],
        "name": resp_data["name"],
        "mimeType": resp_data.get("mimeType", ""),
    }


def handle_drive_error(e: httpx.HTTPStatusError) -> None:
    """Translate Drive API errors to user-friendly messages."""
    try:
        error_data = e.response.json()
        message = error_data.get("error", {}).get("message", str(e))
    except Exception:
        message = str(e)

    status = e.response.status_code
    if status == 401:
        crash(
            "Drive authentication failed. Token may be expired or delegation misconfigured."
        )
    elif status == 403:
        fail(f"Drive access denied: {message}")
    elif status == 404:
        fail(f"File not found: {message}")
    elif status == 429:
        fail("Drive rate limit exceeded. Try again later.")
    else:
        crash(f"Drive API error ({status}): {message}")
