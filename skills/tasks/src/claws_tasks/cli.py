"""CLI entry point for claws-tasks Google Tasks skill."""

import argparse

import httpx

from claws_common.output import crash, result

from claws_tasks.tasks import (
    complete_task,
    create_task,
    delete_task,
    handle_tasks_error,
    list_task_lists,
    list_tasks,
    update_task,
)


def main():
    """Tasks skill CLI with subcommands: lists, list, create, complete, update, delete."""
    parser = argparse.ArgumentParser(
        prog="claws-tasks",
        description="Google Tasks skill for managing task lists and tasks",
    )
    parser.add_argument(
        "--as", dest="as_user", help="Act as this Google Workspace user (email)"
    )
    subs = parser.add_subparsers(dest="command", required=True)

    # lists -- list all task lists
    subs.add_parser("lists", help="List all task lists")

    # list -- list tasks in a task list
    list_p = subs.add_parser("list", help="List tasks in a task list")
    list_p.add_argument(
        "--list", dest="tasklist", default="@default", help="Task list ID (default: @default)"
    )
    list_p.add_argument("--max", type=int, default=100, help="Max tasks (default: 100)")

    # create -- create a task
    create_p = subs.add_parser("create", help="Create a new task")
    create_p.add_argument("--title", required=True, help="Task title")
    create_p.add_argument("--list", dest="tasklist", default="@default")
    create_p.add_argument("--notes", help="Task notes/description")

    # complete -- mark a task as done
    complete_p = subs.add_parser("complete", help="Mark a task as completed")
    complete_p.add_argument("task_id", help="Task ID")
    complete_p.add_argument("--list", dest="tasklist", default="@default")

    # update -- update a task
    update_p = subs.add_parser("update", help="Update a task")
    update_p.add_argument("task_id", help="Task ID")
    update_p.add_argument("--title", help="New title")
    update_p.add_argument("--notes", help="New notes")
    update_p.add_argument("--list", dest="tasklist", default="@default")

    # delete -- delete a task
    delete_p = subs.add_parser("delete", help="Delete a task")
    delete_p.add_argument("task_id", help="Task ID")
    delete_p.add_argument("--list", dest="tasklist", default="@default")

    args = parser.parse_args()

    try:
        if args.command == "lists":
            task_lists = list_task_lists(as_user=args.as_user)
            result({"task_lists": task_lists, "result_count": len(task_lists)})

        elif args.command == "list":
            tasks = list_tasks(
                tasklist=args.tasklist, max_results=args.max, as_user=args.as_user
            )
            result({"tasks": tasks, "result_count": len(tasks)})

        elif args.command == "create":
            task = create_task(
                tasklist=args.tasklist,
                title=args.title,
                notes=args.notes,
                as_user=args.as_user,
            )
            result(task)

        elif args.command == "complete":
            task = complete_task(
                tasklist=args.tasklist, task_id=args.task_id, as_user=args.as_user
            )
            result(task)

        elif args.command == "update":
            task = update_task(
                tasklist=args.tasklist,
                task_id=args.task_id,
                title=args.title,
                notes=args.notes,
                as_user=args.as_user,
            )
            result(task)

        elif args.command == "delete":
            delete_task(
                tasklist=args.tasklist, task_id=args.task_id, as_user=args.as_user
            )
            result({"deleted": True})

    except httpx.HTTPStatusError as e:
        handle_tasks_error(e)
    except ConnectionError as e:
        crash(str(e))
    except TimeoutError as e:
        crash(str(e))


if __name__ == "__main__":
    main()
