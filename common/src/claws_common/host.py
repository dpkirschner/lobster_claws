"""Host resolution for container-to-host communication."""

import os
from pathlib import Path


def resolve_host() -> str:
    """Resolve the host address for reaching servers.

    Priority: OPENCLAW_TOOLS_HOST env var > Docker detection > localhost fallback.
    """
    if host := os.environ.get("OPENCLAW_TOOLS_HOST"):
        return host
    if _in_docker():
        return "host.docker.internal"
    return "127.0.0.1"


def _in_docker() -> bool:
    """Detect if running inside a Docker container."""
    if Path("/.dockerenv").exists():
        return True
    if os.environ.get("container") == "docker":
        return True
    try:
        with open("/proc/1/cgroup") as f:
            return "docker" in f.read()
    except (FileNotFoundError, PermissionError):
        return False
