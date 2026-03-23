"""Tests for Contacts CLI entry point (subcommand routing)."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

# --- list ---


def test_list_default(monkeypatch):
    """list with no args calls list_contacts(max_results=100) and outputs wrapped dict."""
    monkeypatch.setattr("sys.argv", ["claws-contacts", "list"])
    mock_contacts = [{"resourceName": "people/c1", "names": [{"displayName": "Alice"}]}]

    with (
        patch("claws_contacts.cli.list_contacts", return_value=mock_contacts) as mock_list,
        patch("claws_contacts.cli.result") as mock_result,
    ):
        from claws_contacts.cli import main

        main()
        mock_list.assert_called_once_with(max_results=100, as_user=None)
        mock_result.assert_called_once_with({"contacts": mock_contacts, "result_count": 1})


def test_list_max(monkeypatch):
    """list --max 20 passes max_results=20."""
    monkeypatch.setattr("sys.argv", ["claws-contacts", "list", "--max", "20"])

    with (
        patch("claws_contacts.cli.list_contacts", return_value=[]) as mock_list,
        patch("claws_contacts.cli.result"),
    ):
        from claws_contacts.cli import main

        main()
        mock_list.assert_called_once_with(max_results=20, as_user=None)


# --- search ---


def test_search(monkeypatch):
    """search calls search_contacts and wraps output in dict."""
    monkeypatch.setattr("sys.argv", ["claws-contacts", "search", "alice"])
    mock_results = [{"person": {"resourceName": "people/c1"}}]

    with (
        patch("claws_contacts.cli.search_contacts", return_value=mock_results) as mock_search,
        patch("claws_contacts.cli.result") as mock_result,
    ):
        from claws_contacts.cli import main

        main()
        mock_search.assert_called_once_with(query="alice", max_results=10, as_user=None)
        mock_result.assert_called_once_with({"contacts": mock_results, "result_count": 1})


def test_search_max(monkeypatch):
    """search --max 5 passes max_results=5."""
    monkeypatch.setattr("sys.argv", ["claws-contacts", "search", "alice", "--max", "5"])

    with (
        patch("claws_contacts.cli.search_contacts", return_value=[]) as mock_search,
        patch("claws_contacts.cli.result"),
    ):
        from claws_contacts.cli import main

        main()
        mock_search.assert_called_once_with(query="alice", max_results=5, as_user=None)


# --- get ---


def test_get(monkeypatch):
    """get <resource_name> calls get_contact and outputs the returned dict."""
    monkeypatch.setattr("sys.argv", ["claws-contacts", "get", "people/c123"])
    contact = {"resourceName": "people/c123", "names": [{"displayName": "Alice"}]}

    with (
        patch("claws_contacts.cli.get_contact", return_value=contact) as mock_get,
        patch("claws_contacts.cli.result") as mock_result,
    ):
        from claws_contacts.cli import main

        main()
        mock_get.assert_called_once_with(resource_name="people/c123", as_user=None)
        mock_result.assert_called_once_with(contact)


# --- create ---


def test_create_all_fields(monkeypatch):
    """create --name --email --phone passes all args."""
    monkeypatch.setattr(
        "sys.argv",
        ["claws-contacts", "create", "--name", "Alice",
         "--email", "a@x.com", "--phone", "555-1234"],
    )
    resp = {"resourceName": "people/c999"}

    with (
        patch("claws_contacts.cli.create_contact", return_value=resp) as mock_create,
        patch("claws_contacts.cli.result") as mock_result,
    ):
        from claws_contacts.cli import main

        main()
        mock_create.assert_called_once_with(
            name="Alice", email="a@x.com", phone="555-1234", as_user=None
        )
        mock_result.assert_called_once_with(resp)


def test_create_name_only(monkeypatch):
    """create --name works without email/phone."""
    monkeypatch.setattr("sys.argv", ["claws-contacts", "create", "--name", "Alice"])
    resp = {"resourceName": "people/c999"}

    with (
        patch("claws_contacts.cli.create_contact", return_value=resp) as mock_create,
        patch("claws_contacts.cli.result"),
    ):
        from claws_contacts.cli import main

        main()
        mock_create.assert_called_once_with(
            name="Alice", email=None, phone=None, as_user=None
        )


# --- update ---


def test_update(monkeypatch):
    """update <resource_name> --name passes args correctly."""
    monkeypatch.setattr(
        "sys.argv", ["claws-contacts", "update", "people/c123", "--name", "Bob"]
    )
    resp = {"resourceName": "people/c123", "names": [{"givenName": "Bob"}]}

    with (
        patch("claws_contacts.cli.update_contact", return_value=resp) as mock_update,
        patch("claws_contacts.cli.result") as mock_result,
    ):
        from claws_contacts.cli import main

        main()
        mock_update.assert_called_once_with(
            resource_name="people/c123", name="Bob", email=None, phone=None, as_user=None
        )
        mock_result.assert_called_once_with(resp)


# --- delete ---


def test_delete(monkeypatch):
    """delete <resource_name> calls delete_contact and outputs success."""
    monkeypatch.setattr("sys.argv", ["claws-contacts", "delete", "people/c123"])

    with (
        patch("claws_contacts.cli.delete_contact") as mock_delete,
        patch("claws_contacts.cli.result") as mock_result,
    ):
        from claws_contacts.cli import main

        main()
        mock_delete.assert_called_once_with(resource_name="people/c123", as_user=None)
        mock_result.assert_called_once_with({"deleted": True})


# --- --as flag ---


def test_list_with_as_flag(monkeypatch):
    """list --as alice@example.com passes as_user to list_contacts."""
    monkeypatch.setattr("sys.argv", ["claws-contacts", "--as", "alice@example.com", "list"])

    with (
        patch("claws_contacts.cli.list_contacts", return_value=[]) as mock_list,
        patch("claws_contacts.cli.result"),
    ):
        from claws_contacts.cli import main

        main()
        mock_list.assert_called_once_with(max_results=100, as_user="alice@example.com")


def test_search_with_as_flag(monkeypatch):
    """search --as alice@example.com passes as_user to search_contacts."""
    monkeypatch.setattr(
        "sys.argv", ["claws-contacts", "--as", "alice@example.com", "search", "bob"]
    )

    with (
        patch("claws_contacts.cli.search_contacts", return_value=[]) as mock_search,
        patch("claws_contacts.cli.result"),
    ):
        from claws_contacts.cli import main

        main()
        mock_search.assert_called_once_with(
            query="bob", max_results=10, as_user="alice@example.com"
        )


def test_get_with_as_flag(monkeypatch):
    """get --as alice@example.com passes as_user to get_contact."""
    monkeypatch.setattr(
        "sys.argv", ["claws-contacts", "--as", "alice@example.com", "get", "people/c123"]
    )
    contact = {"resourceName": "people/c123"}

    with (
        patch("claws_contacts.cli.get_contact", return_value=contact) as mock_get,
        patch("claws_contacts.cli.result"),
    ):
        from claws_contacts.cli import main

        main()
        mock_get.assert_called_once_with(resource_name="people/c123", as_user="alice@example.com")


def test_create_with_as_flag(monkeypatch):
    """create --as alice@example.com passes as_user to create_contact."""
    monkeypatch.setattr(
        "sys.argv",
        ["claws-contacts", "--as", "alice@example.com", "create", "--name", "Bob"],
    )
    resp = {"resourceName": "people/c999"}

    with (
        patch("claws_contacts.cli.create_contact", return_value=resp) as mock_create,
        patch("claws_contacts.cli.result"),
    ):
        from claws_contacts.cli import main

        main()
        mock_create.assert_called_once_with(
            name="Bob", email=None, phone=None, as_user="alice@example.com"
        )


def test_delete_with_as_flag(monkeypatch):
    """delete --as alice@example.com passes as_user to delete_contact."""
    monkeypatch.setattr(
        "sys.argv",
        ["claws-contacts", "--as", "alice@example.com", "delete", "people/c123"],
    )

    with (
        patch("claws_contacts.cli.delete_contact") as mock_delete,
        patch("claws_contacts.cli.result"),
    ):
        from claws_contacts.cli import main

        main()
        mock_delete.assert_called_once_with(
            resource_name="people/c123", as_user="alice@example.com"
        )


# --- error handling ---


def test_connection_error(monkeypatch):
    """ConnectionError triggers crash()."""
    monkeypatch.setattr("sys.argv", ["claws-contacts", "list"])

    with (
        patch("claws_contacts.cli.list_contacts", side_effect=ConnectionError("cannot connect")),
        patch("claws_contacts.cli.crash") as mock_crash,
    ):
        from claws_contacts.cli import main

        main()
        mock_crash.assert_called_once_with("cannot connect")


def test_timeout_error(monkeypatch):
    """TimeoutError triggers crash()."""
    monkeypatch.setattr("sys.argv", ["claws-contacts", "list"])

    with (
        patch("claws_contacts.cli.list_contacts", side_effect=TimeoutError("timed out")),
        patch("claws_contacts.cli.crash") as mock_crash,
    ):
        from claws_contacts.cli import main

        main()
        mock_crash.assert_called_once_with("timed out")


def test_contacts_api_error(monkeypatch):
    """HTTPStatusError triggers handle_contacts_error()."""
    monkeypatch.setattr("sys.argv", ["claws-contacts", "list"])

    mock_response = MagicMock()
    mock_response.status_code = 401
    error = httpx.HTTPStatusError("auth failed", request=MagicMock(), response=mock_response)

    with (
        patch("claws_contacts.cli.list_contacts", side_effect=error),
        patch("claws_contacts.cli.handle_contacts_error") as mock_handler,
    ):
        from claws_contacts.cli import main

        main()
        mock_handler.assert_called_once_with(error)


# --- no subcommand ---


def test_no_subcommand(monkeypatch):
    """No subcommand raises SystemExit (argparse required=True)."""
    monkeypatch.setattr("sys.argv", ["claws-contacts"])

    with pytest.raises(SystemExit):
        from claws_contacts.cli import main

        main()
