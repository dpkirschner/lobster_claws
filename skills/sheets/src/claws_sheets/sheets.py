"""Google Sheets API client module.

Handles token acquisition, spreadsheet listing via Drive API,
reading and writing cell values via Sheets API, creating spreadsheets,
and error handling. Data-only operations -- no formatting, charts, or formulas.
"""

import httpx
from claws_common.client import ClawsClient
from claws_common.google import google_request
from claws_common.output import crash, fail

AUTH_PORT = 8301
SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
DRIVE_READONLY_SCOPE = "https://www.googleapis.com/auth/drive.readonly"
SHEETS_BASE = "https://sheets.googleapis.com/v4/spreadsheets"
DRIVE_BASE = "https://www.googleapis.com/drive/v3"


def get_access_token(as_user: str | None = None) -> str:
    """Get Sheets access token from auth server.

    Requests both spreadsheets and drive.readonly scopes -- the latter
    is needed for listing spreadsheets via the Drive API.
    """
    client = ClawsClient(service="google-auth", port=AUTH_PORT)
    body: dict = {"scopes": [SHEETS_SCOPE, DRIVE_READONLY_SCOPE]}
    if as_user:
        body["subject"] = as_user
    resp = client.post_json("/token", body)
    return resp["access_token"]


def _token_fn(as_user: str | None = None):
    return lambda: get_access_token(as_user=as_user)


def _sheets_get(url: str, token_fn, params: dict | None = None) -> dict:
    """GET request to Sheets or Drive API (full URL)."""
    return google_request("GET", url, token_fn, params=params)


def _sheets_post(url: str, token_fn, body: dict) -> dict:
    """POST request to Sheets API (full URL)."""
    return google_request("POST", url, token_fn, json=body)


def _sheets_put(url: str, token_fn, body: dict, params: dict | None = None) -> dict:
    """PUT request to Sheets API (full URL)."""
    return google_request("PUT", url, token_fn, json=body, params=params)


def list_spreadsheets(
    max_results: int = 100, as_user: str | None = None
) -> list[dict]:
    """List spreadsheets via Drive API with mimeType filter.

    Args:
        max_results: Maximum number of spreadsheets to return (default 100).
        as_user: Act as this Google Workspace user (email).

    Returns:
        List of file metadata dicts with id, name, modifiedTime.
    """
    tfn = _token_fn(as_user)
    data = _sheets_get(
        f"{DRIVE_BASE}/files",
        tfn,
        params={
            "q": "mimeType='application/vnd.google-apps.spreadsheet'",
            "pageSize": max_results,
            "fields": "files(id,name,modifiedTime)",
        },
    )
    return data.get("files", [])


def read_values(
    spreadsheet_id: str, range_: str, as_user: str | None = None
) -> list[list]:
    """Read cell values from a spreadsheet range.

    Args:
        spreadsheet_id: The spreadsheet ID.
        range_: A1 notation range (e.g., "Sheet1!A1:B5").
        as_user: Act as this Google Workspace user (email).

    Returns:
        2D list of cell values, or empty list if range has no data.
    """
    tfn = _token_fn(as_user)
    data = _sheets_get(f"{SHEETS_BASE}/{spreadsheet_id}/values/{range_}", tfn)
    return data.get("values", [])


def write_values(
    spreadsheet_id: str,
    range_: str,
    values: list[list],
    as_user: str | None = None,
) -> dict:
    """Write cell values to a spreadsheet range.

    Args:
        spreadsheet_id: The spreadsheet ID.
        range_: A1 notation range (e.g., "Sheet1!A1:B2").
        values: 2D list of values to write.
        as_user: Act as this Google Workspace user (email).

    Returns:
        Update response dict with updatedCells, updatedRows, etc.
    """
    tfn = _token_fn(as_user)
    return _sheets_put(
        f"{SHEETS_BASE}/{spreadsheet_id}/values/{range_}",
        tfn,
        body={"range": range_, "values": values},
        params={"valueInputOption": "USER_ENTERED"},
    )


def create_spreadsheet(title: str, as_user: str | None = None) -> dict:
    """Create a new spreadsheet.

    Args:
        title: Title for the new spreadsheet.
        as_user: Act as this Google Workspace user (email).

    Returns:
        Dict with spreadsheetId and title.
    """
    tfn = _token_fn(as_user)
    data = _sheets_post(
        SHEETS_BASE,
        tfn,
        body={"properties": {"title": title}},
    )
    return {
        "spreadsheetId": data["spreadsheetId"],
        "title": data["properties"]["title"],
    }


def handle_sheets_error(e: httpx.HTTPStatusError) -> None:
    """Translate Sheets API errors to user-friendly messages."""
    try:
        error_data = e.response.json()
        message = error_data.get("error", {}).get("message", str(e))
    except Exception:
        message = str(e)

    status = e.response.status_code
    if status == 401:
        crash(
            "Sheets authentication failed. Token may be expired or delegation misconfigured."
        )
    elif status == 403:
        fail(f"Sheets access denied: {message}")
    elif status == 404:
        fail(f"Spreadsheet not found: {message}")
    elif status == 429:
        fail("Sheets rate limit exceeded. Try again later.")
    else:
        crash(f"Sheets API error ({status}): {message}")
