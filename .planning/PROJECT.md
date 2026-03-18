# Lobster Claws

## What This Is

A Python monorepo of "claws" — lightweight CLI skills that give the OpenClaw AI agent new capabilities. Each claw is a pip-installable package that runs inside the OpenClaw Docker container and communicates with a corresponding server on the Mac mini host. The agent is the lobster; each skill is another claw that lets it do something new.

## Core Value

Every skill follows the same pattern: thin CLI in container → HTTP call to host server → stdout result. Adding a new capability means adding a new claw + server pair, nothing else changes.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Shared client library (`claws-common`) handles host resolution, HTTP, and error handling for all skills
- [ ] Host resolution auto-detects Docker vs host environment (`.dockerenv`, cgroup, env var override)
- [ ] Transcribe skill (`claws-transcribe`) accepts audio file, sends to whisper server, prints transcription
- [ ] Whisper server (FastAPI on Mac mini) transcribes audio using mlx-whisper with Apple Silicon GPU
- [ ] Whisper server exposes `POST /transcribe` (file upload) and `GET /health`
- [ ] Server managed via launchd plist for auto-start/restart
- [ ] Skills installable via `pip install` from git URLs with `--break-system-packages`
- [ ] Port convention: 8300+ range to avoid OpenClaw gateway conflicts (18789/18790)

### Out of Scope

- Resy skill — future claw, not in v1
- Spotify skill — future claw, not in v1
- Docker image build changes — skills install via pip, Dockerfile modifications are the OpenClaw repo's concern
- Direct external API calls from container — all skills proxy through host servers

## Context

- **OpenClaw** is an AI agent platform running in Docker (`node:24-bookworm`). The container has Python 3 + pip but no GPU. Skills are invoked by the agent as tools during conversations.
- **Host** is an Apple Silicon Mac mini running macOS. Servers run here with Metal/Neural Engine access for ML inference.
- **Networking**: Container reaches host via `host.docker.internal`. OpenClaw sandbox containers already set `extra_hosts` for this. A unified `OPENCLAW_TOOLS_HOST` env var overrides resolution.
- **Container user**: non-root `node` (uid 502:20). pip requires `--break-system-packages` on Bookworm.
- **Media pipeline**: OpenClaw stores media at `~/.openclaw/media/`. Transcribe flow: channel downloads audio → media store → agent calls transcribe skill with file path → skill POSTs to whisper server → returns text.
- **Architecture pattern**: every skill proxies through a host server, even for external APIs. This centralizes auth, rate limiting, logging, and avoids giving the container direct external access.

## Constraints

- **No GPU in container**: All ML inference must run on the host via servers
- **Port range**: Use 8300+ to avoid conflicts with OpenClaw gateway (18789/18790)
- **Package naming**: `claws-*` convention (claws-common, claws-transcribe)
- **Python >= 3.10**: Container ships Python 3 via Bookworm
- **pip flags**: `--break-system-packages` required in Debian Bookworm

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Always proxy through host servers | Centralizes auth, logging, rate limiting; container stays "dumb" | — Pending |
| `claws-*` package naming | Themed around lobster/claw metaphor | — Pending |
| Port 8300+ range | Avoids OpenClaw gateway port conflicts | — Pending |
| Unified `OPENCLAW_TOOLS_HOST` env var | Single override point instead of per-service vars | — Pending |

---
*Last updated: 2026-03-17 after initialization*
