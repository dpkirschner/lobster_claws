# Architecture Research

**Domain:** Python tools monorepo -- Docker-containerized CLIs + macOS host servers
**Researched:** 2026-03-17
**Confidence:** HIGH

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  OpenClaw Docker Container (node:24-bookworm)                   │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ claws-       │  │ claws-       │  │ claws-       │          │
│  │ transcribe   │  │ resy         │  │ spotify      │          │
│  │ (CLI)        │  │ (CLI)        │  │ (CLI)        │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│  ┌──────┴─────────────────┴─────────────────┴───────┐          │
│  │              claws-common                         │          │
│  │  (host resolution, HTTP client, error handling)   │          │
│  └──────────────────────┬────────────────────────────┘          │
│                         │                                       │
└─────────────────────────┼───────────────────────────────────────┘
                          │ HTTP (host.docker.internal:83XX)
                          │
┌─────────────────────────┼───────────────────────────────────────┐
│  Mac Mini Host (macOS)  │                                       │
│                         │                                       │
│  ┌──────────────┐  ┌────┴─────────┐  ┌──────────────┐          │
│  │ whisper-     │  │ resy-        │  │ spotify-     │          │
│  │ server       │  │ server       │  │ server       │          │
│  │ :8300        │  │ :8301        │  │ :8302        │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│       (FastAPI + uvicorn, managed by launchd)                   │
│                                                                 │
│  ┌──────────────────────────────────────────────────┐           │
│  │           servers-common                          │           │
│  │  (shared FastAPI base, health check, logging)     │           │
│  └──────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| `claws-common` | Host resolution, HTTP client wrapper, stdout formatting, error handling | Python package; `httpx` for HTTP, auto-detects Docker vs host |
| `claws-transcribe` | CLI entry point for audio transcription | Python package with `console_scripts` entry point; calls whisper server |
| `servers-common` | Shared FastAPI boilerplate: health endpoint, structured logging, error middleware | Python package; FastAPI app factory pattern |
| `whisper-server` | Audio transcription via mlx-whisper on Apple Silicon GPU | FastAPI app; `POST /transcribe` (multipart file upload), `GET /health` |
| `launchd plists` | Process supervision for host servers | `.plist` files in `~/Library/LaunchAgents/`, `RunAtLoad`, auto-restart |

## Recommended Monorepo Structure

```
lobster_claws/
├── pyproject.toml              # Root: workspace config, shared dev deps (ruff, pytest, mypy)
├── common/                     # claws-common (shared client library)
│   ├── pyproject.toml          # name = "claws-common"
│   ├── src/
│   │   └── claws_common/
│   │       ├── __init__.py
│   │       ├── client.py       # SkillClient base class (HTTP + stdout)
│   │       ├── host.py         # resolve_host(), _in_docker()
│   │       └── errors.py       # Standardized error output
│   └── tests/
├── skills/                     # Container-side CLIs
│   └── transcribe/
│       ├── pyproject.toml      # name = "claws-transcribe", depends on claws-common
│       ├── src/
│       │   └── claws_transcribe/
│       │       ├── __init__.py
│       │       └── cli.py      # Entry point: transcribe command
│       └── tests/
├── servers/                    # Host-side FastAPI servers
│   ├── common/
│   │   ├── pyproject.toml      # name = "servers-common"
│   │   ├── src/
│   │   │   └── servers_common/
│   │   │       ├── __init__.py
│   │   │       ├── app.py      # FastAPI app factory with /health
│   │   │       ├── logging.py  # Structured logging setup
│   │   │       └── middleware.py  # Error handling middleware
│   │   └── tests/
│   └── whisper/
│       ├── pyproject.toml      # name = "whisper-server", depends on servers-common
│       ├── src/
│       │   └── whisper_server/
│       │       ├── __init__.py
│       │       ├── app.py      # FastAPI app with /transcribe
│       │       └── models.py   # Request/response schemas
│       └── tests/
├── launchd/                    # launchd plist templates
│   └── com.lobsterclaws.whisper.plist
├── scripts/                    # Dev/ops helper scripts
│   ├── install-server.sh       # Install a server + register launchd
│   └── install-skill.sh        # Install a skill into Docker container
└── Makefile                    # Top-level dev commands
```

### Structure Rationale

- **`common/` at root level:** The client library is the foundational dependency. Keeping it top-level (not nested under `skills/`) signals its importance and simplifies path references.
- **`skills/` directory:** Groups all container-side CLIs. Each skill is an independent pip-installable package with its own `pyproject.toml`. Future claws (resy, spotify) just add a new subdirectory.
- **`servers/` directory with its own `common/`:** Host servers share boilerplate (health checks, logging, error middleware) but are distinct from the client-side common library. Servers have different dependencies (FastAPI, uvicorn, ML libraries) that should never leak into container packages.
- **`launchd/` directory:** Plist files are deployment artifacts, not Python packages. Separating them makes the install/uninstall workflow clear.
- **`src/` layout within each package:** Using the `src/` layout prevents accidental imports of uninstalled packages during development. This is the recommended Python packaging practice.

## Architectural Patterns

### Pattern 1: Thin CLI + Fat Server

**What:** Each skill CLI does almost nothing -- it parses arguments, calls `claws-common` to make an HTTP request to the host server, and prints the response to stdout. All business logic lives in the server.

**When to use:** Always. This is the core pattern of the project.

**Trade-offs:** Adds network latency for every call, but gains GPU access, centralized logging, and clean container isolation. The container stays "dumb" by design.

**Example:**
```python
# skills/transcribe/src/claws_transcribe/cli.py
import sys
from pathlib import Path
from claws_common.client import SkillClient

def main():
    if len(sys.argv) < 2:
        print("Usage: transcribe <audio_file>", file=sys.stderr)
        sys.exit(1)

    client = SkillClient(service="whisper", port=8300)
    result = client.post_file("/transcribe", Path(sys.argv[1]))
    print(result["text"])

# pyproject.toml: [project.scripts] transcribe = "claws_transcribe.cli:main"
```

### Pattern 2: FastAPI App Factory with Health Check

**What:** Each server uses a factory function that creates a FastAPI app with standardized health endpoints, error handling middleware, and structured logging. Servers share this via `servers-common`.

**When to use:** Every host server.

**Trade-offs:** Minor indirection for consistency across all servers.

**Example:**
```python
# servers/common/src/servers_common/app.py
from fastapi import FastAPI

def create_app(name: str, version: str = "0.1.0") -> FastAPI:
    app = FastAPI(title=name, version=version)

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": name}

    return app

# servers/whisper/src/whisper_server/app.py
from servers_common.app import create_app

app = create_app("whisper-server")

@app.post("/transcribe")
async def transcribe(file: UploadFile):
    # ... mlx-whisper inference ...
    return {"text": transcription}
```

### Pattern 3: Host Resolution Chain

**What:** `claws-common` resolves the host address using a priority chain: (1) `OPENCLAW_TOOLS_HOST` env var, (2) Docker detection via `/.dockerenv` or cgroup, (3) fallback to `127.0.0.1`.

**When to use:** Every HTTP call from container to host.

**Trade-offs:** The Docker detection heuristics can break in edge cases (nested containers, rootless Docker). The env var override provides an escape hatch.

### Pattern 4: Console Scripts Entry Points

**What:** Each skill registers a CLI command via `[project.scripts]` in `pyproject.toml`. After `pip install`, the command is available on `$PATH`. The OpenClaw agent invokes it as a subprocess.

**When to use:** Every skill.

**Trade-offs:** Simple and universal. No framework dependency (no click/typer needed for single-command tools). For skills with subcommands, add `argparse` as needed.

## Data Flow

### Primary Flow: Skill Invocation

```
OpenClaw Agent (Node.js)
    │
    │  subprocess: `transcribe /path/to/audio.wav`
    ↓
claws-transcribe CLI (Python, in container)
    │
    │  claws-common: resolve_host() → host.docker.internal
    │  HTTP POST multipart/form-data → host.docker.internal:8300/transcribe
    ↓
whisper-server (FastAPI, on Mac mini host)
    │
    │  mlx-whisper inference (Apple Silicon GPU)
    │  Returns JSON: {"text": "transcribed content..."}
    ↓
claws-transcribe CLI
    │
    │  Prints result to stdout
    ↓
OpenClaw Agent
    │  Captures stdout as tool result
    ↓
Agent response to user
```

### Error Flow

```
Skill CLI
    │
    ├── Server unreachable → stderr: "Error: whisper server not running on :8300"
    │                        exit code: 1
    │
    ├── Server returns 4xx/5xx → stderr: "Error: server returned 500: ..."
    │                             exit code: 1
    │
    └── Success → stdout: result text
                  exit code: 0
```

### Key Data Flows

1. **Audio transcription:** Agent subprocess calls CLI with file path. CLI reads file from shared volume (`~/.openclaw/media/`), POSTs to whisper server, prints text to stdout. The file path is accessible because the media directory is a bind mount visible to both container and host.

2. **Health checking:** Servers expose `GET /health`. Installation scripts or monitoring can verify servers are running. The `claws-common` client could optionally pre-check health before making requests, but this adds latency and is better left to the error flow.

3. **Installation:** Skills install via `pip install git+https://...#subdirectory=skills/transcribe`. This pulls `claws-common` as a dependency automatically. Servers install on the host via venv + pip, then register a launchd plist.

## Build Order (Dependency Graph)

```
Phase 1: claws-common
    │     (no dependencies on other project packages)
    │
    ├──→ Phase 2a: servers-common
    │         │     (no dependency on claws-common, parallel track)
    │         │
    │         └──→ Phase 3b: whisper-server
    │               (depends on servers-common)
    │
    └──→ Phase 2b: claws-transcribe
              (depends on claws-common)

Phase 4: launchd plists + install scripts
          (depends on servers existing)

Phase 5: Integration testing
          (depends on everything)
```

**Critical path:** `claws-common` must be built first. After that, the server track (`servers-common` then `whisper-server`) and the skill track (`claws-transcribe`) can proceed in parallel. The two tracks converge at integration testing.

Note: `servers-common` and `claws-common` have zero code dependency on each other. They live in different runtime environments (host vs container). Build them independently.

## Anti-Patterns

### Anti-Pattern 1: Fat CLI

**What people do:** Put business logic, ML model loading, or complex processing in the container-side CLI.
**Why it's wrong:** The container has no GPU, limited resources, and is meant to be a thin proxy. Complex logic in the CLI makes it hard to test, debug, and update independently.
**Do this instead:** Keep CLIs to argument parsing + HTTP call + stdout. All logic in the server.

### Anti-Pattern 2: Per-Service Host Variables

**What people do:** Create `WHISPER_HOST`, `RESY_HOST`, `SPOTIFY_HOST` -- a separate env var for each service.
**Why it's wrong:** All services run on the same host. Multiple variables means multiple things to configure and multiple places to get wrong.
**Do this instead:** Single `OPENCLAW_TOOLS_HOST` with per-service port numbers only.

### Anti-Pattern 3: Shared Python Package Between Container and Host

**What people do:** Make `claws-common` a dependency of both the CLI skills and the host servers, trying to share types/schemas.
**Why it's wrong:** Container and host have different Python versions, different OS, different dependency constraints. Coupling them through a shared package creates version hell.
**Do this instead:** Keep `claws-common` (container-side) and `servers-common` (host-side) completely separate. Use HTTP as the contract boundary. If you want schema validation on both sides, duplicate the simple Pydantic models -- it is cheaper than the coupling cost.

### Anti-Pattern 4: Running Servers Without Process Supervision

**What people do:** Start servers with `uvicorn app:app` in a terminal and forget about it.
**Why it's wrong:** Server dies silently after reboot, crash, or macOS sleep/wake. No logs, no restart.
**Do this instead:** Use launchd plists with `RunAtLoad`, `KeepAlive`, and `StandardOutPath`/`StandardErrorPath` for log capture.

### Anti-Pattern 5: Monolithic Server

**What people do:** Put all endpoints (transcribe, resy, spotify) in one big FastAPI app.
**Why it's wrong:** Different services have different dependencies (mlx-whisper vs resy API client vs spotify SDK). One server's dependency conflict or crash takes down everything.
**Do this instead:** One server per capability. Independent processes, independent failures, independent updates. The port convention (8300, 8301, 8302...) supports this naturally.

## Integration Points

### External: Container to Host

| Boundary | Protocol | Notes |
|----------|----------|-------|
| Skill CLI to Host Server | HTTP (host.docker.internal:83XX) | Multipart file upload for transcribe; JSON for others |
| Host Server to External APIs | HTTPS | Future servers (resy, spotify) proxy external API calls |
| Host Server to ML Models | Local (in-process) | mlx-whisper loaded in server process memory |

### Internal: Package Dependencies

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `claws-transcribe` to `claws-common` | Python import | Declared dependency in pyproject.toml |
| `whisper-server` to `servers-common` | Python import | Declared dependency in pyproject.toml |
| `claws-common` to `servers-common` | NONE | These must never depend on each other |

### Deployment: Installation Flow

| Target | Method | Notes |
|--------|--------|-------|
| Skills into container | `pip install git+...#subdirectory=skills/transcribe` | Pulls claws-common automatically |
| Servers on host | `pip install -e servers/whisper` in a venv | Separate venv per server recommended |
| launchd registration | `launchctl load ~/Library/LaunchAgents/com.lobsterclaws.whisper.plist` | Plist references venv Python path |

## Scaling Considerations

| Concern | Current (1 agent) | Future (multiple agents) |
|---------|-------------------|--------------------------|
| Server concurrency | Single uvicorn worker, async | Add `--workers N` to uvicorn; mlx-whisper is the bottleneck (GPU serialized) |
| Port management | Manual assignment (8300+) | Could add a service registry, but premature -- just document the mapping |
| Server isolation | One venv per server | Already isolated; no changes needed |
| Skill installation | pip from git URL | Consider building wheels and hosting them (e.g., GitHub Releases) if pip-from-git gets slow |

For this project's scale (single Mac mini, single OpenClaw instance), none of these scaling concerns are immediate. The one-server-per-capability pattern handles the foreseeable future.

## Sources

- [Python monorepo best practices (Graphite)](https://graphite.com/guides/python-monorepos) -- monorepo structure patterns
- [Python monorepo with UV (Naor David Melamed, Feb 2026)](https://medium.com/@naorcho/building-a-python-monorepo-with-uv-the-modern-way-to-manage-multi-package-projects-4cbcc56df1b4) -- workspace configuration
- [Tweag Python monorepo example](https://www.tweag.io/blog/2023-04-04-python-monorepo-1/) -- pyproject.toml per package, src layout
- [FastAPI manual deployment](https://fastapi.tiangolo.com/deployment/manually/) -- uvicorn server setup
- [launchd plist examples](https://alvinalexander.com/mac-os-x/launchd-examples-launchd-plist-file-examples-mac/) -- plist configuration
- [Python service as launchd agent (AndyPi)](https://andypi.co.uk/2023/02/14/how-to-run-a-python-script-as-a-service-on-mac-os/) -- Python + launchd integration
- [launchd.plist man page](https://keith.github.io/xcode-man-pages/launchd.plist.5.html) -- official plist reference
- Project context: `.planning/PROJECT.md`, `data.md` (OpenClaw integration cheatsheet)

---
*Architecture research for: Python tools monorepo (Docker CLI skills + macOS host servers)*
*Researched: 2026-03-17*
