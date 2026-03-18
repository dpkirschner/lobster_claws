"""CLI entry point for claws-transcribe audio transcription skill."""

import argparse
from pathlib import Path

from claws_common.client import ClawsClient
from claws_common.output import crash, fail, result


def main():
    """Transcribe an audio file via the whisper server."""
    parser = argparse.ArgumentParser(
        prog="claws-transcribe",
        description="Transcribe audio files via whisper server",
    )
    parser.add_argument("file", help="Path to audio file")
    parser.add_argument(
        "--model",
        help="Whisper model to use (e.g. mlx-community/whisper-large-v3-mlx)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args()

    if not Path(args.file).exists():
        fail(f"File not found: {args.file}")

    client = ClawsClient(service="whisper", port=8300, timeout=300.0)

    params = {}
    if args.model:
        params["model"] = args.model

    try:
        response = client.post_file("/transcribe", str(Path(args.file)), **params)
    except ConnectionError as e:
        crash(str(e))
    except TimeoutError as e:
        crash(str(e))

    if args.format == "json":
        result(response)
    else:
        result(response["text"])


if __name__ == "__main__":
    main()
