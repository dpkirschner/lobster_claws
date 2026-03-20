"""CLI entry point for claws-calendar skill."""

import argparse
from datetime import date, timedelta

import httpx
from claws_common.output import crash, result

from claws_calendar.calendar import (
    create_event,
    date_to_rfc3339,
    delete_event,
    get_event,
    handle_calendar_error,
    list_events,
    update_event,
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
    """Calendar skill CLI with subcommands: list, get, create, update, delete."""
    parser = argparse.ArgumentParser(
        prog="claws-calendar",
        description="Calendar skill for managing events",
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

    # create
    create_p = subs.add_parser("create", help="Create a calendar event")
    create_p.add_argument("--title", required=True, help="Event title")
    create_p.add_argument(
        "--start", help="Start time (ISO 8601, e.g. 2026-03-20T10:00:00)"
    )
    create_p.add_argument(
        "--end", help="End time (ISO 8601, e.g. 2026-03-20T11:00:00)"
    )
    create_p.add_argument("--date", help="Date for all-day event (YYYY-MM-DD)")
    create_p.add_argument(
        "--all-day",
        action="store_true",
        help="Create all-day event (use with --date)",
    )
    create_p.add_argument("--location", help="Event location")
    create_p.add_argument("--description", help="Event description")
    create_p.add_argument("--attendees", help="Comma-separated attendee emails")

    # update
    update_p = subs.add_parser("update", help="Update a calendar event")
    update_p.add_argument("id", help="Event ID to update")
    update_p.add_argument("--title", help="New event title")
    update_p.add_argument("--start", help="New start time (ISO 8601)")
    update_p.add_argument("--end", help="New end time (ISO 8601)")
    update_p.add_argument("--location", help="New event location")
    update_p.add_argument("--description", help="New event description")
    update_p.add_argument(
        "--attendees", help="New comma-separated attendee emails"
    )

    # delete
    delete_p = subs.add_parser("delete", help="Delete a calendar event")
    delete_p.add_argument("id", help="Event ID to delete")

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

        elif args.command == "create":
            attendees = args.attendees.split(",") if args.attendees else None
            if args.all_day and args.date:
                end_date = date.fromisoformat(args.date) + timedelta(days=1)
                event = create_event(
                    title=args.title,
                    start=args.date,
                    end=str(end_date),
                    all_day=True,
                    location=args.location,
                    description=args.description,
                    attendees=attendees,
                )
            else:
                event = create_event(
                    title=args.title,
                    start=args.start,
                    end=args.end,
                    location=args.location,
                    description=args.description,
                    attendees=attendees,
                )
            result(event)

        elif args.command == "update":
            attendees = args.attendees.split(",") if args.attendees else None
            event = update_event(
                args.id,
                title=args.title,
                start=args.start,
                end=args.end,
                location=args.location,
                description=args.description,
                attendees=attendees,
            )
            result(event)

        elif args.command == "delete":
            resp = delete_event(args.id)
            result(resp)

    except httpx.HTTPStatusError as e:
        handle_calendar_error(e)
    except ConnectionError as e:
        crash(str(e))
    except TimeoutError as e:
        crash(str(e))


if __name__ == "__main__":
    main()
