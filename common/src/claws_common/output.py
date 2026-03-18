"""Structured output convention for CLI skills.

Convention:
- Result data goes to stdout (strings as-is, dicts as JSON)
- Errors and diagnostics go to stderr
- Exit codes: 0 = success, 1 = user error, 2 = infrastructure error
"""

import json
import sys


def result(data: str | dict) -> None:
    """Print result to stdout. Strings print as-is, dicts print as JSON."""
    if isinstance(data, dict):
        print(json.dumps(data), flush=True)
    else:
        print(data, flush=True)


def error(message: str, exit_code: int = 1) -> None:
    """Print error to stderr and exit."""
    print(f"Error: {message}", file=sys.stderr, flush=True)
    sys.exit(exit_code)


def fail(message: str) -> None:
    """User-fixable error (exit code 1)."""
    error(message, exit_code=1)


def crash(message: str) -> None:
    """Infrastructure error (exit code 2)."""
    error(message, exit_code=2)
