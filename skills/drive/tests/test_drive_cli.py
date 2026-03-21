"""Tests for Drive CLI entry point (subcommand routing)."""

from unittest.mock import patch

import httpx
import pytest

# --- list ---


def test_list_default(monkeypatch):
    """list with no args calls list_files(max_results=100) and outputs wrapped dict."""
    monkeypatch.setattr("sys.argv", ["claws-drive", "list"])
    mock_files = [{"id": "f1", "name": "report.txt"}]
    with (
        patch("claws_drive.cli.list_files", return_value=mock_files) as mock_list,
        patch("claws_drive.cli.result") as mock_result,
    ):
        from claws_drive.cli import main

        main()
        mock_list.assert_called_once_with(max_results=100, query=None, as_user=None)
        mock_result.assert_called_once_with({"files": mock_files, "result_count": 1})


def test_list_max(monkeypatch):
    """list --max 10 passes max_results=10."""
    monkeypatch.setattr("sys.argv", ["claws-drive", "list", "--max", "10"])
    with (
        patch("claws_drive.cli.list_files", return_value=[]) as mock_list,
        patch("claws_drive.cli.result"),
    ):
        from claws_drive.cli import main

        main()
        mock_list.assert_called_once_with(max_results=10, query=None, as_user=None)


def test_list_query(monkeypatch):
    """list --query passes query string."""
    monkeypatch.setattr("sys.argv", ["claws-drive", "list", "--query", "name contains 'report'"])
    with (
        patch("claws_drive.cli.list_files", return_value=[]) as mock_list,
        patch("claws_drive.cli.result"),
    ):
        from claws_drive.cli import main

        main()
        mock_list.assert_called_once_with(
            max_results=100, query="name contains 'report'", as_user=None
        )


def test_list_as_user(monkeypatch):
    """--as alice@x.com list passes as_user."""
    monkeypatch.setattr("sys.argv", ["claws-drive", "--as", "alice@x.com", "list"])
    with (
        patch("claws_drive.cli.list_files", return_value=[]) as mock_list,
        patch("claws_drive.cli.result"),
    ):
        from claws_drive.cli import main

        main()
        mock_list.assert_called_once_with(max_results=100, query=None, as_user="alice@x.com")


# --- download ---


def test_download_default(monkeypatch):
    """download FILE_ID calls download_file with default output path."""
    monkeypatch.setattr("sys.argv", ["claws-drive", "download", "file-123"])
    resp = {"file_id": "file-123", "path": "./file-123", "name": "report.pdf", "size": 1024}
    with (
        patch("claws_drive.cli.download_file", return_value=resp) as mock_dl,
        patch("claws_drive.cli.result") as mock_result,
    ):
        from claws_drive.cli import main

        main()
        mock_dl.assert_called_once_with(file_id="file-123", output_path="./file-123", as_user=None)
        mock_result.assert_called_once_with(resp)


def test_download_output(monkeypatch):
    """download FILE_ID -o /tmp/out.pdf passes output_path."""
    monkeypatch.setattr("sys.argv", ["claws-drive", "download", "file-123", "-o", "/tmp/out.pdf"])
    resp = {"file_id": "file-123", "path": "/tmp/out.pdf", "name": "report.pdf", "size": 1024}
    with (
        patch("claws_drive.cli.download_file", return_value=resp) as mock_dl,
        patch("claws_drive.cli.result"),
    ):
        from claws_drive.cli import main

        main()
        mock_dl.assert_called_once_with(
            file_id="file-123", output_path="/tmp/out.pdf", as_user=None
        )


# --- upload ---


def test_upload(monkeypatch):
    """upload /tmp/f.txt --name report.txt calls upload_file."""
    monkeypatch.setattr("sys.argv", ["claws-drive", "upload", "/tmp/f.txt", "--name", "report.txt"])
    resp = {"id": "new-id", "name": "report.txt", "mimeType": "text/plain"}
    with (
        patch("claws_drive.cli.upload_file", return_value=resp) as mock_up,
        patch("claws_drive.cli.result") as mock_result,
    ):
        from claws_drive.cli import main

        main()
        mock_up.assert_called_once_with(
            file_path="/tmp/f.txt", name="report.txt", folder_id=None, as_user=None
        )
        mock_result.assert_called_once_with(resp)


def test_upload_folder(monkeypatch):
    """upload with --folder passes folder_id."""
    monkeypatch.setattr(
        "sys.argv",
        ["claws-drive", "upload", "/tmp/f.txt", "--name", "r.txt", "--folder", "fold-1"],
    )
    resp = {"id": "new-id", "name": "r.txt", "mimeType": "text/plain"}
    with (
        patch("claws_drive.cli.upload_file", return_value=resp) as mock_up,
        patch("claws_drive.cli.result"),
    ):
        from claws_drive.cli import main

        main()
        mock_up.assert_called_once_with(
            file_path="/tmp/f.txt", name="r.txt", folder_id="fold-1", as_user=None
        )


# --- error handling ---


def test_http_error_routes_to_handler(monkeypatch):
    """HTTPStatusError triggers handle_drive_error()."""
    monkeypatch.setattr("sys.argv", ["claws-drive", "list"])
    error = httpx.HTTPStatusError(
        "err",
        request=httpx.Request("GET", "http://x"),
        response=httpx.Response(403),
    )
    with (
        patch("claws_drive.cli.list_files", side_effect=error),
        patch("claws_drive.cli.handle_drive_error") as mock_handler,
    ):
        from claws_drive.cli import main

        main()
        mock_handler.assert_called_once_with(error)


def test_connection_error(monkeypatch):
    """ConnectionError triggers crash()."""
    monkeypatch.setattr("sys.argv", ["claws-drive", "list"])
    with (
        patch("claws_drive.cli.list_files", side_effect=ConnectionError("cannot connect")),
        patch("claws_drive.cli.crash") as mock_crash,
    ):
        from claws_drive.cli import main

        main()
        mock_crash.assert_called_once_with("cannot connect")


def test_timeout_error(monkeypatch):
    """TimeoutError triggers crash()."""
    monkeypatch.setattr("sys.argv", ["claws-drive", "list"])
    with (
        patch("claws_drive.cli.list_files", side_effect=TimeoutError("timed out")),
        patch("claws_drive.cli.crash") as mock_crash,
    ):
        from claws_drive.cli import main

        main()
        mock_crash.assert_called_once_with("timed out")


# --- no subcommand ---


def test_no_subcommand(monkeypatch):
    """No subcommand raises SystemExit (argparse required=True)."""
    monkeypatch.setattr("sys.argv", ["claws-drive"])

    with pytest.raises(SystemExit):
        from claws_drive.cli import main

        main()
