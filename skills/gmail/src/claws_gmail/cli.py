"""CLI entry point for claws-gmail email skill."""

import argparse
import sys

import httpx

from claws_common.output import crash, result

from claws_gmail.gmail import (
    archive_message,
    handle_gmail_error,
    list_inbox,
    read_message,
    search_messages,
    send_message,
)


def main():
    """Gmail skill CLI with subcommands: inbox, read, send, search."""
    parser = argparse.ArgumentParser(
        prog="claws-gmail",
        description="Gmail skill for reading, sending, and searching email",
    )
    parser.add_argument("--as", dest="as_user",
                        help="Act as this Google Workspace user (email)")
    subs = parser.add_subparsers(dest="command", required=True)

    # inbox
    inbox_p = subs.add_parser("inbox", help="List inbox messages")
    inbox_p.add_argument("--max", type=int, default=10, help="Max messages (default: 10)")

    # read
    read_p = subs.add_parser("read", help="Read a message by ID")
    read_p.add_argument("id", help="Message ID")

    # send
    send_p = subs.add_parser("send", help="Send an email")
    send_p.add_argument("--to", required=True, help="Recipient email address")
    send_p.add_argument("--subject", required=True, help="Email subject")
    send_p.add_argument(
        "--body", help="Message body (reads stdin if omitted and not a TTY)"
    )
    send_p.add_argument("--cc", help="CC recipient(s)")
    send_p.add_argument("--bcc", help="BCC recipient(s)")

    # archive
    archive_p = subs.add_parser("archive", help="Archive a message (remove from inbox)")
    archive_p.add_argument("id", help="Message ID")

    # search
    search_p = subs.add_parser("search", help="Search messages")
    search_p.add_argument(
        "query", help="Gmail search query (e.g. from:alice subject:hello)"
    )
    search_p.add_argument(
        "--max", type=int, default=10, help="Max results (default: 10)"
    )

    args = parser.parse_args()

    try:
        if args.command == "inbox":
            messages = list_inbox(max_results=args.max, as_user=args.as_user)
            result({"messages": messages, "result_count": len(messages)})

        elif args.command == "read":
            msg = read_message(args.id, as_user=args.as_user)
            result(msg)

        elif args.command == "send":
            body = args.body
            if body is None and not sys.stdin.isatty():
                body = sys.stdin.read()
            if body is None:
                parser.error("--body is required (or pipe text to stdin)")
            resp = send_message(
                to=args.to,
                subject=args.subject,
                body=body,
                cc=args.cc,
                bcc=args.bcc,
                as_user=args.as_user,
            )
            result(resp)

        elif args.command == "archive":
            resp = archive_message(args.id, as_user=args.as_user)
            result({"message_id": resp["id"], "labels": resp.get("labelIds", [])})

        elif args.command == "search":
            messages = search_messages(query=args.query, max_results=args.max, as_user=args.as_user)
            result({"messages": messages, "result_count": len(messages)})

    except httpx.HTTPStatusError as e:
        handle_gmail_error(e)
    except ConnectionError as e:
        crash(str(e))
    except TimeoutError as e:
        crash(str(e))


if __name__ == "__main__":
    main()
