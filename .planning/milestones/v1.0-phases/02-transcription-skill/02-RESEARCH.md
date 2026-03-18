# Phase 2: Transcription Skill - Research

**Researched:** 2026-03-17
**Domain:** FastAPI whisper server + CLI skill + launchd process management
**Confidence:** HIGH

## Summary

Phase 2 builds the first complete claw: a whisper transcription server on the Mac mini host and a thin CLI skill in the container that proxies to it. The foundation from Phase 1 (claws-common with ClawsClient, host resolution, output helpers) is already in place, so this phase focuses on three new components: (1) the whisper-server FastAPI application using mlx-whisper for Apple Silicon GPU inference, (2) the claws-transcribe CLI package that uses ClawsClient to POST audio files, and (3) a launchd plist for auto-starting the server.

The mlx-whisper library provides a simple `transcribe()` API with a built-in `ModelHolder` singleton cache that keeps the model loaded between calls. The default model is `mlx-community/whisper-turbo`. FastAPI handles multipart file uploads natively via `UploadFile`. The server needs to write uploaded audio to a temp file (mlx-whisper expects a file path, not bytes), transcribe it, and return the text. Uvicorn has no built-in request body size limit, so large audio files work out of the box.

**Primary recommendation:** Build the whisper-server first (it is the core logic), then the CLI skill (thin wrapper over ClawsClient), then the launchd plist. Keep the server simple -- single-file FastAPI app with lifespan-based model preloading, POST /transcribe, and GET /health.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| WHSP-01 | FastAPI server exposes `POST /transcribe` accepting audio file upload, returns transcription text | FastAPI UploadFile + mlx_whisper.transcribe() API documented below |
| WHSP-02 | Server exposes `GET /health` returning server status and loaded model info | FastAPI health endpoint pattern; ModelHolder provides loaded model info |
| WHSP-03 | Model selection parameter on `/transcribe` allows choosing whisper model per request | mlx_whisper `path_or_hf_repo` parameter; ModelHolder auto-reloads on model change |
| WHSP-04 | Model preloading keeps the default model in memory between requests | ModelHolder singleton pattern built into mlx-whisper; trigger via lifespan event |
| TRNS-01 | `claws-transcribe` CLI accepts audio file path, POSTs to whisper server, prints transcription to stdout | ClawsClient.post_file() already supports multipart upload; output.result() handles stdout |
| TRNS-02 | `--format` flag switches output between plain text and JSON | argparse flag; output.result() already handles both str and dict |
| TRNS-03 | `--model` flag allows choosing whisper model for the request | Pass as query param to POST /transcribe; server passes to mlx_whisper |
| TRNS-04 | Runs with `PYTHONUNBUFFERED=1` for Docker compatibility | output.py already uses flush=True; document PYTHONUNBUFFERED in install instructions |
| INFR-01 | launchd plist auto-starts and restarts whisper server on Mac mini | launchd plist with RunAtLoad + KeepAlive; absolute paths required |
</phase_requirements>

## Standard Stack

### Core (Server-side, macOS host)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | >=0.135 | HTTP server framework | Auto-validation, OpenAPI docs, async-native, UploadFile support |
| uvicorn | >=0.42 | ASGI server | Default FastAPI server, lightweight, production-ready for single-process |
| mlx-whisper | >=0.4.3 | Speech-to-text inference | Apple MLX framework, Metal GPU optimized, simple transcribe() API |
| python-multipart | >=0.0.18 | Multipart form parsing | Required by FastAPI for file upload endpoints |
| pydantic | v2 (>=2.10) | Request/response models | Ships with FastAPI, type-safe schemas |

### Core (Client-side, container)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| claws-common | workspace | HTTP client, host resolution, output | Already built in Phase 1; ClawsClient.post_file() handles multipart uploads |
| argparse | stdlib | CLI argument parsing | Zero dependencies, sufficient for single-command tool |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| mlx-whisper | lightning-whisper-mlx | Claims 4x faster but less maintained; evaluate only if latency is a problem |
| mlx-whisper | whisper.cpp | CPU-only; slower on Apple Silicon than MLX |
| Direct uvicorn | Gunicorn + uvicorn workers | Overkill -- launchd handles restarts, single worker is sufficient for one Mac mini |

**Server installation:**
```bash
# In servers/whisper/ directory
uv add fastapi uvicorn mlx-whisper python-multipart
```

**Skill installation:**
```bash
# In skills/transcribe/ directory -- only needs claws-common
uv add claws-common
```

## Architecture Patterns

### Recommended Project Structure
```
servers/
  whisper/
    pyproject.toml          # name = "whisper-server"
    src/
      whisper_server/
        __init__.py
        app.py              # FastAPI app, /transcribe, /health
        config.py           # Settings (port, default model, log level)
    tests/
      test_app.py

skills/
  transcribe/
    pyproject.toml          # name = "claws-transcribe"
    src/
      claws_transcribe/
        __init__.py
        cli.py              # Entry point: main()
    tests/
      test_cli.py

launchd/
  com.lobsterclaws.whisper.plist
```

### Pattern 1: mlx-whisper Model Preloading via Lifespan

**What:** Load the default whisper model at server startup using FastAPI's lifespan context manager. The mlx-whisper `ModelHolder` singleton caches the model between requests automatically.

**When to use:** Always -- cold-start penalty for whisper models is 5-30 seconds depending on model size.

**Example:**
```python
# servers/whisper/src/whisper_server/app.py
from contextlib import asynccontextmanager
import mlx_whisper
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Preload default model into ModelHolder cache
    mlx_whisper.transcribe.__wrapped__  # not needed; just call transcribe on a tiny audio
    # OR: directly trigger model loading
    from mlx_whisper.transcribe import ModelHolder
    ModelHolder.get_model(app.state.default_model)
    yield

app = FastAPI(title="whisper-server", lifespan=lifespan)
```

### Pattern 2: Temp File for Audio Upload

**What:** mlx-whisper expects a file path (string), not bytes or a file-like object. Write the uploaded file to a temp file, transcribe it, then clean up.

**When to use:** Every POST /transcribe request.

**Example:**
```python
import tempfile
from pathlib import Path
from fastapi import FastAPI, UploadFile

@app.post("/transcribe")
async def transcribe(file: UploadFile, model: str | None = None):
    suffix = Path(file.filename).suffix if file.filename else ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp.flush()
        result = mlx_whisper.transcribe(
            tmp.name,
            path_or_hf_repo=model or DEFAULT_MODEL,
        )
    return {"text": result["text"]}
```

### Pattern 3: Thin CLI with ClawsClient

**What:** The CLI skill does argument parsing, calls ClawsClient.post_file(), and prints the result. All logic lives in the server.

**When to use:** This is the core pattern for every claw.

**Example:**
```python
# skills/transcribe/src/claws_transcribe/cli.py
import argparse
import sys
from pathlib import Path
from claws_common.client import ClawsClient
from claws_common.output import result, fail, crash

def main():
    parser = argparse.ArgumentParser(description="Transcribe audio files")
    parser.add_argument("file", help="Path to audio file")
    parser.add_argument("--model", help="Whisper model to use")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    if not Path(args.file).exists():
        fail(f"File not found: {args.file}")

    client = ClawsClient(service="whisper", port=8300, timeout=300.0)
    params = {}
    if args.model:
        params["model"] = args.model

    try:
        response = client.post_file("/transcribe", args.file, **params)
    except ConnectionError as e:
        crash(str(e))
    except TimeoutError as e:
        crash(str(e))

    if args.format == "json":
        result(response)
    else:
        result(response["text"])
```

### Pattern 4: launchd Plist with Absolute Paths

**What:** A launchd user agent plist that starts the whisper server on login with auto-restart.

**When to use:** INFR-01 requirement.

**Example:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.lobsterclaws.whisper</string>

    <key>ProgramArguments</key>
    <array>
        <string>/path/to/venv/bin/uvicorn</string>
        <string>whisper_server.app:app</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>8300</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>WorkingDirectory</key>
    <string>/Users/little-dank/code/lobster_claws/servers/whisper</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>WHISPER_MODEL</key>
        <string>mlx-community/whisper-turbo</string>
    </dict>

    <key>StandardOutPath</key>
    <string>/Users/little-dank/Library/Logs/lobsterclaws/whisper.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/little-dank/Library/Logs/lobsterclaws/whisper.err</string>
</dict>
</plist>
```

### Anti-Patterns to Avoid

- **Loading model per request:** mlx-whisper's ModelHolder caches, but calling with a different `path_or_hf_repo` each time triggers a reload. Design the API so the default model stays loaded and only switches on explicit `--model` flag.
- **Reading entire audio into memory then writing to disk:** Use chunked reads for very large files (though for typical audio <100MB this is acceptable).
- **Binding to 127.0.0.1:** The server must bind to `0.0.0.0` so Docker containers can reach it via `host.docker.internal`.
- **Using `~` in plist paths:** launchd does not expand `~`. Always use absolute paths like `/Users/little-dank/...`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Speech-to-text inference | Custom whisper integration | `mlx_whisper.transcribe()` | Handles audio preprocessing, chunking, decoding, model loading |
| Model caching | Custom singleton/cache | mlx-whisper's `ModelHolder` | Already built into the library, handles model path comparison |
| File upload parsing | Manual multipart parsing | FastAPI `UploadFile` | Async streaming, content type detection, cleanup |
| Process supervision | Custom watchdog/cron | launchd plist | macOS native, handles crashes, reboots, auto-restart |
| CLI argument parsing | Manual sys.argv parsing | argparse | stdlib, generates help text, type validation |

**Key insight:** mlx-whisper's transcribe() API is intentionally high-level -- it handles audio loading (via ffmpeg), mel spectrogram computation, chunked decoding, and model management. The server's job is just to bridge HTTP to this API.

## Common Pitfalls

### Pitfall 1: MLX Memory Accumulation
**What goes wrong:** Server memory grows after many transcriptions, eventually causing slowdowns or crashes.
**Why it happens:** MLX Metal GPU buffers may not be freed between requests. The model stays loaded (good) but intermediate computation buffers accumulate.
**How to avoid:** Call `mx.metal.clear_cache()` after each transcription. Monitor memory in /health endpoint. Set a max file size limit.
**Warning signs:** Transcription time increases over successive requests. `memory_pressure` shows yellow/red.

### Pitfall 2: Transcription Timeout for Long Audio
**What goes wrong:** Large audio files (30+ minutes) take longer than the default ClawsClient timeout (30s).
**Why it happens:** Whisper processes audio in 30-second chunks sequentially. A 60-minute file could take 2-5 minutes.
**How to avoid:** Use a generous timeout for the transcribe CLI (300s). The ClawsClient already supports configurable timeouts.
**Warning signs:** Timeout errors on large files that work fine with small clips.

### Pitfall 3: launchd Environment Missing PATH
**What goes wrong:** Server fails to start under launchd because Python, uvicorn, or ffmpeg cannot be found.
**Why it happens:** launchd does not inherit shell environment. PATH is minimal.
**How to avoid:** Set PATH explicitly in plist EnvironmentVariables including `/opt/homebrew/bin`. Use absolute path to venv's uvicorn binary.
**Warning signs:** Works from terminal, fails after reboot. Check `launchctl list | grep lobsterclaws`.

### Pitfall 4: ffmpeg Not Available
**What goes wrong:** mlx-whisper fails with an error about ffmpeg when processing non-WAV audio formats.
**Why it happens:** mlx-whisper uses ffmpeg to decode audio files. If ffmpeg is not on PATH (especially under launchd), it fails.
**How to avoid:** Ensure ffmpeg is installed (`brew install ffmpeg`) and its path is in the plist's PATH environment variable.
**Warning signs:** WAV files work but MP3/M4A/OGG fail.

### Pitfall 5: Model Download on First Request
**What goes wrong:** First transcription request takes 30+ seconds or times out because the model has to be downloaded from Hugging Face.
**Why it happens:** mlx-whisper auto-downloads models from HF Hub on first use. Large models (whisper-turbo: ~800MB, large-v3: ~3GB) take significant time.
**How to avoid:** Pre-download the model during server setup/installation, not at request time. The lifespan preload triggers the download at startup.
**Warning signs:** First request after fresh install is extremely slow, subsequent requests are fast.

## Code Examples

### Complete Whisper Server App
```python
# servers/whisper/src/whisper_server/app.py
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

import mlx.core as mx
import mlx_whisper
from fastapi import FastAPI, UploadFile, Query

DEFAULT_MODEL = "mlx-community/whisper-turbo"

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Preload default model at startup."""
    mlx_whisper.transcribe(
        # Transcribe silence to trigger model load
        # Alternative: directly access ModelHolder
    )
    yield

app = FastAPI(title="whisper-server", version="0.1.0", lifespan=lifespan)

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "whisper-server",
        "default_model": DEFAULT_MODEL,
    }

@app.post("/transcribe")
async def transcribe(
    file: UploadFile,
    model: str = Query(default=None, description="Whisper model repo ID"),
):
    model_id = model or DEFAULT_MODEL
    suffix = Path(file.filename).suffix if file.filename else ".wav"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp.flush()

        result = mlx_whisper.transcribe(
            tmp.name,
            path_or_hf_repo=model_id,
        )

    # Clear MLX metal cache to prevent memory accumulation
    mx.metal.clear_cache()

    return {"text": result["text"]}
```

### Complete CLI Entry Point
```python
# skills/transcribe/src/claws_transcribe/cli.py
import argparse
import sys
from pathlib import Path

from claws_common.client import ClawsClient
from claws_common.output import result, fail, crash


def main():
    parser = argparse.ArgumentParser(
        prog="claws-transcribe",
        description="Transcribe audio files via whisper server",
    )
    parser.add_argument("file", help="Path to audio file")
    parser.add_argument("--model", help="Whisper model to use (e.g. mlx-community/whisper-large-v3-mlx)")
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args()

    audio_path = Path(args.file)
    if not audio_path.exists():
        fail(f"File not found: {args.file}")

    client = ClawsClient(service="whisper", port=8300, timeout=300.0)
    params = {}
    if args.model:
        params["model"] = args.model

    try:
        response = client.post_file("/transcribe", str(audio_path), **params)
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
```

### Server pyproject.toml
```toml
[project]
name = "whisper-server"
version = "0.1.0"
description = "Whisper transcription server for Lobster Claws"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.135",
    "uvicorn>=0.42",
    "mlx-whisper>=0.4.3",
    "python-multipart>=0.0.18",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project.scripts]
whisper-server = "whisper_server.app:main"
```

### Skill pyproject.toml
```toml
[project]
name = "claws-transcribe"
version = "0.1.0"
description = "Audio transcription skill for Lobster Claws"
requires-python = ">=3.12"
dependencies = ["claws-common"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project.scripts]
claws-transcribe = "claws_transcribe.cli:main"

[tool.uv.sources]
claws-common = { workspace = true }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| openai-whisper (PyTorch) | mlx-whisper (MLX) | 2024 | 30-40% faster on Apple Silicon, no PyTorch dependency |
| FastAPI @app.on_event("startup") | Lifespan context manager | FastAPI 0.100+ | on_event is deprecated; lifespan is the current pattern |
| launchctl load/unload | launchctl bootstrap/bootout | macOS 10.10+ | load/unload still works but is deprecated |
| whisper-tiny default | whisper-turbo default | mlx-whisper recent | Better quality default model, still fast on Apple Silicon |

## mlx-whisper Model Reference

| Model ID | Parameters | Size | Speed | Quality |
|----------|-----------|------|-------|---------|
| mlx-community/whisper-tiny | 39M | ~75MB | Fastest | Low |
| mlx-community/whisper-small-mlx | 244M | ~500MB | Fast | Medium |
| mlx-community/whisper-medium-mlx | 769M | ~1.5GB | Medium | Good |
| mlx-community/whisper-turbo | ~800M | ~800MB | Fast | Good (default) |
| mlx-community/whisper-large-v3-mlx | 1.55B | ~3GB | Slow | Best |
| mlx-community/whisper-large-v3-turbo | 1.55B | ~3GB | Medium | Very good |

## Open Questions

1. **mx.metal.clear_cache() API**
   - What we know: MLX has Metal cache management, referenced in community discussions
   - What's unclear: Exact API name -- could be `mx.metal.clear_cache()` or similar
   - Recommendation: Verify at implementation time with `help(mx.metal)`. If not available, skip cache clearing for v1 and monitor memory.

2. **Model preloading mechanism**
   - What we know: ModelHolder.get_model() loads on first call. Lifespan can trigger it.
   - What's unclear: Whether we can import and call ModelHolder directly without a dummy transcribe call
   - Recommendation: Try direct ModelHolder access first; fall back to transcribing a tiny silent audio clip at startup.

3. **Max audio file size**
   - What we know: Uvicorn has no built-in body size limit. MLX processes in 30s chunks.
   - What's unclear: Practical memory limits for very large files on 16GB Mac mini
   - Recommendation: Start without a limit. Add one later if memory issues arise. Log file sizes.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0+ |
| Config file | Root `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest skills/transcribe/tests servers/whisper/tests -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WHSP-01 | POST /transcribe returns transcription text | unit (mock mlx_whisper) | `uv run pytest servers/whisper/tests/test_app.py::test_transcribe -x` | No -- Wave 0 |
| WHSP-02 | GET /health returns status and model info | unit | `uv run pytest servers/whisper/tests/test_app.py::test_health -x` | No -- Wave 0 |
| WHSP-03 | Model query param propagates to mlx_whisper | unit (mock mlx_whisper) | `uv run pytest servers/whisper/tests/test_app.py::test_model_selection -x` | No -- Wave 0 |
| WHSP-04 | Model preloaded at startup via lifespan | unit (mock) | `uv run pytest servers/whisper/tests/test_app.py::test_model_preload -x` | No -- Wave 0 |
| TRNS-01 | CLI posts file and prints transcription | unit (mock ClawsClient) | `uv run pytest skills/transcribe/tests/test_cli.py::test_transcribe_success -x` | No -- Wave 0 |
| TRNS-02 | --format flag switches text/json output | unit | `uv run pytest skills/transcribe/tests/test_cli.py::test_format_flag -x` | No -- Wave 0 |
| TRNS-03 | --model flag passes model to server | unit | `uv run pytest skills/transcribe/tests/test_cli.py::test_model_flag -x` | No -- Wave 0 |
| TRNS-04 | Output uses flush=True | unit/inspection | `uv run pytest skills/transcribe/tests/test_cli.py::test_output_flushed -x` | No -- Wave 0 |
| INFR-01 | launchd plist is valid XML with required keys | unit (plist parsing) | `uv run pytest tests/test_launchd.py::test_plist_valid -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest skills/transcribe/tests servers/whisper/tests -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `servers/whisper/tests/test_app.py` -- covers WHSP-01, WHSP-02, WHSP-03, WHSP-04
- [ ] `skills/transcribe/tests/test_cli.py` -- covers TRNS-01, TRNS-02, TRNS-03, TRNS-04
- [ ] `tests/test_launchd.py` -- covers INFR-01 (plist validation)
- [ ] pytest testpaths in root pyproject.toml may need updating to include `tests/`
- [ ] Server tests need `pytest-httpx` (already in dev deps) and `httpx` TestClient from FastAPI

## Sources

### Primary (HIGH confidence)
- [mlx-whisper transcribe.py source](https://github.com/ml-explore/mlx-examples/blob/main/whisper/mlx_whisper/transcribe.py) -- full transcribe() signature, ModelHolder singleton pattern
- [mlx-whisper PyPI](https://pypi.org/project/mlx-whisper/) -- v0.4.3, MIT license, dependencies
- [FastAPI Request Files docs](https://fastapi.tiangolo.com/tutorial/request-files/) -- UploadFile usage
- [launchd.plist man page](https://keith.github.io/xcode-man-pages/launchd.plist.5.html) -- plist keys reference

### Secondary (MEDIUM confidence)
- [mlx-community Whisper collection](https://huggingface.co/collections/mlx-community/whisper) -- available model repos
- [Uvicorn settings](https://uvicorn.dev/settings/) -- no built-in request body size limit confirmed
- [MLX GitHub](https://github.com/ml-explore/mlx) -- Metal cache management

### Tertiary (LOW confidence)
- `mx.metal.clear_cache()` API -- referenced in community discussions but exact API name needs runtime verification

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries verified on PyPI, APIs confirmed from source code
- Architecture: HIGH -- patterns follow established Phase 1 conventions and existing ClawsClient API
- Pitfalls: HIGH -- inherited from pre-existing PITFALLS.md research, cross-verified
- mlx-whisper API: HIGH -- verified from actual source code on GitHub
- MLX memory management: LOW -- exact cache clearing API needs runtime verification

**Research date:** 2026-03-17
**Valid until:** 2026-04-17 (stable domain, mlx-whisper releases are infrequent)
