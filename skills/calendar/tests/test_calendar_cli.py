"""Tests for Calendar CLI entry point (subcommand routing and date flags)."""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import httpx
import pytest


# --- list: default ---


def test_list_default(monkeypatch):
    """list with no flags calls list_events with next-7-day range, max_results=25."""
    monkeypatch.setattr("sys.argv", ["claws-calendar", "list"])
    mock_events = [{"id": "e1", "summary": "Meeting"}]

    fake_today = date(2026, 3, 20)

    with (
        patch("claws_calendar.cli.date") as mock_date,
        patch("claws_calendar.cli.list_events", return_value=mock_events) as mock_list,
        patch("claws_calendar.cli.date_to_rfc3339", side_effect=lambda d, **kw: f"rfc:{d}:{kw.get('end_of_day', False)}") as mock_rfc,
        patch("claws_calendar.cli.result") as mock_result,
    ):
        mock_date.today.return_value = fake_today
        mock_date.fromisoformat = date.fromisoformat

        from claws_calendar.cli import main

        main()

        # Default: today to today+7
        mock_list.assert_called_once_with(
            time_min=f"rfc:{fake_today}:False",
            time_max=f"rfc:{fake_today + timedelta(days=7)}:False",
            max_results=25,
        )
        mock_result.assert_called_once_with({"events": mock_events, "result_count": 1})


# --- list: --today ---


def test_list_today(monkeypatch):
    """--today shows events from start of today to start of tomorrow."""
    monkeypatch.setattr("sys.argv", ["claws-calendar", "list", "--today"])

    fake_today = date(2026, 3, 20)

    with (
        patch("claws_calendar.cli.date") as mock_date,
        patch("claws_calendar.cli.list_events", return_value=[]) as mock_list,
        patch("claws_calendar.cli.date_to_rfc3339", side_effect=lambda d, **kw: f"rfc:{d}:{kw.get('end_of_day', False)}") as mock_rfc,
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
    monday = fake_today - timedelta(days=fake_today.weekday())  # 2026-03-16
    next_monday = monday + timedelta(days=7)  # 2026-03-23

    with (
        patch("claws_calendar.cli.date") as mock_date,
        patch("claws_calendar.cli.list_events", return_value=[]) as mock_list,
        patch("claws_calendar.cli.date_to_rfc3339", side_effect=lambda d, **kw: f"rfc:{d}:{kw.get('end_of_day', False)}") as mock_rfc,
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
    monkeypatch.setattr("sys.argv", ["claws-calendar", "list", "--from", "2026-03-20", "--to", "2026-03-25"])

    with (
        patch("claws_calendar.cli.date") as mock_date,
        patch("claws_calendar.cli.list_events", return_value=[]) as mock_list,
        patch("claws_calendar.cli.date_to_rfc3339", side_effect=lambda d, **kw: f"rfc:{d}:{kw.get('end_of_day', False)}") as mock_rfc,
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
    monkeypatch.setattr("sys.argv", ["claws-calendar", "list", "--from", "2026-03-20"])

    with (
        patch("claws_calendar.cli.date") as mock_date,
        patch("claws_calendar.cli.list_events", return_value=[]) as mock_list,
        patch("claws_calendar.cli.date_to_rfc3339", side_effect=lambda d, **kw: f"rfc:{d}:{kw.get('end_of_day', False)}") as mock_rfc,
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
    monkeypatch.setattr("sys.argv", ["claws-calendar", "list", "--to", "2026-03-25"])

    with (
        patch("claws_calendar.cli.date") as mock_date,
        patch("claws_calendar.cli.list_events", return_value=[]) as mock_list,
        patch("claws_calendar.cli.date_to_rfc3339", side_effect=lambda d, **kw: f"rfc:{d}:{kw.get('end_of_day', False)}") as mock_rfc,
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
        patch("claws_calendar.cli.date_to_rfc3339", side_effect=lambda d, **kw: f"rfc:{d}:{kw.get('end_of_day', False)}"),
        patch("claws_calendar.cli.result"),
    ):
        mock_date.today.return_value = date(2026, 3, 20)
        mock_date.fromisoformat = date.fromisoformat

        from claws_calendar.cli import main

        main()

        assert mock_list.call_args.kwargs["max_results"] == 5


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
    error = httpx.HTTPStatusError("not found", request=MagicMock(), response=mock_response)

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
        patch("claws_calendar.cli.get_event", side_effect=ConnectionError("cannot connect")),
        patch("claws_calendar.cli.crash") as mock_crash,
    ):
        from claws_calendar.cli import main

        main()
        mock_crash.assert_called_once_with("cannot connect")


def test_timeout_error(monkeypatch):
    """TimeoutError triggers crash()."""
    monkeypatch.setattr("sys.argv", ["claws-calendar", "get", "evt-001"])

    with (
        patch("claws_calendar.cli.get_event", side_effect=TimeoutError("timed out")),
        patch("claws_calendar.cli.crash") as mock_crash,
    ):
        from claws_calendar.cli import main

        main()
        mock_crash.assert_called_once_with("timed out")
