# Lobster Claws

## What This Is

A Python monorepo of "claws" — lightweight CLI skills that give the OpenClaw AI agent new capabilities. Each claw is a pip-installable package that runs inside the OpenClaw Docker container and communicates with a corresponding server on the Mac mini host. The agent is the lobster; each skill is another claw that lets it do something new. A unified `claws` meta-CLI discovers installed skills via Python entry points and routes to them.

## Core Value

Every skill follows the same pattern: thin CLI in container → HTTP call to host server → stdout result. Adding a new capability means adding a new claw + server pair, nothing else changes.

## Requirements

### Validated

- ✓ Shared client library (`claws-common`) handles host resolution, HTTP, and error handling — v1.0
- ✓ Host resolution auto-detects Docker vs host environment — v1.0
- ✓ Transcribe skill (`claws-transcribe`) accepts audio file, sends to whisper server, prints transcription — v1.0
- ✓ Whisper server (FastAPI on Mac mini) transcribes audio using mlx-whisper with Apple Silicon GPU — v1.0
- ✓ Whisper server exposes `POST /transcribe` and `GET /health` — v1.0
- ✓ Server managed via launchd plist for auto-start/restart — v1.0
- ✓ Skills installable via `pip install` from git URLs with `--break-system-packages` — v1.0
- ✓ Port convention: 8300+ range to avoid OpenClaw gateway conflicts — v1.0
- ✓ Meta-CLI `claws` discovers installed skills via entry points — v1.0
- ✓ uv workspace monorepo with hatchling build backend — v1.0
- ✓ README with repo structure, installation, server setup, new skill guide — v1.0

### Active

- [ ] Resy reservation skill + server
- [ ] Spotify control skill + server

### Out of Scope

- Docker image build changes — skills install via pip, Dockerfile modifications are the OpenClaw repo's concern
- Direct external API calls from container — all skills proxy through host servers
- MCP protocol support — OpenClaw uses CLI-based tool invocation
- GPU in container — ML inference runs on host Apple Silicon

## Context

- **Shipped v1.0** with 904 lines of Python across 4 packages (claws-common, claws-cli, claws-transcribe, whisper-server)
- **Tech stack**: uv workspaces, hatchling build backend, httpx, FastAPI, mlx-whisper, argparse
- **44 tests** passing across all packages
- **OpenClaw** is an AI agent platform running in Docker (`node:24-bookworm`). The container has Python 3 + pip but no GPU.
- **Host** is an Apple Silicon Mac mini running macOS with Metal/Neural Engine access for ML inference.
- **Networking**: Container reaches host via `host.docker.internal` with `OPENCLAW_TOOLS_HOST` env var override.
- **Architecture pattern**: every skill proxies through a host server, centralizing auth, rate limiting, and logging.

## Constraints

- **No GPU in container**: All ML inference must run on the host via servers
- **Port range**: Use 8300+ to avoid conflicts with OpenClaw gateway (18789/18790)
- **Package naming**: `claws-*` convention (claws-common, claws-transcribe, claws-cli)
- **Python >= 3.10**: Container ships Python 3 via Bookworm
- **pip flags**: `--break-system-packages` required in Debian Bookworm

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Always proxy through host servers | Centralizes auth, logging, rate limiting; container stays "dumb" | ✓ Good |
| `claws-*` package naming | Themed around lobster/claw metaphor | ✓ Good |
| Port 8300+ range | Avoids OpenClaw gateway port conflicts | ✓ Good |
| Unified `OPENCLAW_TOOLS_HOST` env var | Single override point instead of per-service vars | ✓ Good |
| hatchling over uv-build | Container uses pip, not uv; hatchling is pip-compatible | ✓ Good |
| httpx over requests | Modern async-capable HTTP client with better timeout defaults | ✓ Good |
| argparse over Click/Typer | Single-command tools don't need the overhead | ✓ Good |
| Entry-point based skill discovery | `claws.skills` group lets skills self-register without central config | ✓ Good |

---
*Last updated: 2026-03-18 after v1.0 milestone*
