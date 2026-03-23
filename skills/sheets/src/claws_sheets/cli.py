"""CLI entry point for claws-sheets spreadsheet skill."""

import argparse
import json

import httpx
from claws_common.output import crash, fail, result

from claws_sheets.sheets import (
    create_spreadsheet,
    handle_sheets_error,
    list_spreadsheets,
    read_values,
    write_values,
)


def main():
    """Sheets skill CLI with subcommands: list, read, write, create."""
    parser = argparse.ArgumentParser(
        prog="claws-sheets",
        description="Google Sheets skill for reading, writing, and creating spreadsheets",
    )
    parser.add_argument(
        "--as", dest="as_user", help="Act as this Google Workspace user (email)"
    )
    subs = parser.add_subparsers(dest="command", required=True)

    # list
    list_p = subs.add_parser("list", help="List spreadsheets")
    list_p.add_argument(
        "--max", type=int, default=100, help="Max results (default: 100)"
    )

    # read
    read_p = subs.add_parser("read", help="Read cell values")
    read_p.add_argument("spreadsheet_id", help="Spreadsheet ID")
    read_p.add_argument("range", help="A1 notation range (e.g., Sheet1!A1:B5)")

    # write
    write_p = subs.add_parser("write", help="Write cell values")
    write_p.add_argument("spreadsheet_id", help="Spreadsheet ID")
    write_p.add_argument("range", help="A1 notation range")
    write_p.add_argument(
        "--values",
        required=True,
        help='JSON 2D array (e.g., \'[["a","b"],["c","d"]]\')',
    )

    # create
    create_p = subs.add_parser("create", help="Create a new spreadsheet")
    create_p.add_argument("--title", required=True, help="Spreadsheet title")

    args = parser.parse_args()

    try:
        if args.command == "list":
            files = list_spreadsheets(max_results=args.max, as_user=args.as_user)
            result({"spreadsheets": files, "result_count": len(files)})

        elif args.command == "read":
            values = read_values(args.spreadsheet_id, args.range, as_user=args.as_user)
            result({"values": values, "row_count": len(values)})

        elif args.command == "write":
            try:
                values = json.loads(args.values)
            except json.JSONDecodeError as e:
                fail(f"Invalid JSON for --values: {e}")
                return
            resp = write_values(
                args.spreadsheet_id, args.range, values, as_user=args.as_user
            )
            result(resp)

        elif args.command == "create":
            resp = create_spreadsheet(title=args.title, as_user=args.as_user)
            result(resp)

    except httpx.HTTPStatusError as e:
        handle_sheets_error(e)
    except ConnectionError as e:
        crash(str(e))
    except TimeoutError as e:
        crash(str(e))


if __name__ == "__main__":
    main()
