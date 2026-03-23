"""CLI entry point for claws-contacts Google Contacts skill."""

import argparse

import httpx

from claws_common.output import crash, result

from claws_contacts.contacts import (
    create_contact,
    delete_contact,
    get_contact,
    handle_contacts_error,
    list_contacts,
    search_contacts,
    update_contact,
)


def main():
    """Contacts skill CLI with subcommands: list, search, get, create, update, delete."""
    parser = argparse.ArgumentParser(
        prog="claws-contacts",
        description="Google Contacts skill for listing, searching, and managing contacts",
    )
    parser.add_argument(
        "--as", dest="as_user", help="Act as this Google Workspace user (email)"
    )
    subs = parser.add_subparsers(dest="command", required=True)

    # list
    list_p = subs.add_parser("list", help="List all contacts")
    list_p.add_argument("--max", type=int, default=100, help="Max contacts (default: 100)")

    # search
    search_p = subs.add_parser("search", help="Search contacts")
    search_p.add_argument("query", help="Search query")
    search_p.add_argument("--max", type=int, default=10, help="Max results (default: 10)")

    # get
    get_p = subs.add_parser("get", help="Get a contact by resource name")
    get_p.add_argument("resource_name", help="Contact resource name (e.g., people/c1234567890)")

    # create
    create_p = subs.add_parser("create", help="Create a new contact")
    create_p.add_argument("--name", required=True, help="Contact name")
    create_p.add_argument("--email", help="Email address")
    create_p.add_argument("--phone", help="Phone number")

    # update
    update_p = subs.add_parser("update", help="Update a contact")
    update_p.add_argument("resource_name", help="Contact resource name")
    update_p.add_argument("--name", help="New name")
    update_p.add_argument("--email", help="New email")
    update_p.add_argument("--phone", help="New phone")

    # delete
    delete_p = subs.add_parser("delete", help="Delete a contact")
    delete_p.add_argument("resource_name", help="Contact resource name")

    args = parser.parse_args()

    try:
        if args.command == "list":
            contacts = list_contacts(max_results=args.max, as_user=args.as_user)
            result({"contacts": contacts, "result_count": len(contacts)})

        elif args.command == "search":
            contacts = search_contacts(
                query=args.query, max_results=args.max, as_user=args.as_user
            )
            result({"contacts": contacts, "result_count": len(contacts)})

        elif args.command == "get":
            contact = get_contact(resource_name=args.resource_name, as_user=args.as_user)
            result(contact)

        elif args.command == "create":
            contact = create_contact(
                name=args.name, email=args.email, phone=args.phone, as_user=args.as_user
            )
            result(contact)

        elif args.command == "update":
            contact = update_contact(
                resource_name=args.resource_name,
                name=args.name,
                email=args.email,
                phone=args.phone,
                as_user=args.as_user,
            )
            result(contact)

        elif args.command == "delete":
            delete_contact(resource_name=args.resource_name, as_user=args.as_user)
            result({"deleted": True})

    except httpx.HTTPStatusError as e:
        handle_contacts_error(e)
    except ConnectionError as e:
        crash(str(e))
    except TimeoutError as e:
        crash(str(e))


if __name__ == "__main__":
    main()
