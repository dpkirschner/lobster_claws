import os
from unittest.mock import patch

from claws_common.host import _in_docker, resolve_host


def test_env_var_override():
    """OPENCLAW_TOOLS_HOST always takes priority."""
    with patch.dict(os.environ, {"OPENCLAW_TOOLS_HOST": "my-custom-host"}):
        assert resolve_host() == "my-custom-host"


def test_docker_detection_dockerenv():
    """/.dockerenv file signals Docker environment."""
    with patch("claws_common.host.Path") as MockPath:
        MockPath.return_value.exists.return_value = True
        with patch.dict(os.environ, {}, clear=True):
            assert _in_docker() is True


def test_docker_detection_env_var():
    """container=docker env var signals Docker environment."""
    with patch("claws_common.host.Path") as MockPath:
        MockPath.return_value.exists.return_value = False
        with patch.dict(os.environ, {"container": "docker"}, clear=True):
            assert _in_docker() is True


def test_docker_returns_host_docker_internal():
    """In Docker without override, resolve to host.docker.internal."""
    with patch.dict(os.environ, {}, clear=True):
        with patch("claws_common.host._in_docker", return_value=True):
            assert resolve_host() == "host.docker.internal"


def test_localhost_fallback():
    """Outside Docker without override, resolve to 127.0.0.1."""
    with patch.dict(os.environ, {}, clear=True):
        with patch("claws_common.host._in_docker", return_value=False):
            assert resolve_host() == "127.0.0.1"


def test_env_override_takes_priority_over_docker():
    """Env var beats Docker detection."""
    with patch.dict(os.environ, {"OPENCLAW_TOOLS_HOST": "override.local"}):
        with patch("claws_common.host._in_docker", return_value=True):
            assert resolve_host() == "override.local"
