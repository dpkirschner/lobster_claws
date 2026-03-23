"""CLI entry point for claws-docs Google Docs skill."""

import argparse

import httpx
from claws_common.output import crash, result

from claws_docs.docs import (
    append_text,
    create_document,
    handle_docs_error,
    list_documents,
    read_document,
)


def main():
    """Google Docs skill CLI with subcommands: list, read, create, append."""
    parser = argparse.ArgumentParser(
        prog="claws-docs",
        description="Google Docs skill for listing, reading, creating, and appending",
    )
    parser.add_argument(
        "--as", dest="as_user", help="Act as this Google Workspace user (email)"
    )
    subs = parser.add_subparsers(dest="command", required=True)

    # list
    list_p = subs.add_parser("list", help="List documents")
    list_p.add_argument(
        "--max", type=int, default=100, help="Max results (default: 100)"
    )

    # read
    read_p = subs.add_parser("read", help="Read document as plain text")
    read_p.add_argument("doc_id", help="Document ID")

    # create
    create_p = subs.add_parser("create", help="Create a new document")
    create_p.add_argument("--title", required=True, help="Document title")
    create_p.add_argument("--body", help="Initial document body text")

    # append
    append_p = subs.add_parser("append", help="Append text to a document")
    append_p.add_argument("doc_id", help="Document ID")
    append_p.add_argument("--body", required=True, help="Text to append")

    args = parser.parse_args()

    try:
        if args.command == "list":
            documents = list_documents(max_results=args.max, as_user=args.as_user)
            result({"documents": documents, "result_count": len(documents)})

        elif args.command == "read":
            doc = read_document(doc_id=args.doc_id, as_user=args.as_user)
            result(doc)

        elif args.command == "create":
            resp = create_document(
                title=args.title, body=args.body, as_user=args.as_user
            )
            result(resp)

        elif args.command == "append":
            resp = append_text(
                doc_id=args.doc_id, text=args.body, as_user=args.as_user
            )
            result(resp)

    except httpx.HTTPStatusError as e:
        handle_docs_error(e)
    except ConnectionError as e:
        crash(str(e))
    except TimeoutError as e:
        crash(str(e))


if __name__ == "__main__":
    main()
