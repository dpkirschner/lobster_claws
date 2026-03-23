"""Tests for Tasks CLI entry point (subcommand routing)."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

# --- lists ---


def test_lists_default(monkeypatch):
    """lists calls list_task_lists(as_user=None) and outputs result."""
    monkeypatch.setattr("sys.argv", ["claws-tasks", "lists"])
    mock_lists = [{"id": "list-1", "title": "My Tasks"}]

    with (
        patch("claws_tasks.cli.list_task_lists", return_value=mock_lists) as mock_fn,
        patch("claws_tasks.cli.result") as mock_result,
    ):
        from claws_tasks.cli import main

        main()
        mock_fn.assert_called_once_with(as_user=None)
        mock_result.assert_called_once_with({"task_lists": mock_lists, "result_count": 1})


# --- list ---


def test_list_default(monkeypatch):
    """list calls list_tasks(tasklist='@default', as_user=None)."""
    monkeypatch.setattr("sys.argv", ["claws-tasks", "list"])
    mock_tasks = [{"id": "task-1", "title": "Buy milk"}]

    with (
        patch("claws_tasks.cli.list_tasks", return_value=mock_tasks) as mock_fn,
        patch("claws_tasks.cli.result") as mock_result,
    ):
        from claws_tasks.cli import main

        main()
        mock_fn.assert_called_once_with(tasklist="@default", max_results=100, as_user=None)
        mock_result.assert_called_once_with({"tasks": mock_tasks, "result_count": 1})


def test_list_with_list_flag(monkeypatch):
    """list --list LISTID calls list_tasks(tasklist='LISTID')."""
    monkeypatch.setattr("sys.argv", ["claws-tasks", "list", "--list", "my-list-id"])

    with (
        patch("claws_tasks.cli.list_tasks", return_value=[]) as mock_fn,
        patch("claws_tasks.cli.result"),
    ):
        from claws_tasks.cli import main

        main()
        mock_fn.assert_called_once_with(tasklist="my-list-id", max_results=100, as_user=None)


def test_list_with_max(monkeypatch):
    """list --max 5 passes max_results=5."""
    monkeypatch.setattr("sys.argv", ["claws-tasks", "list", "--max", "5"])

    with (
        patch("claws_tasks.cli.list_tasks", return_value=[]) as mock_fn,
        patch("claws_tasks.cli.result"),
    ):
        from claws_tasks.cli import main

        main()
        mock_fn.assert_called_once_with(tasklist="@default", max_results=5, as_user=None)


# --- create ---


def test_create_default(monkeypatch):
    """create --title 'Buy milk' creates task in @default list."""
    monkeypatch.setattr("sys.argv", ["claws-tasks", "create", "--title", "Buy milk"])
    mock_task = {"id": "new-task", "title": "Buy milk"}

    with (
        patch("claws_tasks.cli.create_task", return_value=mock_task) as mock_fn,
        patch("claws_tasks.cli.result") as mock_result,
    ):
        from claws_tasks.cli import main

        main()
        mock_fn.assert_called_once_with(
            tasklist="@default", title="Buy milk", notes=None, as_user=None
        )
        mock_result.assert_called_once_with(mock_task)


def test_create_with_list_and_notes(monkeypatch):
    """create --title 'Buy milk' --list LISTID --notes 'From store' passes all args."""
    monkeypatch.setattr(
        "sys.argv",
        ["claws-tasks", "create", "--title", "Buy milk",
         "--list", "my-list", "--notes", "From store"],
    )
    mock_task = {"id": "new-task", "title": "Buy milk", "notes": "From store"}

    with (
        patch("claws_tasks.cli.create_task", return_value=mock_task) as mock_fn,
        patch("claws_tasks.cli.result"),
    ):
        from claws_tasks.cli import main

        main()
        mock_fn.assert_called_once_with(
            tasklist="my-list", title="Buy milk", notes="From store", as_user=None
        )


# --- complete ---


def test_complete_default(monkeypatch):
    """complete TASKID completes task in @default list."""
    monkeypatch.setattr("sys.argv", ["claws-tasks", "complete", "task-123"])
    mock_task = {"id": "task-123", "status": "completed"}

    with (
        patch("claws_tasks.cli.complete_task", return_value=mock_task) as mock_fn,
        patch("claws_tasks.cli.result") as mock_result,
    ):
        from claws_tasks.cli import main

        main()
        mock_fn.assert_called_once_with(tasklist="@default", task_id="task-123", as_user=None)
        mock_result.assert_called_once_with(mock_task)


def test_complete_with_list(monkeypatch):
    """complete TASKID --list LISTID uses specified list."""
    monkeypatch.setattr("sys.argv", ["claws-tasks", "complete", "task-123", "--list", "my-list"])
    mock_task = {"id": "task-123", "status": "completed"}

    with (
        patch("claws_tasks.cli.complete_task", return_value=mock_task) as mock_fn,
        patch("claws_tasks.cli.result"),
    ):
        from claws_tasks.cli import main

        main()
        mock_fn.assert_called_once_with(tasklist="my-list", task_id="task-123", as_user=None)


# --- update ---


def test_update_title(monkeypatch):
    """update TASKID --title 'New title' calls update_task with title."""
    monkeypatch.setattr("sys.argv", ["claws-tasks", "update", "task-123", "--title", "New title"])
    mock_task = {"id": "task-123", "title": "New title"}

    with (
        patch("claws_tasks.cli.update_task", return_value=mock_task) as mock_fn,
        patch("claws_tasks.cli.result") as mock_result,
    ):
        from claws_tasks.cli import main

        main()
        mock_fn.assert_called_once_with(
            tasklist="@default", task_id="task-123", title="New title", notes=None, as_user=None
        )
        mock_result.assert_called_once_with(mock_task)


# --- delete ---


def test_delete_default(monkeypatch):
    """delete TASKID deletes task from @default list."""
    monkeypatch.setattr("sys.argv", ["claws-tasks", "delete", "task-123"])

    with (
        patch("claws_tasks.cli.delete_task", return_value=None) as mock_fn,
        patch("claws_tasks.cli.result") as mock_result,
    ):
        from claws_tasks.cli import main

        main()
        mock_fn.assert_called_once_with(tasklist="@default", task_id="task-123", as_user=None)
        mock_result.assert_called_once_with({"deleted": True})


def test_delete_with_list(monkeypatch):
    """delete TASKID --list LISTID uses specified list."""
    monkeypatch.setattr("sys.argv", ["claws-tasks", "delete", "task-123", "--list", "my-list"])

    with (
        patch("claws_tasks.cli.delete_task", return_value=None) as mock_fn,
        patch("claws_tasks.cli.result"),
    ):
        from claws_tasks.cli import main

        main()
        mock_fn.assert_called_once_with(tasklist="my-list", task_id="task-123", as_user=None)


# --- --as flag ---


def test_lists_with_as_flag(monkeypatch):
    """lists --as alice@example.com passes as_user to list_task_lists."""
    monkeypatch.setattr("sys.argv", ["claws-tasks", "--as", "alice@example.com", "lists"])

    with (
        patch("claws_tasks.cli.list_task_lists", return_value=[]) as mock_fn,
        patch("claws_tasks.cli.result"),
    ):
        from claws_tasks.cli import main

        main()
        mock_fn.assert_called_once_with(as_user="alice@example.com")


def test_list_with_as_flag(monkeypatch):
    """list --as alice@example.com passes as_user to list_tasks."""
    monkeypatch.setattr("sys.argv", ["claws-tasks", "--as", "alice@example.com", "list"])

    with (
        patch("claws_tasks.cli.list_tasks", return_value=[]) as mock_fn,
        patch("claws_tasks.cli.result"),
    ):
        from claws_tasks.cli import main

        main()
        mock_fn.assert_called_once_with(
            tasklist="@default", max_results=100, as_user="alice@example.com"
        )


def test_create_with_as_flag(monkeypatch):
    """create --as alice@example.com passes as_user to create_task."""
    monkeypatch.setattr(
        "sys.argv",
        ["claws-tasks", "--as", "alice@example.com", "create", "--title", "Test"],
    )

    with (
        patch("claws_tasks.cli.create_task", return_value={}) as mock_fn,
        patch("claws_tasks.cli.result"),
    ):
        from claws_tasks.cli import main

        main()
        mock_fn.assert_called_once_with(
            tasklist="@default", title="Test", notes=None, as_user="alice@example.com"
        )


def test_complete_with_as_flag(monkeypatch):
    """complete --as alice@example.com passes as_user to complete_task."""
    monkeypatch.setattr(
        "sys.argv",
        ["claws-tasks", "--as", "alice@example.com", "complete", "task-1"],
    )

    with (
        patch("claws_tasks.cli.complete_task", return_value={}) as mock_fn,
        patch("claws_tasks.cli.result"),
    ):
        from claws_tasks.cli import main

        main()
        mock_fn.assert_called_once_with(
            tasklist="@default", task_id="task-1", as_user="alice@example.com"
        )


def test_delete_with_as_flag(monkeypatch):
    """delete --as alice@example.com passes as_user to delete_task."""
    monkeypatch.setattr(
        "sys.argv",
        ["claws-tasks", "--as", "alice@example.com", "delete", "task-1"],
    )

    with (
        patch("claws_tasks.cli.delete_task", return_value=None) as mock_fn,
        patch("claws_tasks.cli.result"),
    ):
        from claws_tasks.cli import main

        main()
        mock_fn.assert_called_once_with(
            tasklist="@default", task_id="task-1", as_user="alice@example.com"
        )


# --- error handling ---


def test_connection_error(monkeypatch):
    """ConnectionError triggers crash()."""
    monkeypatch.setattr("sys.argv", ["claws-tasks", "lists"])

    with (
        patch("claws_tasks.cli.list_task_lists", side_effect=ConnectionError("cannot connect")),
        patch("claws_tasks.cli.crash") as mock_crash,
    ):
        from claws_tasks.cli import main

        main()
        mock_crash.assert_called_once_with("cannot connect")


def test_timeout_error(monkeypatch):
    """TimeoutError triggers crash()."""
    monkeypatch.setattr("sys.argv", ["claws-tasks", "lists"])

    with (
        patch("claws_tasks.cli.list_task_lists", side_effect=TimeoutError("timed out")),
        patch("claws_tasks.cli.crash") as mock_crash,
    ):
        from claws_tasks.cli import main

        main()
        mock_crash.assert_called_once_with("timed out")


def test_http_status_error(monkeypatch):
    """HTTPStatusError triggers handle_tasks_error()."""
    monkeypatch.setattr("sys.argv", ["claws-tasks", "lists"])

    mock_response = MagicMock()
    mock_response.status_code = 401
    error = httpx.HTTPStatusError("auth failed", request=MagicMock(), response=mock_response)

    with (
        patch("claws_tasks.cli.list_task_lists", side_effect=error),
        patch("claws_tasks.cli.handle_tasks_error") as mock_handler,
    ):
        from claws_tasks.cli import main

        main()
        mock_handler.assert_called_once_with(error)


# --- no subcommand ---


def test_no_subcommand(monkeypatch):
    """No subcommand raises SystemExit (argparse required=True)."""
    monkeypatch.setattr("sys.argv", ["claws-tasks"])

    with pytest.raises(SystemExit):
        from claws_tasks.cli import main

        main()
