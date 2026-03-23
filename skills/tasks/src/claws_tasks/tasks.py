"""Google Tasks API client module.

Handles token acquisition, task list management, task CRUD operations,
and error handling for the Google Tasks API.
"""

import httpx

from claws_common.client import ClawsClient
from claws_common.output import crash, fail

AUTH_PORT = 8301
TASKS_SCOPE = "https://www.googleapis.com/auth/tasks"
TASKS_BASE = "https://tasks.googleapis.com/tasks/v1"


def get_access_token(as_user: str | None = None) -> str:
    """Get Tasks access token from auth server."""
    client = ClawsClient(service="google-auth", port=8301)
    body: dict = {"scopes": [TASKS_SCOPE]}
    if as_user:
        body["subject"] = as_user
    resp = client.post_json("/token", body)
    return resp["access_token"]


def _tasks_headers(token: str) -> dict:
    """Build authorization headers for Tasks API calls."""
    return {"Authorization": f"Bearer {token}"}


def _tasks_get(path: str, token: str, params: dict | None = None) -> dict:
    """GET request to Tasks API."""
    resp = httpx.get(
        f"{TASKS_BASE}{path}",
        params=params,
        headers=_tasks_headers(token),
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


def _tasks_post(path: str, token: str, body: dict) -> dict:
    """POST request to Tasks API."""
    resp = httpx.post(
        f"{TASKS_BASE}{path}",
        json=body,
        headers=_tasks_headers(token),
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


def _tasks_patch(path: str, token: str, body: dict) -> dict:
    """PATCH request to Tasks API."""
    resp = httpx.patch(
        f"{TASKS_BASE}{path}",
        json=body,
        headers=_tasks_headers(token),
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


def _tasks_delete(path: str, token: str) -> None:
    """DELETE request to Tasks API."""
    resp = httpx.delete(
        f"{TASKS_BASE}{path}",
        headers=_tasks_headers(token),
        timeout=30.0,
    )
    resp.raise_for_status()


def list_task_lists(as_user: str | None = None) -> list[dict]:
    """List all task lists for the user."""
    token = get_access_token(as_user=as_user)
    data = _tasks_get("/users/@me/lists", token)
    return data.get("items", [])


def list_tasks(
    tasklist: str = "@default", max_results: int = 100, as_user: str | None = None
) -> list[dict]:
    """List tasks in a task list."""
    token = get_access_token(as_user=as_user)
    data = _tasks_get(
        f"/lists/{tasklist}/tasks",
        token,
        params={"maxResults": max_results},
    )
    return data.get("items", [])


def create_task(
    tasklist: str, title: str, notes: str | None = None, as_user: str | None = None
) -> dict:
    """Create a new task in a task list."""
    token = get_access_token(as_user=as_user)
    body: dict = {"title": title}
    if notes:
        body["notes"] = notes
    return _tasks_post(f"/lists/{tasklist}/tasks", token, body)


def complete_task(tasklist: str, task_id: str, as_user: str | None = None) -> dict:
    """Mark a task as completed."""
    token = get_access_token(as_user=as_user)
    return _tasks_patch(
        f"/lists/{tasklist}/tasks/{task_id}",
        token,
        {"status": "completed"},
    )


def update_task(
    tasklist: str,
    task_id: str,
    title: str | None = None,
    notes: str | None = None,
    as_user: str | None = None,
) -> dict:
    """Update a task's title and/or notes."""
    token = get_access_token(as_user=as_user)
    body: dict = {}
    if title is not None:
        body["title"] = title
    if notes is not None:
        body["notes"] = notes
    return _tasks_patch(f"/lists/{tasklist}/tasks/{task_id}", token, body)


def delete_task(tasklist: str, task_id: str, as_user: str | None = None) -> None:
    """Delete a task from a task list."""
    token = get_access_token(as_user=as_user)
    _tasks_delete(f"/lists/{tasklist}/tasks/{task_id}", token)


def handle_tasks_error(e: httpx.HTTPStatusError) -> None:
    """Translate Tasks API errors to user-friendly messages."""
    try:
        error_data = e.response.json()
        message = error_data.get("error", {}).get("message", str(e))
    except Exception:
        message = str(e)

    status = e.response.status_code
    if status == 401:
        crash(
            "Tasks authentication failed. Token may be expired or delegation misconfigured."
        )
    elif status == 403:
        fail(f"Tasks access denied: {message}")
    elif status == 404:
        fail(f"Task not found: {message}")
    elif status == 429:
        fail("Tasks rate limit exceeded. Try again later.")
    else:
        crash(f"Tasks API error ({status}): {message}")
