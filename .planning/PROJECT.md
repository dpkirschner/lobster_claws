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

- ✓ ClawsClient supports POST with JSON body and GET with query parameters — v1.1 Phase 4
- ✓ Google auth server with service account + domain-wide delegation — v1.1 Phase 4
- ✓ Auth server token caching, health endpoint, launchd auto-start — v1.1 Phase 4

- ✓ Gmail skill reads inbox, sends emails, searches messages via Gmail REST API — v1.1 Phase 5
- ✓ Gmail CLI registered as `claws gmail` with inbox/read/send/search subcommands — v1.1 Phase 5

- ✓ Calendar skill lists events by date range and gets event details — v1.2 Phase 6
- ✓ Calendar CLI registered as `claws calendar` with list/get subcommands — v1.2 Phase 6
- ✓ Calendar write operations — create, update, delete events with all-day support — v1.2 Phase 7

- ✓ Auth server accepts per-request `subject` for multi-agent identity — v1.3 Phase 8
- ✓ Gmail and Calendar skills support `--as user@domain.com` flag — v1.3 Phase 8
- ✓ Google Drive skill with list, download (binary + Docs export), upload (multipart/related) — v1.3 Phase 9
- ✓ Drive CLI registered as `claws drive` with `--as` flag — v1.3 Phase 9

### Active

(None — v1.3 milestone complete)


### Out of Scope

- Docker image build changes — skills install via pip, Dockerfile modifications are the OpenClaw repo's concern
- Direct external API calls from container — all skills proxy through host servers
- MCP protocol support — OpenClaw uses CLI-based tool invocation
- GPU in container — ML inference runs on host Apple Silicon
- Per-skill scope enforcement on auth server — simpler open model chosen for now

## Context

- **Shipped v1.3 + Phase 01** with ~6,000+ lines of Python across 12 packages (claws-common, claws-cli, claws-transcribe, claws-gmail, claws-calendar, claws-drive, claws-tasks, claws-contacts, claws-sheets, claws-docs, whisper-server, google-auth-server)
- **Tech stack**: uv workspaces, hatchling build backend, httpx, FastAPI, mlx-whisper, google-auth, argparse
- **369 tests** passing across all packages
- **8 skills**: transcribe, gmail (read/send/search), calendar (list/get/create/update/delete), drive (list/download/upload), tasks (full CRUD with task lists), contacts (full CRUD + search via People API), sheets (data read/write by range), docs (read/create/append)
- **2 servers**: whisper (port 8300), google-auth (port 8301)
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

| Google Workspace for agent identity | Service account + delegation = no OAuth refresh tokens, set-once auth | ✓ Good |
| Open token model (any skill, any scope) | Simpler than per-skill ACLs; internal network only | ✓ Good |
| Direct Gmail REST API over google-python-client | httpx + bearer token is lighter, matches existing patterns | ✓ Good |
| Two-tier HTTP for external API skills | ClawsClient for internal auth server, raw httpx for external Gmail API | ✓ Good |
| gmail.modify scope for all operations | Single scope covers read + send + modify, simplest approach | ✓ Good |
| Auth server binds 127.0.0.1 only | Security: token minting endpoint must not be network-accessible | ✓ Good |
| Full URL scopes (no short aliases) | No mapping table needed, matches Google docs exactly | ✓ Good |

| --as flag for per-agent identity | Each agent gets its own Workspace user, skills pass subject to auth server | — Pending |

---
*Last updated: 2026-03-23 after Phase 01 (Tasks, Contacts, Sheets, Docs skills)*
