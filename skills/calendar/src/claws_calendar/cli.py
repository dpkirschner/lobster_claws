"""CLI entry point for claws-calendar skill."""

import argparse
from datetime import date, timedelta

import httpx
from claws_common.output import crash, result

from claws_calendar.calendar import (
    date_to_rfc3339,
    get_event,
    handle_calendar_error,
    list_events,
)


def _resolve_date_range(args) -> tuple[str | None, str | None]:
    """Convert CLI date flags to RFC 3339 time_min/time_max strings."""
    today = date.today()

    if args.today:
        return date_to_rfc3339(today), date_to_rfc3339(today + timedelta(days=1))

    if args.week:
        monday = today - timedelta(days=today.weekday())
        next_monday = monday + timedelta(days=7)
        return date_to_rfc3339(monday), date_to_rfc3339(next_monday)

    time_min = None
    time_max = None

    if args.from_date:
        time_min = date_to_rfc3339(date.fromisoformat(args.from_date))
    if args.to_date:
        time_max = date_to_rfc3339(date.fromisoformat(args.to_date), end_of_day=True)

    # Default: next 7 days
    if time_min is None and time_max is None:
        time_min = date_to_rfc3339(today)
        time_max = date_to_rfc3339(today + timedelta(days=7))

    return time_min, time_max


def main():
    """Calendar skill CLI with subcommands: list, get."""
    parser = argparse.ArgumentParser(
        prog="claws-calendar",
        description="Calendar skill for listing and viewing events",
    )
    subs = parser.add_subparsers(dest="command", required=True)

    # list
    list_p = subs.add_parser("list", help="List calendar events")
    list_p.add_argument("--today", action="store_true", help="Show today's events")
    list_p.add_argument(
        "--week", action="store_true", help="Show this week's events (Mon-Sun)"
    )
    list_p.add_argument("--from", dest="from_date", help="Start date (YYYY-MM-DD)")
    list_p.add_argument("--to", dest="to_date", help="End date (YYYY-MM-DD)")
    list_p.add_argument(
        "--max", type=int, default=25, help="Max events (default: 25)"
    )

    # get
    get_p = subs.add_parser("get", help="Get event details by ID")
    get_p.add_argument("id", help="Event ID")

    args = parser.parse_args()

    try:
        if args.command == "list":
            time_min, time_max = _resolve_date_range(args)
            events = list_events(
                time_min=time_min, time_max=time_max, max_results=args.max
            )
            result({"events": events, "result_count": len(events)})

        elif args.command == "get":
            event = get_event(args.id)
            result(event)

    except httpx.HTTPStatusError as e:
        handle_calendar_error(e)
    except ConnectionError as e:
        crash(str(e))
    except TimeoutError as e:
        crash(str(e))


if __name__ == "__main__":
    main()
