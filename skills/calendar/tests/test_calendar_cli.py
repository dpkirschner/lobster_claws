"""Tests for Calendar CLI entry point (subcommand routing and date flags)."""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import httpx


def _fake_rfc3339(d, *, end_of_day=False):
    """Fake date_to_rfc3339 that returns a predictable string."""
    return f"rfc:{d}:{end_of_day}"


# --- list: default ---


def test_list_default(monkeypatch):
    """list with no flags calls list_events with next-7-day range."""
    monkeypatch.setattr("sys.argv", ["claws-calendar", "list"])
    mock_events = [{"id": "e1", "summary": "Meeting"}]
    fake_today = date(2026, 3, 20)

    with (
        patch("claws_calendar.cli.date") as mock_date,
        patch("claws_calendar.cli.list_events", return_value=mock_events) as mock_list,
        patch("claws_calendar.cli.date_to_rfc3339", side_effect=_fake_rfc3339),
        patch("claws_calendar.cli.result") as mock_result,
    ):
        mock_date.today.return_value = fake_today
        mock_date.fromisoformat = date.fromisoformat

        from claws_calendar.cli import main

        main()

        mock_list.assert_called_once_with(
            time_min=f"rfc:{fake_today}:False",
            time_max=f"rfc:{fake_today + timedelta(days=7)}:False",
            max_results=25,
        )
        mock_result.assert_called_once_with(
            {"events": mock_events, "result_count": 1}
        )


# --- list: --today ---


def test_list_today(monkeypatch):
    """--today shows events from start of today to start of tomorrow."""
    monkeypatch.setattr("sys.argv", ["claws-calendar", "list", "--today"])
    fake_today = date(2026, 3, 20)

    with (
        patch("claws_calendar.cli.date") as mock_date,
        patch("claws_calendar.cli.list_events", return_value=[]) as mock_list,
        patch("claws_calendar.cli.date_to_rfc3339", side_effect=_fake_rfc3339),
        patch("claws_calendar.cli.result"),
    ):
        mock_date.today.return_value = fake_today
        mock_date.fromisoformat = date.fromisoformat

        from claws_calendar.cli import main

        main()

        mock_list.assert_called_once_with(
            time_min=f"rfc:{fake_today}:False",
            time_max=f"rfc:{fake_today + timedelta(days=1)}:False",
            max_results=25,
        )


# --- list: --week ---


def test_list_week(monkeypatch):
    """--week shows events from Monday of current week to next Monday."""
    monkeypatch.setattr("sys.argv", ["claws-calendar", "list", "--week"])

    # 2026-03-20 is a Friday (weekday=4)
    fake_today = date(2026, 3, 20)
    monday = fake_today - timedelta(days=fake_today.weekday())
    next_monday = monday + timedelta(days=7)

    with (
        patch("claws_calendar.cli.date") as mock_date,
        patch("claws_calendar.cli.list_events", return_value=[]) as mock_list,
        patch("claws_calendar.cli.date_to_rfc3339", side_effect=_fake_rfc3339),
        patch("claws_calendar.cli.result"),
    ):
        mock_date.today.return_value = fake_today
        mock_date.fromisoformat = date.fromisoformat

        from claws_calendar.cli import main

        main()

        mock_list.assert_called_once_with(
            time_min=f"rfc:{monday}:False",
            time_max=f"rfc:{next_monday}:False",
            max_results=25,
        )


# --- list: --from and --to ---


def test_list_from_to(monkeypatch):
    """--from and --to set both bounds."""
    monkeypatch.setattr(
        "sys.argv",
        ["claws-calendar", "list", "--from", "2026-03-20", "--to", "2026-03-25"],
    )

    with (
        patch("claws_calendar.cli.date") as mock_date,
        patch("claws_calendar.cli.list_events", return_value=[]) as mock_list,
        patch("claws_calendar.cli.date_to_rfc3339", side_effect=_fake_rfc3339),
        patch("claws_calendar.cli.result"),
    ):
        mock_date.today.return_value = date(2026, 3, 20)
        mock_date.fromisoformat = date.fromisoformat

        from claws_calendar.cli import main

        main()

        mock_list.assert_called_once_with(
            time_min=f"rfc:{date(2026, 3, 20)}:False",
            time_max=f"rfc:{date(2026, 3, 25)}:True",
            max_results=25,
        )


def test_list_from_only(monkeypatch):
    """--from only sets time_min, time_max is None."""
    monkeypatch.setattr(
        "sys.argv", ["claws-calendar", "list", "--from", "2026-03-20"]
    )

    with (
        patch("claws_calendar.cli.date") as mock_date,
        patch("claws_calendar.cli.list_events", return_value=[]) as mock_list,
        patch("claws_calendar.cli.date_to_rfc3339", side_effect=_fake_rfc3339),
        patch("claws_calendar.cli.result"),
    ):
        mock_date.today.return_value = date(2026, 3, 20)
        mock_date.fromisoformat = date.fromisoformat

        from claws_calendar.cli import main

        main()

        mock_list.assert_called_once_with(
            time_min=f"rfc:{date(2026, 3, 20)}:False",
            time_max=None,
            max_results=25,
        )


def test_list_to_only(monkeypatch):
    """--to only sets time_max, time_min is None."""
    monkeypatch.setattr(
        "sys.argv", ["claws-calendar", "list", "--to", "2026-03-25"]
    )

    with (
        patch("claws_calendar.cli.date") as mock_date,
        patch("claws_calendar.cli.list_events", return_value=[]) as mock_list,
        patch("claws_calendar.cli.date_to_rfc3339", side_effect=_fake_rfc3339),
        patch("claws_calendar.cli.result"),
    ):
        mock_date.today.return_value = date(2026, 3, 20)
        mock_date.fromisoformat = date.fromisoformat

        from claws_calendar.cli import main

        main()

        mock_list.assert_called_once_with(
            time_min=None,
            time_max=f"rfc:{date(2026, 3, 25)}:True",
            max_results=25,
        )


# --- list: --max ---


def test_list_max(monkeypatch):
    """--max 5 passes max_results=5."""
    monkeypatch.setattr("sys.argv", ["claws-calendar", "list", "--max", "5"])

    with (
        patch("claws_calendar.cli.date") as mock_date,
        patch("claws_calendar.cli.list_events", return_value=[]) as mock_list,
        patch("claws_calendar.cli.date_to_rfc3339", side_effect=_fake_rfc3339),
        patch("claws_calendar.cli.result"),
    ):
        mock_date.today.return_value = date(2026, 3, 20)
        mock_date.fromisoformat = date.fromisoformat

        from claws_calendar.cli import main

        main()

        assert mock_list.call_args.kwargs["max_results"] == 5


# --- --as flag ---


def test_list_with_as_flag(monkeypatch):
    """list --as bob@example.com passes as_user to list_events."""
    monkeypatch.setattr("sys.argv", ["claws-calendar", "--as", "bob@example.com", "list"])
    fake_today = date(2026, 3, 20)

    with (
        patch("claws_calendar.cli.date") as mock_date,
        patch("claws_calendar.cli.list_events", return_value=[]) as mock_list,
        patch("claws_calendar.cli.date_to_rfc3339", side_effect=_fake_rfc3339),
        patch("claws_calendar.cli.result"),
    ):
        mock_date.today.return_value = fake_today
        mock_date.fromisoformat = date.fromisoformat

        from claws_calendar.cli import main

        main()

        assert mock_list.call_args.kwargs["as_user"] == "bob@example.com"


def test_list_without_as_flag(monkeypatch):
    """list without --as passes as_user=None."""
    monkeypatch.setattr("sys.argv", ["claws-calendar", "list"])
    fake_today = date(2026, 3, 20)

    with (
        patch("claws_calendar.cli.date") as mock_date,
        patch("claws_calendar.cli.list_events", return_value=[]) as mock_list,
        patch("claws_calendar.cli.date_to_rfc3339", side_effect=_fake_rfc3339),
        patch("claws_calendar.cli.result"),
    ):
        mock_date.today.return_value = fake_today
        mock_date.fromisoformat = date.fromisoformat

        from claws_calendar.cli import main

        main()

        assert mock_list.call_args.kwargs["as_user"] is None


def test_get_with_as_flag(monkeypatch):
    """get --as bob@example.com passes as_user to get_event."""
    monkeypatch.setattr("sys.argv", ["claws-calendar", "--as", "bob@example.com", "get", "evt-001"])
    event = {"id": "evt-001", "summary": "Standup"}

    with (
        patch("claws_calendar.cli.get_event", return_value=event) as mock_get,
        patch("claws_calendar.cli.result"),
    ):
        from claws_calendar.cli import main

        main()
        mock_get.assert_called_once_with("evt-001", as_user="bob@example.com")


def test_create_with_as_flag(monkeypatch):
    """create --as bob@example.com passes as_user to create_event."""
    monkeypatch.setattr(
        "sys.argv",
        ["claws-calendar", "--as", "bob@example.com", "create", "--title", "Meeting",
         "--start", "2026-03-20T10:00:00", "--end", "2026-03-20T11:00:00"],
    )
    event = {"id": "new-001", "summary": "Meeting"}

    with (
        patch("claws_calendar.cli.create_event", return_value=event) as mock_create,
        patch("claws_calendar.cli.result"),
    ):
        from claws_calendar.cli import main

        main()
        assert mock_create.call_args.kwargs["as_user"] == "bob@example.com"


def test_update_with_as_flag(monkeypatch):
    """update --as bob@example.com passes as_user to update_event."""
    monkeypatch.setattr(
        "sys.argv",
        ["claws-calendar", "--as", "bob@example.com", "update", "evt-001", "--title", "New"],
    )
    event = {"id": "evt-001", "summary": "New"}

    with (
        patch("claws_calendar.cli.update_event", return_value=event) as mock_update,
        patch("claws_calendar.cli.result"),
    ):
        from claws_calendar.cli import main

        main()
        assert mock_update.call_args.kwargs["as_user"] == "bob@example.com"


def test_delete_with_as_flag(monkeypatch):
    """delete --as bob@example.com passes as_user to delete_event."""
    monkeypatch.setattr("sys.argv", ["claws-calendar", "--as", "bob@example.com", "delete", "evt-001"])
    resp = {"deleted": True, "event_id": "evt-001"}

    with (
        patch("claws_calendar.cli.delete_event", return_value=resp) as mock_delete,
        patch("claws_calendar.cli.result"),
    ):
        from claws_calendar.cli import main

        main()
        mock_delete.assert_called_once_with("evt-001", as_user="bob@example.com")


# --- get ---


def test_get_event(monkeypatch):
    """get <id> calls get_event and outputs the result directly."""
    monkeypatch.setattr("sys.argv", ["claws-calendar", "get", "evt-001"])
    event = {"id": "evt-001", "summary": "Standup"}

    with (
        patch("claws_calendar.cli.get_event", return_value=event) as mock_get,
        patch("claws_calendar.cli.result") as mock_result,
    ):
        from claws_calendar.cli import main

        main()
        mock_get.assert_called_once_with("evt-001")
        mock_result.assert_called_once_with(event)


# --- error handling ---


def test_http_error_handling(monkeypatch):
    """HTTPStatusError triggers handle_calendar_error."""
    monkeypatch.setattr("sys.argv", ["claws-calendar", "get", "evt-bad"])

    mock_response = MagicMock()
    mock_response.status_code = 404
    error = httpx.HTTPStatusError(
        "not found", request=MagicMock(), response=mock_response
    )

    with (
        patch("claws_calendar.cli.get_event", side_effect=error),
        patch("claws_calendar.cli.handle_calendar_error") as mock_handler,
    ):
        from claws_calendar.cli import main

        main()
        mock_handler.assert_called_once_with(error)


def test_connection_error(monkeypatch):
    """ConnectionError triggers crash()."""
    monkeypatch.setattr("sys.argv", ["claws-calendar", "get", "evt-001"])

    with (
        patch(
            "claws_calendar.cli.get_event",
            side_effect=ConnectionError("cannot connect"),
        ),
        patch("claws_calendar.cli.crash") as mock_crash,
    ):
        from claws_calendar.cli import main

        main()
        mock_crash.assert_called_once_with("cannot connect")


def test_timeout_error(monkeypatch):
    """TimeoutError triggers crash()."""
    monkeypatch.setattr("sys.argv", ["claws-calendar", "get", "evt-001"])

    with (
        patch(
            "claws_calendar.cli.get_event",
            side_effect=TimeoutError("timed out"),
        ),
        patch("claws_calendar.cli.crash") as mock_crash,
    ):
        from claws_calendar.cli import main

        main()
        mock_crash.assert_called_once_with("timed out")


# --- create: minimal ---


def test_create_minimal(monkeypatch):
    """create with --title, --start, --end calls create_event with required args only."""
    monkeypatch.setattr(
        "sys.argv",
        [
            "claws-calendar",
            "create",
            "--title",
            "Meeting",
            "--start",
            "2026-03-20T10:00:00",
            "--end",
            "2026-03-20T11:00:00",
        ],
    )
    event = {"id": "new-001", "summary": "Meeting"}

    with (
        patch(
            "claws_calendar.cli.create_event", return_value=event
        ) as mock_create,
        patch("claws_calendar.cli.result") as mock_result,
    ):
        from claws_calendar.cli import main

        main()

        mock_create.assert_called_once_with(
            title="Meeting",
            start="2026-03-20T10:00:00",
            end="2026-03-20T11:00:00",
            location=None,
            description=None,
            attendees=None,
        )
        mock_result.assert_called_once_with(event)


# --- create: full ---


def test_create_full(monkeypatch):
    """create with all flags passes all fields including split attendees."""
    monkeypatch.setattr(
        "sys.argv",
        [
            "claws-calendar",
            "create",
            "--title",
            "Team Sync",
            "--start",
            "2026-03-20T10:00:00",
            "--end",
            "2026-03-20T11:00:00",
            "--location",
            "Room 42",
            "--description",
            "Weekly sync",
            "--attendees",
            "a@b.com,c@d.com",
        ],
    )
    event = {"id": "new-002", "summary": "Team Sync"}

    with (
        patch(
            "claws_calendar.cli.create_event", return_value=event
        ) as mock_create,
        patch("claws_calendar.cli.result") as mock_result,
    ):
        from claws_calendar.cli import main

        main()

        mock_create.assert_called_once_with(
            title="Team Sync",
            start="2026-03-20T10:00:00",
            end="2026-03-20T11:00:00",
            location="Room 42",
            description="Weekly sync",
            attendees=["a@b.com", "c@d.com"],
        )
        mock_result.assert_called_once_with(event)


# --- create: all-day ---


def test_create_all_day(monkeypatch):
    """create with --date and --all-day computes end as date+1."""
    monkeypatch.setattr(
        "sys.argv",
        [
            "claws-calendar",
            "create",
            "--title",
            "Holiday",
            "--date",
            "2026-03-20",
            "--all-day",
        ],
    )
    event = {"id": "new-003", "summary": "Holiday"}

    with (
        patch(
            "claws_calendar.cli.create_event", return_value=event
        ) as mock_create,
        patch("claws_calendar.cli.result") as mock_result,
    ):
        from claws_calendar.cli import main

        main()

        mock_create.assert_called_once_with(
            title="Holiday",
            start="2026-03-20",
            end="2026-03-21",
            all_day=True,
            location=None,
            description=None,
            attendees=None,
        )
        mock_result.assert_called_once_with(event)


# --- update: title only ---


def test_update_title(monkeypatch):
    """update with --title calls update_event with title only."""
    monkeypatch.setattr(
        "sys.argv",
        ["claws-calendar", "update", "evt-001", "--title", "New Title"],
    )
    event = {"id": "evt-001", "summary": "New Title"}

    with (
        patch(
            "claws_calendar.cli.update_event", return_value=event
        ) as mock_update,
        patch("claws_calendar.cli.result") as mock_result,
    ):
        from claws_calendar.cli import main

        main()

        mock_update.assert_called_once_with(
            "evt-001",
            title="New Title",
            start=None,
            end=None,
            location=None,
            description=None,
            attendees=None,
        )
        mock_result.assert_called_once_with(event)


# --- update: multiple fields ---


def test_update_multiple_fields(monkeypatch):
    """update with multiple flags passes all fields."""
    monkeypatch.setattr(
        "sys.argv",
        [
            "claws-calendar",
            "update",
            "evt-002",
            "--title",
            "Updated",
            "--start",
            "2026-03-21T09:00:00",
            "--end",
            "2026-03-21T10:00:00",
            "--location",
            "Room 7",
            "--description",
            "New desc",
            "--attendees",
            "x@y.com",
        ],
    )
    event = {"id": "evt-002", "summary": "Updated"}

    with (
        patch(
            "claws_calendar.cli.update_event", return_value=event
        ) as mock_update,
        patch("claws_calendar.cli.result") as mock_result,
    ):
        from claws_calendar.cli import main

        main()

        mock_update.assert_called_once_with(
            "evt-002",
            title="Updated",
            start="2026-03-21T09:00:00",
            end="2026-03-21T10:00:00",
            location="Room 7",
            description="New desc",
            attendees=["x@y.com"],
        )
        mock_result.assert_called_once_with(event)


# --- delete ---


def test_delete(monkeypatch):
    """delete <id> calls delete_event and outputs result."""
    monkeypatch.setattr("sys.argv", ["claws-calendar", "delete", "evt-001"])
    resp = {"deleted": True, "event_id": "evt-001"}

    with (
        patch(
            "claws_calendar.cli.delete_event", return_value=resp
        ) as mock_delete,
        patch("claws_calendar.cli.result") as mock_result,
    ):
        from claws_calendar.cli import main

        main()

        mock_delete.assert_called_once_with("evt-001")
        mock_result.assert_called_once_with(resp)


# --- write error handling ---


def test_create_http_error(monkeypatch):
    """HTTPStatusError from create_event triggers handle_calendar_error."""
    monkeypatch.setattr(
        "sys.argv",
        [
            "claws-calendar",
            "create",
            "--title",
            "Bad",
            "--start",
            "2026-03-20T10:00:00",
            "--end",
            "2026-03-20T11:00:00",
        ],
    )

    mock_response = MagicMock()
    mock_response.status_code = 400
    error = httpx.HTTPStatusError(
        "bad request", request=MagicMock(), response=mock_response
    )

    with (
        patch("claws_calendar.cli.create_event", side_effect=error),
        patch("claws_calendar.cli.handle_calendar_error") as mock_handler,
    ):
        from claws_calendar.cli import main

        main()
        mock_handler.assert_called_once_with(error)


def test_update_http_error(monkeypatch):
    """HTTPStatusError from update_event triggers handle_calendar_error."""
    monkeypatch.setattr(
        "sys.argv",
        ["claws-calendar", "update", "evt-001", "--title", "Fail"],
    )

    mock_response = MagicMock()
    mock_response.status_code = 403
    error = httpx.HTTPStatusError(
        "forbidden", request=MagicMock(), response=mock_response
    )

    with (
        patch("claws_calendar.cli.update_event", side_effect=error),
        patch("claws_calendar.cli.handle_calendar_error") as mock_handler,
    ):
        from claws_calendar.cli import main

        main()
        mock_handler.assert_called_once_with(error)


def test_delete_http_error(monkeypatch):
    """HTTPStatusError from delete_event triggers handle_calendar_error."""
    monkeypatch.setattr("sys.argv", ["claws-calendar", "delete", "evt-bad"])

    mock_response = MagicMock()
    mock_response.status_code = 404
    error = httpx.HTTPStatusError(
        "not found", request=MagicMock(), response=mock_response
    )

    with (
        patch("claws_calendar.cli.delete_event", side_effect=error),
        patch("claws_calendar.cli.handle_calendar_error") as mock_handler,
    ):
        from claws_calendar.cli import main

        main()
        mock_handler.assert_called_once_with(error)
