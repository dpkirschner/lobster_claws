"""Validation tests for launchd plists."""

from __future__ import annotations

import plistlib
from pathlib import Path

LAUNCHD_DIR = Path(__file__).parent.parent / "launchd"

WHISPER_PLIST = LAUNCHD_DIR / "com.lobsterclaws.whisper.plist"
GOOGLE_AUTH_PLIST = LAUNCHD_DIR / "com.lobsterclaws.google-auth.plist"


def _load_plist(path: Path) -> dict:
    with open(path, "rb") as f:
        return plistlib.load(f)


# -- Whisper plist tests (existing, unchanged behavior) --


def test_whisper_plist_valid_xml():
    plist = _load_plist(WHISPER_PLIST)
    assert isinstance(plist, dict)


def test_whisper_plist_label():
    plist = _load_plist(WHISPER_PLIST)
    assert plist["Label"] == "com.lobsterclaws.whisper"


def test_whisper_plist_run_at_load():
    plist = _load_plist(WHISPER_PLIST)
    assert plist["RunAtLoad"] is True


def test_whisper_plist_keep_alive():
    plist = _load_plist(WHISPER_PLIST)
    assert plist["KeepAlive"] is True


def test_whisper_plist_program_args():
    plist = _load_plist(WHISPER_PLIST)
    args = plist["ProgramArguments"]
    assert "whisper_server.app:app" in args
    assert "--host" in args
    assert "0.0.0.0" in args
    assert "--port" in args
    assert "8300" in args


def test_whisper_plist_no_tilde():
    raw_text = WHISPER_PLIST.read_text()
    assert "~" not in raw_text


def test_whisper_plist_env_path():
    plist = _load_plist(WHISPER_PLIST)
    env = plist["EnvironmentVariables"]
    assert "/opt/homebrew/bin" in env["PATH"]


def test_whisper_plist_log_paths():
    plist = _load_plist(WHISPER_PLIST)
    assert plist["StandardOutPath"].startswith("/")
    assert plist["StandardErrorPath"].startswith("/")
    assert "/Library/Logs/lobsterclaws/" in plist["StandardOutPath"]
    assert "/Library/Logs/lobsterclaws/" in plist["StandardErrorPath"]


# -- Google Auth plist tests --


def test_google_auth_plist_valid_xml():
    plist = _load_plist(GOOGLE_AUTH_PLIST)
    assert isinstance(plist, dict)


def test_google_auth_plist_label():
    plist = _load_plist(GOOGLE_AUTH_PLIST)
    assert plist["Label"] == "com.lobsterclaws.google-auth"


def test_google_auth_plist_run_at_load():
    plist = _load_plist(GOOGLE_AUTH_PLIST)
    assert plist["RunAtLoad"] is True


def test_google_auth_plist_keep_alive():
    plist = _load_plist(GOOGLE_AUTH_PLIST)
    assert plist["KeepAlive"] is True


def test_google_auth_plist_binds_localhost():
    """SECURITY: auth server MUST bind 127.0.0.1, NOT 0.0.0.0."""
    plist = _load_plist(GOOGLE_AUTH_PLIST)
    args = plist["ProgramArguments"]
    assert "127.0.0.1" in args
    assert "0.0.0.0" not in args


def test_google_auth_plist_port():
    plist = _load_plist(GOOGLE_AUTH_PLIST)
    args = plist["ProgramArguments"]
    assert "8301" in args


def test_google_auth_plist_module():
    plist = _load_plist(GOOGLE_AUTH_PLIST)
    args = plist["ProgramArguments"]
    assert "google_auth_server.app:app" in args


def test_google_auth_plist_env_key_path():
    plist = _load_plist(GOOGLE_AUTH_PLIST)
    env = plist["EnvironmentVariables"]
    assert "GOOGLE_SERVICE_ACCOUNT_KEY" in env


def test_google_auth_plist_env_delegated_user():
    plist = _load_plist(GOOGLE_AUTH_PLIST)
    env = plist["EnvironmentVariables"]
    assert "GOOGLE_DELEGATED_USER" in env


def test_google_auth_plist_log_paths():
    plist = _load_plist(GOOGLE_AUTH_PLIST)
    assert plist["StandardOutPath"].startswith("/")
    assert plist["StandardErrorPath"].startswith("/")
    assert "/Library/Logs/lobsterclaws/" in plist["StandardOutPath"]
    assert "/Library/Logs/lobsterclaws/" in plist["StandardErrorPath"]


def test_google_auth_plist_no_tilde():
    raw_text = GOOGLE_AUTH_PLIST.read_text()
    assert "~" not in raw_text


def test_google_auth_plist_env_path():
    plist = _load_plist(GOOGLE_AUTH_PLIST)
    env = plist["EnvironmentVariables"]
    assert "/opt/homebrew/bin" in env["PATH"]
