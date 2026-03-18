"""Shared client library for Lobster Claws skills."""

from claws_common.client import ClawsClient
from claws_common.host import resolve_host
from claws_common.output import crash, error, fail, result

__all__ = ["ClawsClient", "resolve_host", "result", "error", "fail", "crash"]
