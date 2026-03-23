"""Tests for Sheets CLI entry point (subcommand routing)."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

# --- list ---


def test_list_default(monkeypatch):
    """list with no args calls list_spreadsheets(max_results=100) and outputs wrapped dict."""
    monkeypatch.setattr("sys.argv", ["claws-sheets", "list"])
    mock_files = [{"id": "s1", "name": "Budget"}]

    with (
        patch("claws_sheets.cli.list_spreadsheets", return_value=mock_files) as mock_list,
        patch("claws_sheets.cli.result") as mock_result,
    ):
        from claws_sheets.cli import main

        main()
        mock_list.assert_called_once_with(max_results=100, as_user=None)
        mock_result.assert_called_once_with({"spreadsheets": mock_files, "result_count": 1})


def test_list_max(monkeypatch):
    """list --max 20 passes max_results=20."""
    monkeypatch.setattr("sys.argv", ["claws-sheets", "list", "--max", "20"])

    with (
        patch("claws_sheets.cli.list_spreadsheets", return_value=[]) as mock_list,
        patch("claws_sheets.cli.result"),
    ):
        from claws_sheets.cli import main

        main()
        mock_list.assert_called_once_with(max_results=20, as_user=None)


# --- read ---


def test_read(monkeypatch):
    """read SPREADSHEET_ID RANGE calls read_values and outputs values."""
    monkeypatch.setattr("sys.argv", ["claws-sheets", "read", "sheet-123", "Sheet1!A1:B5"])
    mock_values = [["a", "b"], ["c", "d"]]

    with (
        patch("claws_sheets.cli.read_values", return_value=mock_values) as mock_read,
        patch("claws_sheets.cli.result") as mock_result,
    ):
        from claws_sheets.cli import main

        main()
        mock_read.assert_called_once_with("sheet-123", "Sheet1!A1:B5", as_user=None)
        mock_result.assert_called_once_with({"values": mock_values, "row_count": 2})


# --- write ---


def test_write(monkeypatch):
    """write SPREADSHEET_ID RANGE --values JSON calls write_values with parsed values."""
    monkeypatch.setattr(
        "sys.argv",
        ["claws-sheets", "write", "sheet-123", "Sheet1!A1:B2", "--values", '[["a","b"],["c","d"]]'],
    )
    mock_resp = {"updatedCells": 4}

    with (
        patch("claws_sheets.cli.write_values", return_value=mock_resp) as mock_write,
        patch("claws_sheets.cli.result") as mock_result,
    ):
        from claws_sheets.cli import main

        main()
        mock_write.assert_called_once_with(
            "sheet-123", "Sheet1!A1:B2", [["a", "b"], ["c", "d"]], as_user=None
        )
        mock_result.assert_called_once_with(mock_resp)


def test_write_invalid_json(monkeypatch):
    """write with invalid --values JSON calls fail()."""
    monkeypatch.setattr(
        "sys.argv",
        ["claws-sheets", "write", "sheet-123", "Sheet1!A1", "--values", "not-json"],
    )

    with (
        patch("claws_sheets.cli.fail") as mock_fail,
    ):
        from claws_sheets.cli import main

        main()
        mock_fail.assert_called_once()
        assert "invalid json" in mock_fail.call_args[0][0].lower()


# --- create ---


def test_create(monkeypatch):
    """create --title NAME calls create_spreadsheet and outputs result."""
    monkeypatch.setattr("sys.argv", ["claws-sheets", "create", "--title", "My Sheet"])
    mock_resp = {"spreadsheetId": "new-1", "title": "My Sheet"}

    with (
        patch("claws_sheets.cli.create_spreadsheet", return_value=mock_resp) as mock_create,
        patch("claws_sheets.cli.result") as mock_result,
    ):
        from claws_sheets.cli import main

        main()
        mock_create.assert_called_once_with(title="My Sheet", as_user=None)
        mock_result.assert_called_once_with(mock_resp)


# --- --as flag ---


def test_list_with_as_flag(monkeypatch):
    """list --as alice@example.com passes as_user to list_spreadsheets."""
    monkeypatch.setattr("sys.argv", ["claws-sheets", "--as", "alice@example.com", "list"])
    mock_files = [{"id": "s1", "name": "Budget"}]

    with (
        patch("claws_sheets.cli.list_spreadsheets", return_value=mock_files) as mock_list,
        patch("claws_sheets.cli.result"),
    ):
        from claws_sheets.cli import main

        main()
        mock_list.assert_called_once_with(max_results=100, as_user="alice@example.com")


def test_read_with_as_flag(monkeypatch):
    """read --as alice@example.com passes as_user to read_values."""
    monkeypatch.setattr(
        "sys.argv", ["claws-sheets", "--as", "alice@example.com", "read", "sheet-123", "A1:B2"]
    )

    with (
        patch("claws_sheets.cli.read_values", return_value=[]) as mock_read,
        patch("claws_sheets.cli.result"),
    ):
        from claws_sheets.cli import main

        main()
        mock_read.assert_called_once_with("sheet-123", "A1:B2", as_user="alice@example.com")


def test_write_with_as_flag(monkeypatch):
    """write --as alice@example.com passes as_user to write_values."""
    monkeypatch.setattr(
        "sys.argv",
        [
            "claws-sheets",
            "--as",
            "alice@example.com",
            "write",
            "sheet-123",
            "A1",
            "--values",
            '[["x"]]',
        ],
    )

    with (
        patch("claws_sheets.cli.write_values", return_value={}) as mock_write,
        patch("claws_sheets.cli.result"),
    ):
        from claws_sheets.cli import main

        main()
        mock_write.assert_called_once_with("sheet-123", "A1", [["x"]], as_user="alice@example.com")


def test_create_with_as_flag(monkeypatch):
    """create --as alice@example.com passes as_user to create_spreadsheet."""
    monkeypatch.setattr(
        "sys.argv",
        ["claws-sheets", "--as", "alice@example.com", "create", "--title", "Test"],
    )
    mock_resp = {"spreadsheetId": "new-1", "title": "Test"}

    with (
        patch("claws_sheets.cli.create_spreadsheet", return_value=mock_resp) as mock_create,
        patch("claws_sheets.cli.result"),
    ):
        from claws_sheets.cli import main

        main()
        mock_create.assert_called_once_with(title="Test", as_user="alice@example.com")


# --- error handling ---


def test_connection_error(monkeypatch):
    """ConnectionError triggers crash()."""
    monkeypatch.setattr("sys.argv", ["claws-sheets", "list"])

    with (
        patch("claws_sheets.cli.list_spreadsheets", side_effect=ConnectionError("cannot connect")),
        patch("claws_sheets.cli.crash") as mock_crash,
    ):
        from claws_sheets.cli import main

        main()
        mock_crash.assert_called_once_with("cannot connect")


def test_timeout_error(monkeypatch):
    """TimeoutError triggers crash()."""
    monkeypatch.setattr("sys.argv", ["claws-sheets", "list"])

    with (
        patch("claws_sheets.cli.list_spreadsheets", side_effect=TimeoutError("timed out")),
        patch("claws_sheets.cli.crash") as mock_crash,
    ):
        from claws_sheets.cli import main

        main()
        mock_crash.assert_called_once_with("timed out")


def test_sheets_api_error(monkeypatch):
    """HTTPStatusError triggers handle_sheets_error()."""
    monkeypatch.setattr("sys.argv", ["claws-sheets", "list"])

    mock_response = MagicMock()
    mock_response.status_code = 401
    error = httpx.HTTPStatusError("auth failed", request=MagicMock(), response=mock_response)

    with (
        patch("claws_sheets.cli.list_spreadsheets", side_effect=error),
        patch("claws_sheets.cli.handle_sheets_error") as mock_handler,
    ):
        from claws_sheets.cli import main

        main()
        mock_handler.assert_called_once_with(error)


# --- no subcommand ---


def test_no_subcommand(monkeypatch):
    """No subcommand raises SystemExit (argparse required=True)."""
    monkeypatch.setattr("sys.argv", ["claws-sheets"])

    with pytest.raises(SystemExit):
        from claws_sheets.cli import main

        main()
