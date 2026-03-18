# Lobster Claws

AI agent skills as thin container CLIs paired with macOS host servers. Each skill follows one pattern: CLI in container sends HTTP to host server, prints result to stdout.

## Architecture Overview

Lobster Claws uses a two-layer design:

- **Skills** (CLIs) run inside the OpenClaw Docker container (`node:24-bookworm`). They are pip-installed Python packages that parse arguments, call a host server over HTTP, and print structured output.
- **Servers** run on the Mac mini host (macOS, Apple Silicon). They do the heavy lifting -- ML inference, API calls, anything that needs GPU or persistent state.

Communication flows from container to host via `host.docker.internal` (or the `OPENCLAW_TOOLS_HOST` env var override).

```
+----------------------------------+          +----------------------------------+
|  OpenClaw Container              |          |  Mac mini Host                   |
|  (node:24-bookworm)              |          |  (macOS, Apple Silicon)          |
|                                  |          |                                  |
|  claws-transcribe audio.wav      |  --HTTP-->  whisper-server :8300            |
|                                  |          |  (FastAPI + mlx-whisper)         |
+----------------------------------+          +----------------------------------+
```

## Repository Structure

```
lobster_claws/
  common/              # claws-common: shared client library (host resolution, HTTP, output)
  cli/                 # claws-cli: meta-CLI for skill discovery and routing
  skills/
    transcribe/        # claws-transcribe: audio transcription via whisper
  servers/
    whisper/           # whisper-server: FastAPI + mlx-whisper on Apple Silicon
  launchd/             # launchd plists for server auto-start
  pyproject.toml       # uv workspace root
```

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

### Dev Setup

```bash
git clone <repo-url> lobster_claws
cd lobster_claws
uv sync
uv run claws          # verify installation -- lists available skills
```

### Container Installation

Install skills into the OpenClaw container (Debian Bookworm requires `--break-system-packages`):

```bash
pip install --break-system-packages \
    git+https://github.com/yourorg/lobster_claws.git#subdirectory=common \
    git+https://github.com/yourorg/lobster_claws.git#subdirectory=skills/transcribe
```

Set the host resolution env var in your container environment:

```bash
export OPENCLAW_TOOLS_HOST=host.docker.internal
```

## Available Skills

### transcribe

Transcribe audio files via the whisper server.

```bash
claws transcribe <audio-file> [--model MODEL] [--format text|json]
```

- Sends audio to the whisper server on the host
- `--model` selects a specific whisper model (e.g. `mlx-community/whisper-large-v3-mlx`)
- `--format json` returns the full response object instead of plain text
- Talks to: `whisper-server` on port 8300

## Server Setup

### Whisper Server

The whisper server runs FastAPI with mlx-whisper on Apple Silicon. Default port: **8300**.

**Start manually:**

```bash
uv run uvicorn whisper_server.app:app --host 0.0.0.0 --port 8300
```

**Auto-start via launchd:**

The plist at `launchd/com.lobsterclaws.whisper.plist` configures auto-start on boot and auto-restart on crash. Install it:

```bash
cp launchd/com.lobsterclaws.whisper.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.lobsterclaws.whisper.plist
```

**Health check:**

```bash
curl http://localhost:8300/health
```

## Adding a New Skill

Each skill is a "claw" -- a pip-installable CLI that follows the same pattern.

### Step by step

1. **Create the skill directory:**

   ```
   skills/<name>/
     src/claws_<name>/
       __init__.py
       cli.py
     tests/
       __init__.py
     pyproject.toml
   ```

2. **Create `pyproject.toml`** with the claws-common dependency, a console script entry, and the `claws.skills` entry point for discovery:

   ```toml
   [project]
   name = "claws-<name>"
   version = "0.1.0"
   requires-python = ">=3.12"
   dependencies = ["claws-common"]

   [build-system]
   requires = ["hatchling"]
   build-backend = "hatchling.build"

   [project.scripts]
   claws-<name> = "claws_<name>.cli:main"

   [project.entry-points."claws.skills"]
   <name> = "claws_<name>.cli:main"

   [tool.uv.sources]
   claws-common = { workspace = true }
   ```

   The `[project.scripts]` entry makes `claws-<name>` available as a standalone command. The `[project.entry-points."claws.skills"]` entry registers the skill for automatic discovery by the `claws` meta-CLI.

3. **Create `src/claws_<name>/cli.py`** following the pattern:

   ```python
   import argparse
   from claws_common.client import ClawsClient
   from claws_common.output import crash, fail, result

   def main():
       parser = argparse.ArgumentParser(prog="claws-<name>")
       # add arguments...
       args = parser.parse_args()

       client = ClawsClient(service="<server-name>", port=<port>)
       try:
           response = client.post("/endpoint", data={...})
       except (ConnectionError, TimeoutError) as e:
           crash(str(e))

       result(response)
   ```

4. **Create a corresponding server** (if needed) in `servers/<name>/` with a FastAPI app exposing at minimum `GET /health` and whatever endpoints the skill calls.

5. **Register in root `pyproject.toml`:**

   Add to dev dependencies and uv sources:

   ```toml
   [dependency-groups]
   dev = [..., "claws-<name>"]

   [tool.uv.sources]
   claws-<name> = { workspace = true }
   ```

6. **Sync the workspace:**

   ```bash
   uv sync
   ```

7. **Verify:**

   ```bash
   uv run claws       # should list the new skill
   ```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPENCLAW_TOOLS_HOST` | `host.docker.internal` in Docker, `127.0.0.1` on host | Override host resolution for all skills |
| `WHISPER_SERVER_PORT` | `8300` | Whisper server port |
| `WHISPER_MODEL` | `mlx-community/whisper-turbo` | Default whisper model for transcription |

## Development

### Running tests

```bash
uv run pytest
```

### Linting

```bash
uv run ruff check .
```

### Workspace structure

This project uses [uv workspaces](https://docs.astral.sh/uv/concepts/workspaces/). The root `pyproject.toml` defines workspace members:

```toml
[tool.uv.workspace]
members = ["common", "skills/*", "servers/*"]
```

Each package (`common/`, `skills/transcribe/`, `servers/whisper/`) is an independent Python package with its own `pyproject.toml`. Adding a new workspace member means creating the package directory with a `pyproject.toml` and adding it to the root dev dependencies.
