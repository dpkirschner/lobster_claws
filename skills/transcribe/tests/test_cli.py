"""Tests for claws-transcribe CLI."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def tmp_audio(tmp_path):
    """Create a temporary audio file."""
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake audio data")
    return audio_file


@pytest.fixture
def mock_client():
    """Create a mock ClawsClient."""
    with patch("claws_transcribe.cli.ClawsClient") as mock_cls:
        client = MagicMock()
        mock_cls.return_value = client
        client.post_file.return_value = {"text": "hello world", "segments": []}
        yield client, mock_cls


class TestTranscribeCLI:
    def test_transcribe_success(self, tmp_audio, mock_client):
        """main() with valid file calls post_file and prints response text via result()."""
        client, mock_cls = mock_client
        with (
            patch("sys.argv", ["claws-transcribe", str(tmp_audio)]),
            patch("claws_transcribe.cli.result") as mock_result,
        ):
            from claws_transcribe.cli import main

            main()

            mock_cls.assert_called_once_with(service="whisper", port=8300, timeout=300.0)
            client.post_file.assert_called_once_with("/transcribe", str(tmp_audio))
            mock_result.assert_called_once_with("hello world")

    def test_transcribe_json_format(self, tmp_audio, mock_client):
        """main() with --format json calls result() with the full response dict."""
        client, mock_cls = mock_client
        with (
            patch("sys.argv", ["claws-transcribe", str(tmp_audio), "--format", "json"]),
            patch("claws_transcribe.cli.result") as mock_result,
        ):
            from claws_transcribe.cli import main

            main()

            mock_result.assert_called_once_with({"text": "hello world", "segments": []})

    def test_transcribe_text_format(self, tmp_audio, mock_client):
        """main() with --format text calls result() with response['text']."""
        client, mock_cls = mock_client
        with (
            patch("sys.argv", ["claws-transcribe", str(tmp_audio), "--format", "text"]),
            patch("claws_transcribe.cli.result") as mock_result,
        ):
            from claws_transcribe.cli import main

            main()

            mock_result.assert_called_once_with("hello world")

    def test_model_flag(self, tmp_audio, mock_client):
        """main() with --model passes model kwarg to post_file."""
        client, mock_cls = mock_client
        model = "mlx-community/whisper-large-v3-mlx"
        with (
            patch("sys.argv", ["claws-transcribe", str(tmp_audio), "--model", model]),
            patch("claws_transcribe.cli.result"),
        ):
            from claws_transcribe.cli import main

            main()

            client.post_file.assert_called_once_with(
                "/transcribe", str(tmp_audio), model=model
            )

    def test_file_not_found(self, mock_client):
        """main() with nonexistent path calls fail()."""
        with (
            patch("sys.argv", ["claws-transcribe", "/nonexistent/audio.wav"]),
            patch("claws_transcribe.cli.fail", side_effect=SystemExit(1)) as mock_fail,
        ):
            from claws_transcribe.cli import main

            with pytest.raises(SystemExit):
                main()

            mock_fail.assert_called_once()
            assert "not found" in mock_fail.call_args[0][0].lower()

    def test_connection_error(self, tmp_audio, mock_client):
        """ClawsClient.post_file raises ConnectionError -> main() calls crash()."""
        client, mock_cls = mock_client
        client.post_file.side_effect = ConnectionError("Connection refused")
        with (
            patch("sys.argv", ["claws-transcribe", str(tmp_audio)]),
            patch("claws_transcribe.cli.crash", side_effect=SystemExit(2)) as mock_crash,
        ):
            from claws_transcribe.cli import main

            with pytest.raises(SystemExit):
                main()

            mock_crash.assert_called_once()

    def test_timeout_error(self, tmp_audio, mock_client):
        """ClawsClient.post_file raises TimeoutError -> main() calls crash()."""
        client, mock_cls = mock_client
        client.post_file.side_effect = TimeoutError("Request timed out")
        with (
            patch("sys.argv", ["claws-transcribe", str(tmp_audio)]),
            patch("claws_transcribe.cli.crash", side_effect=SystemExit(2)) as mock_crash,
        ):
            from claws_transcribe.cli import main

            with pytest.raises(SystemExit):
                main()

            mock_crash.assert_called_once()
