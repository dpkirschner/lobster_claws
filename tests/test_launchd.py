"""Validation tests for the whisper server launchd plist."""

from __future__ import annotations

import plistlib
from pathlib import Path

PLIST_PATH = Path(__file__).parent.parent / "launchd" / "com.lobsterclaws.whisper.plist"


def _load_plist() -> dict:
    with open(PLIST_PATH, "rb") as f:
        return plistlib.load(f)


def test_plist_valid_xml():
    """Plist file parses as valid XML without errors."""
    plist = _load_plist()
    assert isinstance(plist, dict)


def test_plist_label():
    """Label is com.lobsterclaws.whisper."""
    plist = _load_plist()
    assert plist["Label"] == "com.lobsterclaws.whisper"


def test_plist_run_at_load():
    """RunAtLoad is true."""
    plist = _load_plist()
    assert plist["RunAtLoad"] is True


def test_plist_keep_alive():
    """KeepAlive is true."""
    plist = _load_plist()
    assert plist["KeepAlive"] is True


def test_plist_program_args():
    """ProgramArguments contains uvicorn with correct module and host/port."""
    plist = _load_plist()
    args = plist["ProgramArguments"]
    assert "whisper_server.app:app" in args
    assert "--host" in args
    assert "0.0.0.0" in args
    assert "--port" in args
    assert "8300" in args


def test_plist_no_tilde():
    """No path in plist contains ~ (all paths must be absolute)."""
    raw_text = PLIST_PATH.read_text()
    assert "~" not in raw_text


def test_plist_env_path():
    """EnvironmentVariables PATH includes /opt/homebrew/bin."""
    plist = _load_plist()
    env = plist["EnvironmentVariables"]
    assert "/opt/homebrew/bin" in env["PATH"]


def test_plist_log_paths():
    """StandardOutPath and StandardErrorPath are absolute under ~/Library/Logs/lobsterclaws/."""
    plist = _load_plist()
    stdout_path = plist["StandardOutPath"]
    stderr_path = plist["StandardErrorPath"]
    assert stdout_path.startswith("/")
    assert stderr_path.startswith("/")
    assert "/Library/Logs/lobsterclaws/" in stdout_path
    assert "/Library/Logs/lobsterclaws/" in stderr_path
