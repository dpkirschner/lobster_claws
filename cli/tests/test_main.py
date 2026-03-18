"""Tests for claws meta-CLI discovery and routing."""

from unittest.mock import MagicMock, patch

import pytest

from claws_cli.main import discover_skills, main


class TestDiscoverSkills:
    """Tests for the discover_skills function."""

    def test_returns_dict_of_entry_points(self):
        """discover_skills returns a dict mapping skill names to entry points."""
        mock_ep = MagicMock()
        mock_ep.name = "transcribe"

        with patch("claws_cli.main.entry_points", return_value=[mock_ep]):
            skills = discover_skills()

        assert isinstance(skills, dict)
        assert "transcribe" in skills
        assert skills["transcribe"] is mock_ep

    def test_returns_empty_dict_when_no_skills(self):
        """discover_skills returns empty dict when no skills installed."""
        with patch("claws_cli.main.entry_points", return_value=[]):
            skills = discover_skills()

        assert skills == {}


class TestMainNoArgs:
    """Tests for claws with no arguments."""

    def test_lists_available_skills(self, capsys):
        """claws with no args prints list including 'transcribe' and exits 0."""
        mock_ep = MagicMock()
        mock_ep.name = "transcribe"

        with (
            patch("claws_cli.main.discover_skills", return_value={"transcribe": mock_ep}),
            patch("sys.argv", ["claws"]),
        ):
            main()

        captured = capsys.readouterr()
        assert "transcribe" in captured.out

    def test_no_skills_found_message(self, capsys):
        """claws with no args and no skills prints 'no skills found' message."""
        with (
            patch("claws_cli.main.discover_skills", return_value={}),
            patch("sys.argv", ["claws"]),
        ):
            main()

        captured = capsys.readouterr()
        assert "no skills" in captured.out.lower() or "No skills" in captured.out


class TestMainRouting:
    """Tests for skill routing."""

    def test_routes_to_known_skill(self):
        """claws transcribe routes to the transcribe skill's main function."""
        mock_fn = MagicMock()
        mock_ep = MagicMock()
        mock_ep.name = "transcribe"
        mock_ep.load.return_value = mock_fn

        with (
            patch("claws_cli.main.discover_skills", return_value={"transcribe": mock_ep}),
            patch("sys.argv", ["claws", "transcribe", "audio.wav"]),
        ):
            main()

        mock_ep.load.assert_called_once()
        mock_fn.assert_called_once()

    def test_sets_sys_argv_for_skill(self):
        """Before calling skill, sys.argv is set so skill's argparse works."""
        captured_argv = []

        def capture_argv():
            import sys

            captured_argv.extend(sys.argv)

        mock_ep = MagicMock()
        mock_ep.name = "transcribe"
        mock_ep.load.return_value = capture_argv

        with (
            patch("claws_cli.main.discover_skills", return_value={"transcribe": mock_ep}),
            patch("sys.argv", ["claws", "transcribe", "audio.wav"]),
        ):
            main()

        assert captured_argv == ["transcribe", "audio.wav"]

    def test_unknown_skill_prints_error_and_exits_2(self, capsys):
        """claws unknown-skill prints error to stderr and exits 2."""
        with (
            patch("claws_cli.main.discover_skills", return_value={}),
            patch("sys.argv", ["claws", "unknown-skill"]),
            pytest.raises(SystemExit, match="2"),
        ):
            main()

        captured = capsys.readouterr()
        assert "unknown-skill" in captured.err.lower() or "unknown-skill" in captured.err
