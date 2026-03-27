"""Tests for Gmail CLI entry point (subcommand routing)."""

from unittest.mock import MagicMock, patch

import httpx
import pytest


# --- inbox ---


def test_inbox_default(monkeypatch):
    """inbox with no args calls list_inbox(max_results=10) and outputs wrapped dict."""
    monkeypatch.setattr("sys.argv", ["claws-gmail", "inbox"])
    mock_messages = [{"id": "1", "subject": "Hello"}]

    with (
        patch("claws_gmail.cli.list_inbox", return_value=mock_messages) as mock_list,
        patch("claws_gmail.cli.result") as mock_result,
    ):
        from claws_gmail.cli import main

        main()
        mock_list.assert_called_once_with(max_results=10, as_user=None)
        mock_result.assert_called_once_with({"messages": mock_messages, "result_count": 1})


def test_inbox_max(monkeypatch):
    """inbox --max 5 passes max_results=5."""
    monkeypatch.setattr("sys.argv", ["claws-gmail", "inbox", "--max", "5"])

    with (
        patch("claws_gmail.cli.list_inbox", return_value=[]) as mock_list,
        patch("claws_gmail.cli.result"),
    ):
        from claws_gmail.cli import main

        main()
        mock_list.assert_called_once_with(max_results=5, as_user=None)


# --- read ---


def test_read(monkeypatch):
    """read <id> calls read_message and outputs the returned dict."""
    monkeypatch.setattr("sys.argv", ["claws-gmail", "read", "abc"])
    msg = {"id": "abc", "body": "Hello"}

    with (
        patch("claws_gmail.cli.read_message", return_value=msg) as mock_read,
        patch("claws_gmail.cli.result") as mock_result,
    ):
        from claws_gmail.cli import main

        main()
        mock_read.assert_called_once_with("abc", as_user=None)
        mock_result.assert_called_once_with(msg)


# --- send ---


def test_send_with_body_flag(monkeypatch):
    """send --to --subject --body sends with all args."""
    monkeypatch.setattr(
        "sys.argv",
        ["claws-gmail", "send", "--to", "bob@example.com", "--subject", "Hi", "--body", "Hello"],
    )
    resp = {"message_id": "m1", "thread_id": "t1"}

    with (
        patch("claws_gmail.cli.send_message", return_value=resp) as mock_send,
        patch("claws_gmail.cli.result") as mock_result,
    ):
        from claws_gmail.cli import main

        main()
        mock_send.assert_called_once_with(
            to="bob@example.com", subject="Hi", body="Hello", cc=None, bcc=None, as_user=None
        )
        mock_result.assert_called_once_with(resp)


def test_send_with_cc_bcc(monkeypatch):
    """send with --cc and --bcc passes them through."""
    monkeypatch.setattr(
        "sys.argv",
        [
            "claws-gmail",
            "send",
            "--to",
            "bob@example.com",
            "--subject",
            "Hi",
            "--body",
            "Hello",
            "--cc",
            "cc@x.com",
            "--bcc",
            "bcc@x.com",
        ],
    )

    with (
        patch("claws_gmail.cli.send_message", return_value={}) as mock_send,
        patch("claws_gmail.cli.result"),
    ):
        from claws_gmail.cli import main

        main()
        mock_send.assert_called_once_with(
            to="bob@example.com", subject="Hi", body="Hello", cc="cc@x.com", bcc="bcc@x.com", as_user=None
        )


def test_send_stdin_fallback(monkeypatch):
    """send without --body reads from stdin when not a TTY."""
    monkeypatch.setattr(
        "sys.argv",
        ["claws-gmail", "send", "--to", "bob@example.com", "--subject", "Hi"],
    )

    mock_stdin = MagicMock()
    mock_stdin.isatty.return_value = False
    mock_stdin.read.return_value = "Body from stdin"
    monkeypatch.setattr("sys.stdin", mock_stdin)

    with (
        patch("claws_gmail.cli.send_message", return_value={}) as mock_send,
        patch("claws_gmail.cli.result"),
    ):
        from claws_gmail.cli import main

        main()
        mock_send.assert_called_once_with(
            to="bob@example.com",
            subject="Hi",
            body="Body from stdin",
            cc=None,
            bcc=None,
            as_user=None,
        )


# --- search ---


def test_inbox_with_as_flag(monkeypatch):
    """inbox --as alice@example.com passes as_user to list_inbox."""
    monkeypatch.setattr("sys.argv", ["claws-gmail", "--as", "alice@example.com", "inbox"])
    mock_messages = [{"id": "1", "subject": "Hello"}]

    with (
        patch("claws_gmail.cli.list_inbox", return_value=mock_messages) as mock_list,
        patch("claws_gmail.cli.result"),
    ):
        from claws_gmail.cli import main

        main()
        mock_list.assert_called_once_with(max_results=10, as_user="alice@example.com")


def test_inbox_without_as_flag(monkeypatch):
    """inbox without --as passes as_user=None to list_inbox."""
    monkeypatch.setattr("sys.argv", ["claws-gmail", "inbox"])
    mock_messages = [{"id": "1", "subject": "Hello"}]

    with (
        patch("claws_gmail.cli.list_inbox", return_value=mock_messages) as mock_list,
        patch("claws_gmail.cli.result"),
    ):
        from claws_gmail.cli import main

        main()
        mock_list.assert_called_once_with(max_results=10, as_user=None)


def test_read_with_as_flag(monkeypatch):
    """read --as alice@example.com passes as_user to read_message."""
    monkeypatch.setattr("sys.argv", ["claws-gmail", "--as", "alice@example.com", "read", "abc"])
    msg = {"id": "abc", "body": "Hello"}

    with (
        patch("claws_gmail.cli.read_message", return_value=msg) as mock_read,
        patch("claws_gmail.cli.result"),
    ):
        from claws_gmail.cli import main

        main()
        mock_read.assert_called_once_with("abc", as_user="alice@example.com")


def test_send_with_as_flag(monkeypatch):
    """send --as alice@example.com passes as_user to send_message."""
    monkeypatch.setattr(
        "sys.argv",
        ["claws-gmail", "--as", "alice@example.com", "send", "--to", "bob@example.com", "--subject", "Hi", "--body", "Hello"],
    )
    resp = {"message_id": "m1", "thread_id": "t1"}

    with (
        patch("claws_gmail.cli.send_message", return_value=resp) as mock_send,
        patch("claws_gmail.cli.result"),
    ):
        from claws_gmail.cli import main

        main()
        mock_send.assert_called_once_with(
            to="bob@example.com", subject="Hi", body="Hello", cc=None, bcc=None, as_user="alice@example.com"
        )


def test_search_with_as_flag(monkeypatch):
    """search --as alice@example.com passes as_user to search_messages."""
    monkeypatch.setattr("sys.argv", ["claws-gmail", "--as", "alice@example.com", "search", "from:bob"])
    msgs = [{"id": "1"}]

    with (
        patch("claws_gmail.cli.search_messages", return_value=msgs) as mock_search,
        patch("claws_gmail.cli.result"),
    ):
        from claws_gmail.cli import main

        main()
        mock_search.assert_called_once_with(query="from:bob", max_results=10, as_user="alice@example.com")


# --- archive ---


def test_archive(monkeypatch):
    """archive <id> calls archive_message and outputs result."""
    monkeypatch.setattr("sys.argv", ["claws-gmail", "archive", "msg-001"])
    resp = {"id": "msg-001", "labelIds": ["UNREAD"]}

    with (
        patch("claws_gmail.cli.archive_message", return_value=resp) as mock_archive,
        patch("claws_gmail.cli.result") as mock_result,
    ):
        from claws_gmail.cli import main

        main()
        mock_archive.assert_called_once_with("msg-001", as_user=None)
        mock_result.assert_called_once_with({"message_id": "msg-001", "labels": ["UNREAD"]})


def test_archive_with_as_flag(monkeypatch):
    """archive --as alice@example.com passes as_user."""
    monkeypatch.setattr("sys.argv", ["claws-gmail", "--as", "alice@example.com", "archive", "msg-001"])
    resp = {"id": "msg-001", "labelIds": []}

    with (
        patch("claws_gmail.cli.archive_message", return_value=resp) as mock_archive,
        patch("claws_gmail.cli.result"),
    ):
        from claws_gmail.cli import main

        main()
        mock_archive.assert_called_once_with("msg-001", as_user="alice@example.com")


# --- search ---


def test_search(monkeypatch):
    """search calls search_messages and wraps output in dict."""
    monkeypatch.setattr("sys.argv", ["claws-gmail", "search", "from:alice"])
    msgs = [{"id": "1"}, {"id": "2"}]

    with (
        patch("claws_gmail.cli.search_messages", return_value=msgs) as mock_search,
        patch("claws_gmail.cli.result") as mock_result,
    ):
        from claws_gmail.cli import main

        main()
        mock_search.assert_called_once_with(query="from:alice", max_results=10, as_user=None)
        mock_result.assert_called_once_with({"messages": msgs, "result_count": 2})


def test_search_max(monkeypatch):
    """search --max 20 passes max_results=20."""
    monkeypatch.setattr("sys.argv", ["claws-gmail", "search", "from:alice", "--max", "20"])

    with (
        patch("claws_gmail.cli.search_messages", return_value=[]) as mock_search,
        patch("claws_gmail.cli.result"),
    ):
        from claws_gmail.cli import main

        main()
        mock_search.assert_called_once_with(query="from:alice", max_results=20, as_user=None)


# --- error handling ---


def test_connection_error(monkeypatch):
    """ConnectionError triggers crash()."""
    monkeypatch.setattr("sys.argv", ["claws-gmail", "inbox"])

    with (
        patch("claws_gmail.cli.list_inbox", side_effect=ConnectionError("cannot connect")),
        patch("claws_gmail.cli.crash") as mock_crash,
    ):
        from claws_gmail.cli import main

        main()
        mock_crash.assert_called_once_with("cannot connect")


def test_timeout_error(monkeypatch):
    """TimeoutError triggers crash()."""
    monkeypatch.setattr("sys.argv", ["claws-gmail", "inbox"])

    with (
        patch("claws_gmail.cli.list_inbox", side_effect=TimeoutError("timed out")),
        patch("claws_gmail.cli.crash") as mock_crash,
    ):
        from claws_gmail.cli import main

        main()
        mock_crash.assert_called_once_with("timed out")


def test_gmail_api_error(monkeypatch):
    """HTTPStatusError triggers handle_gmail_error()."""
    monkeypatch.setattr("sys.argv", ["claws-gmail", "inbox"])

    mock_response = MagicMock()
    mock_response.status_code = 401
    error = httpx.HTTPStatusError("auth failed", request=MagicMock(), response=mock_response)

    with (
        patch("claws_gmail.cli.list_inbox", side_effect=error),
        patch("claws_gmail.cli.handle_gmail_error") as mock_handler,
    ):
        from claws_gmail.cli import main

        main()
        mock_handler.assert_called_once_with(error)


# --- no subcommand ---


def test_no_subcommand(monkeypatch):
    """No subcommand raises SystemExit (argparse required=True)."""
    monkeypatch.setattr("sys.argv", ["claws-gmail"])

    with pytest.raises(SystemExit):
        from claws_gmail.cli import main

        main()
