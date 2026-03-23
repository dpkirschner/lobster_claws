"""Tests for Google Docs CLI entry point (subcommand routing)."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

# --- list ---


def test_list_default(monkeypatch):
    """list with no args calls list_documents(max_results=100) and outputs wrapped dict."""
    monkeypatch.setattr("sys.argv", ["claws-docs", "list"])
    mock_docs = [{"id": "doc1", "name": "My Doc"}]

    with (
        patch("claws_docs.cli.list_documents", return_value=mock_docs) as mock_list,
        patch("claws_docs.cli.result") as mock_result,
    ):
        from claws_docs.cli import main

        main()
        mock_list.assert_called_once_with(max_results=100, as_user=None)
        mock_result.assert_called_once_with({"documents": mock_docs, "result_count": 1})


def test_list_max(monkeypatch):
    """list --max 20 passes max_results=20."""
    monkeypatch.setattr("sys.argv", ["claws-docs", "list", "--max", "20"])

    with (
        patch("claws_docs.cli.list_documents", return_value=[]) as mock_list,
        patch("claws_docs.cli.result"),
    ):
        from claws_docs.cli import main

        main()
        mock_list.assert_called_once_with(max_results=20, as_user=None)


# --- read ---


def test_read(monkeypatch):
    """read <doc_id> calls read_document and outputs the returned dict."""
    monkeypatch.setattr("sys.argv", ["claws-docs", "read", "doc-123"])
    doc = {"documentId": "doc-123", "title": "Test", "text": "Hello"}

    with (
        patch("claws_docs.cli.read_document", return_value=doc) as mock_read,
        patch("claws_docs.cli.result") as mock_result,
    ):
        from claws_docs.cli import main

        main()
        mock_read.assert_called_once_with(doc_id="doc-123", as_user=None)
        mock_result.assert_called_once_with(doc)


# --- create ---


def test_create_without_body(monkeypatch):
    """create --title 'My Doc' calls create_document with body=None."""
    monkeypatch.setattr("sys.argv", ["claws-docs", "create", "--title", "My Doc"])
    resp = {"documentId": "new-1", "title": "My Doc"}

    with (
        patch("claws_docs.cli.create_document", return_value=resp) as mock_create,
        patch("claws_docs.cli.result") as mock_result,
    ):
        from claws_docs.cli import main

        main()
        mock_create.assert_called_once_with(title="My Doc", body=None, as_user=None)
        mock_result.assert_called_once_with(resp)


def test_create_with_body(monkeypatch):
    """create --title 'My Doc' --body 'Hello world' passes body through."""
    monkeypatch.setattr(
        "sys.argv",
        ["claws-docs", "create", "--title", "My Doc", "--body", "Hello world"],
    )
    resp = {"documentId": "new-2", "title": "My Doc"}

    with (
        patch("claws_docs.cli.create_document", return_value=resp) as mock_create,
        patch("claws_docs.cli.result"),
    ):
        from claws_docs.cli import main

        main()
        mock_create.assert_called_once_with(
            title="My Doc", body="Hello world", as_user=None
        )


# --- append ---


def test_append(monkeypatch):
    """append <doc_id> --body 'More text' calls append_text."""
    monkeypatch.setattr(
        "sys.argv", ["claws-docs", "append", "doc-123", "--body", "More text"]
    )
    resp = {"replies": []}

    with (
        patch("claws_docs.cli.append_text", return_value=resp) as mock_append,
        patch("claws_docs.cli.result") as mock_result,
    ):
        from claws_docs.cli import main

        main()
        mock_append.assert_called_once_with(
            doc_id="doc-123", text="More text", as_user=None
        )
        mock_result.assert_called_once_with(resp)


# --- --as flag ---


def test_list_with_as_flag(monkeypatch):
    """list --as alice@example.com passes as_user to list_documents."""
    monkeypatch.setattr(
        "sys.argv", ["claws-docs", "--as", "alice@example.com", "list"]
    )

    with (
        patch("claws_docs.cli.list_documents", return_value=[]) as mock_list,
        patch("claws_docs.cli.result"),
    ):
        from claws_docs.cli import main

        main()
        mock_list.assert_called_once_with(max_results=100, as_user="alice@example.com")


def test_read_with_as_flag(monkeypatch):
    """read --as alice@example.com passes as_user to read_document."""
    monkeypatch.setattr(
        "sys.argv", ["claws-docs", "--as", "alice@example.com", "read", "doc-123"]
    )
    doc = {"documentId": "doc-123", "title": "T", "text": ""}

    with (
        patch("claws_docs.cli.read_document", return_value=doc) as mock_read,
        patch("claws_docs.cli.result"),
    ):
        from claws_docs.cli import main

        main()
        mock_read.assert_called_once_with(doc_id="doc-123", as_user="alice@example.com")


def test_create_with_as_flag(monkeypatch):
    """create --as alice@example.com passes as_user to create_document."""
    monkeypatch.setattr(
        "sys.argv",
        ["claws-docs", "--as", "alice@example.com", "create", "--title", "T"],
    )
    resp = {"documentId": "new-1", "title": "T"}

    with (
        patch("claws_docs.cli.create_document", return_value=resp) as mock_create,
        patch("claws_docs.cli.result"),
    ):
        from claws_docs.cli import main

        main()
        mock_create.assert_called_once_with(
            title="T", body=None, as_user="alice@example.com"
        )


def test_append_with_as_flag(monkeypatch):
    """append --as alice@example.com passes as_user to append_text."""
    monkeypatch.setattr(
        "sys.argv",
        [
            "claws-docs",
            "--as",
            "alice@example.com",
            "append",
            "doc-123",
            "--body",
            "text",
        ],
    )
    resp = {"replies": []}

    with (
        patch("claws_docs.cli.append_text", return_value=resp) as mock_append,
        patch("claws_docs.cli.result"),
    ):
        from claws_docs.cli import main

        main()
        mock_append.assert_called_once_with(
            doc_id="doc-123", text="text", as_user="alice@example.com"
        )


# --- error handling ---


def test_connection_error(monkeypatch):
    """ConnectionError triggers crash()."""
    monkeypatch.setattr("sys.argv", ["claws-docs", "list"])

    with (
        patch(
            "claws_docs.cli.list_documents",
            side_effect=ConnectionError("cannot connect"),
        ),
        patch("claws_docs.cli.crash") as mock_crash,
    ):
        from claws_docs.cli import main

        main()
        mock_crash.assert_called_once_with("cannot connect")


def test_timeout_error(monkeypatch):
    """TimeoutError triggers crash()."""
    monkeypatch.setattr("sys.argv", ["claws-docs", "list"])

    with (
        patch(
            "claws_docs.cli.list_documents",
            side_effect=TimeoutError("timed out"),
        ),
        patch("claws_docs.cli.crash") as mock_crash,
    ):
        from claws_docs.cli import main

        main()
        mock_crash.assert_called_once_with("timed out")


def test_docs_api_error(monkeypatch):
    """HTTPStatusError triggers handle_docs_error()."""
    monkeypatch.setattr("sys.argv", ["claws-docs", "list"])

    mock_response = MagicMock()
    mock_response.status_code = 401
    error = httpx.HTTPStatusError(
        "auth failed", request=MagicMock(), response=mock_response
    )

    with (
        patch("claws_docs.cli.list_documents", side_effect=error),
        patch("claws_docs.cli.handle_docs_error") as mock_handler,
    ):
        from claws_docs.cli import main

        main()
        mock_handler.assert_called_once_with(error)


# --- no subcommand ---


def test_no_subcommand(monkeypatch):
    """No subcommand raises SystemExit (argparse required=True)."""
    monkeypatch.setattr("sys.argv", ["claws-docs"])

    with pytest.raises(SystemExit):
        from claws_docs.cli import main

        main()
