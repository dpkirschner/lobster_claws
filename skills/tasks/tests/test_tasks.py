"""Tests for Google Tasks API client module."""

from unittest.mock import MagicMock, patch

import pytest
from claws_tasks.tasks import (
    complete_task,
    create_task,
    delete_task,
    get_access_token,
    handle_tasks_error,
    list_task_lists,
    list_tasks,
    update_task,
)

# --- fixtures ---


@pytest.fixture
def mock_auth_client():
    """Patch ClawsClient in tasks module to return a test token."""
    with patch("claws_tasks.tasks.ClawsClient") as mock_cls:
        instance = MagicMock()
        instance.post_json.return_value = {
            "access_token": "test-token",
            "expires_in": 3300,
            "token_type": "Bearer",
        }
        mock_cls.return_value = instance
        yield instance


@pytest.fixture
def mock_google_request():
    """Patch google_request in tasks module."""
    with patch("claws_tasks.tasks.google_request") as mock:
        yield mock


# --- get_access_token ---


def test_get_access_token(mock_auth_client):
    """get_access_token returns the token string from auth server."""
    token = get_access_token()
    assert token == "test-token"
    mock_auth_client.post_json.assert_called_once_with(
        "/token", {"scopes": ["https://www.googleapis.com/auth/tasks"]}
    )


def test_get_access_token_with_subject(mock_auth_client):
    """get_access_token(as_user=...) includes subject in auth server POST body."""
    token = get_access_token(as_user="alice@example.com")
    assert token == "test-token"
    mock_auth_client.post_json.assert_called_once_with(
        "/token",
        {"scopes": ["https://www.googleapis.com/auth/tasks"], "subject": "alice@example.com"},
    )


def test_get_access_token_without_subject(mock_auth_client):
    """get_access_token() without as_user does NOT include subject in body."""
    token = get_access_token()
    assert token == "test-token"
    call_args = mock_auth_client.post_json.call_args
    body = call_args[0][1]
    assert "subject" not in body


# --- list_task_lists ---


def test_list_task_lists(mock_auth_client, mock_google_request):
    """list_task_lists returns list of task list dicts."""
    mock_google_request.return_value = {
        "items": [
            {"id": "list-1", "title": "My Tasks"},
            {"id": "list-2", "title": "Work"},
        ]
    }

    lists = list_task_lists()

    assert len(lists) == 2
    assert lists[0]["title"] == "My Tasks"
    assert lists[1]["id"] == "list-2"


def test_list_task_lists_empty(mock_auth_client, mock_google_request):
    """list_task_lists returns empty list when no task lists exist."""
    mock_google_request.return_value = {}

    lists = list_task_lists()
    assert lists == []


def test_list_task_lists_passes_subject(mock_auth_client, mock_google_request):
    """list_task_lists(as_user=...) threads as_user through to get_access_token."""
    mock_google_request.return_value = {"items": []}

    with patch("claws_tasks.tasks._token_fn") as mock_tfn:
        mock_tfn.return_value = lambda: "test-token"
        list_task_lists(as_user="test@example.com")
        mock_tfn.assert_called_once_with("test@example.com")


# --- list_tasks ---


def test_list_tasks(mock_auth_client, mock_google_request):
    """list_tasks returns list of task dicts for a given task list."""
    mock_google_request.return_value = {
        "items": [
            {"id": "task-1", "title": "Buy milk", "status": "needsAction"},
            {"id": "task-2", "title": "Walk dog", "status": "completed"},
        ]
    }

    tasks = list_tasks(tasklist="@default")

    assert len(tasks) == 2
    assert tasks[0]["title"] == "Buy milk"


def test_list_tasks_default_tasklist(mock_auth_client, mock_google_request):
    """list_tasks uses @default tasklist by default."""
    mock_google_request.return_value = {"items": []}

    list_tasks()

    call_args = mock_google_request.call_args
    url = call_args[0][1]  # second positional arg is the URL
    assert "/lists/@default/tasks" in url


def test_list_tasks_passes_subject(mock_auth_client, mock_google_request):
    """list_tasks(as_user=...) threads as_user through to get_access_token."""
    mock_google_request.return_value = {"items": []}

    with patch("claws_tasks.tasks._token_fn") as mock_tfn:
        mock_tfn.return_value = lambda: "test-token"
        list_tasks(as_user="test@example.com")
        mock_tfn.assert_called_once_with("test@example.com")


# --- create_task ---


def test_create_task(mock_auth_client, mock_google_request):
    """create_task posts title and returns created task dict."""
    mock_google_request.return_value = {"id": "new-task", "title": "Buy milk", "status": "needsAction"}

    task = create_task(tasklist="@default", title="Buy milk")

    assert task["id"] == "new-task"
    assert task["title"] == "Buy milk"
    call_args = mock_google_request.call_args
    assert call_args[0][0] == "POST"
    json_data = call_args.kwargs.get("json")
    assert json_data["title"] == "Buy milk"


def test_create_task_with_notes(mock_auth_client, mock_google_request):
    """create_task with notes includes notes in body."""
    mock_google_request.return_value = {"id": "new-task", "title": "Buy milk", "notes": "From store"}

    create_task(tasklist="@default", title="Buy milk", notes="From store")

    call_args = mock_google_request.call_args
    json_data = call_args.kwargs.get("json")
    assert json_data["notes"] == "From store"


def test_create_task_passes_subject(mock_auth_client, mock_google_request):
    """create_task(as_user=...) threads as_user through to get_access_token."""
    mock_google_request.return_value = {"id": "new-task", "title": "Buy milk"}

    with patch("claws_tasks.tasks._token_fn") as mock_tfn:
        mock_tfn.return_value = lambda: "test-token"
        create_task(tasklist="@default", title="Buy milk", as_user="test@example.com")
        mock_tfn.assert_called_once_with("test@example.com")


# --- complete_task ---


def test_complete_task(mock_auth_client, mock_google_request):
    """complete_task patches task with status completed."""
    mock_google_request.return_value = {"id": "task-1", "status": "completed"}

    task = complete_task(tasklist="@default", task_id="task-1")

    assert task["status"] == "completed"
    call_args = mock_google_request.call_args
    assert call_args[0][0] == "PATCH"
    json_data = call_args.kwargs.get("json")
    assert json_data == {"status": "completed"}


def test_complete_task_passes_subject(mock_auth_client, mock_google_request):
    """complete_task(as_user=...) threads as_user through to get_access_token."""
    mock_google_request.return_value = {"id": "task-1", "status": "completed"}

    with patch("claws_tasks.tasks._token_fn") as mock_tfn:
        mock_tfn.return_value = lambda: "test-token"
        complete_task(tasklist="@default", task_id="task-1", as_user="test@example.com")
        mock_tfn.assert_called_once_with("test@example.com")


# --- update_task ---


def test_update_task_title(mock_auth_client, mock_google_request):
    """update_task with title patches title only."""
    mock_google_request.return_value = {"id": "task-1", "title": "New title"}

    task = update_task(tasklist="@default", task_id="task-1", title="New title")

    assert task["title"] == "New title"
    call_args = mock_google_request.call_args
    json_data = call_args.kwargs.get("json")
    assert json_data == {"title": "New title"}


def test_update_task_notes(mock_auth_client, mock_google_request):
    """update_task with notes patches notes only."""
    mock_google_request.return_value = {"id": "task-1", "notes": "Updated notes"}

    update_task(tasklist="@default", task_id="task-1", notes="Updated notes")

    call_args = mock_google_request.call_args
    json_data = call_args.kwargs.get("json")
    assert json_data == {"notes": "Updated notes"}


def test_update_task_both(mock_auth_client, mock_google_request):
    """update_task with title and notes patches both."""
    mock_google_request.return_value = {"id": "task-1", "title": "New", "notes": "Notes"}

    update_task(tasklist="@default", task_id="task-1", title="New", notes="Notes")

    call_args = mock_google_request.call_args
    json_data = call_args.kwargs.get("json")
    assert json_data == {"title": "New", "notes": "Notes"}


def test_update_task_passes_subject(mock_auth_client, mock_google_request):
    """update_task(as_user=...) threads as_user through to get_access_token."""
    mock_google_request.return_value = {"id": "task-1", "title": "New"}

    with patch("claws_tasks.tasks._token_fn") as mock_tfn:
        mock_tfn.return_value = lambda: "test-token"
        update_task(tasklist="@default", task_id="task-1", title="New", as_user="test@example.com")
        mock_tfn.assert_called_once_with("test@example.com")


# --- delete_task ---


def test_delete_task(mock_auth_client, mock_google_request):
    """delete_task sends DELETE request and returns None."""
    mock_google_request.return_value = MagicMock()

    result = delete_task(tasklist="@default", task_id="task-1")

    assert result is None
    call_args = mock_google_request.call_args
    assert call_args[0][0] == "DELETE"
    url = call_args[0][1]
    assert "/lists/@default/tasks/task-1" in url


def test_delete_task_passes_subject(mock_auth_client, mock_google_request):
    """delete_task(as_user=...) threads as_user through to get_access_token."""
    mock_google_request.return_value = MagicMock()

    with patch("claws_tasks.tasks._token_fn") as mock_tfn:
        mock_tfn.return_value = lambda: "test-token"
        delete_task(tasklist="@default", task_id="task-1", as_user="test@example.com")
        mock_tfn.assert_called_once_with("test@example.com")


# --- handle_tasks_error ---


def test_handle_tasks_error_401():
    """401 errors call crash() with auth failure message."""
    import httpx as real_httpx

    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.json.return_value = {
        "error": {"code": 401, "message": "Invalid Credentials"}
    }
    error = real_httpx.HTTPStatusError(
        "error", request=MagicMock(), response=mock_response
    )

    with patch("claws_tasks.tasks.crash") as mock_crash:
        handle_tasks_error(error)
        mock_crash.assert_called_once()
        assert "auth" in mock_crash.call_args[0][0].lower()


def test_handle_tasks_error_403():
    """403 errors call fail() with access denied message."""
    import httpx as real_httpx

    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.json.return_value = {
        "error": {"code": 403, "message": "Forbidden"}
    }
    error = real_httpx.HTTPStatusError(
        "error", request=MagicMock(), response=mock_response
    )

    with patch("claws_tasks.tasks.fail") as mock_fail:
        handle_tasks_error(error)
        mock_fail.assert_called_once()
        msg = mock_fail.call_args[0][0].lower()
        assert "denied" in msg or "forbidden" in msg


def test_handle_tasks_error_404():
    """404 errors call fail() with not found message."""
    import httpx as real_httpx

    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.json.return_value = {
        "error": {"code": 404, "message": "Not Found"}
    }
    error = real_httpx.HTTPStatusError(
        "error", request=MagicMock(), response=mock_response
    )

    with patch("claws_tasks.tasks.fail") as mock_fail:
        handle_tasks_error(error)
        mock_fail.assert_called_once()
        assert "not found" in mock_fail.call_args[0][0].lower()


def test_handle_tasks_error_429():
    """429 errors call fail() with rate limit message."""
    import httpx as real_httpx

    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.json.return_value = {
        "error": {"code": 429, "message": "Rate Limit Exceeded"}
    }
    error = real_httpx.HTTPStatusError(
        "error", request=MagicMock(), response=mock_response
    )

    with patch("claws_tasks.tasks.fail") as mock_fail:
        handle_tasks_error(error)
        mock_fail.assert_called_once()
        assert "rate limit" in mock_fail.call_args[0][0].lower()
