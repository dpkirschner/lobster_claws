# Project Research Summary

**Project:** lobster_claws
**Domain:** Python CLI tool monorepo — Docker container skills + macOS host servers for AI agent integration
**Researched:** 2026-03-17
**Confidence:** HIGH

## Executive Summary

Lobster Claws is a Python monorepo that delivers AI agent skills as thin container-side CLIs paired with macOS host-side FastAPI servers. The canonical pattern is "thin CLI + fat server": the Docker container stays dumb (argument parsing, HTTP call, stdout printing) while all business logic and GPU inference lives on the Apple Silicon host. This split-brain architecture exists because Docker has no Metal GPU passthrough, so ML workloads must run natively on macOS. The monorepo is managed with uv workspaces, giving a single lockfile and fast dependency resolution for development while pip-from-git-URL handles container installs.

The recommended approach is to build the shared client library (`claws-common`) first, then implement the first skill pair (whisper server + `claws-transcribe` CLI) as the proof-of-concept that validates the full stack. Every subsequent skill follows the same pattern: a new subdirectory in `skills/`, a new server in `servers/`, and a launchd plist for process supervision. The project's opinionated conventions — one server per capability, one model per server, port 8300+, structured stdout/stderr, meaningful exit codes — exist to make the agent a reliable consumer.

The primary risks are all infrastructural: launchd not inheriting shell environment (servers fail silently after reboot), pip-from-git-URL breaking when `claws-common` is specified as a path dependency instead of a named package, Python stdout buffering eating CLI output in non-interactive Docker contexts, and MLX GPU memory accumulation on long-running servers. All six critical pitfalls identified surface in Phase 1 or Phase 2 and are entirely avoidable with known patterns. There are no research gaps; the stack is mature and the patterns are well-documented.

## Key Findings

### Recommended Stack

The toolchain is the Astral ecosystem on both ends: uv for workspace/dependency management and ruff for linting/formatting. Hatchling is the build backend (not uv-build) because the container uses pip, not uv, and hatchling works standalone. On the host, FastAPI + uvicorn is the server framework; mlx-whisper provides Apple Silicon-optimized speech-to-text. In the container, httpx handles HTTP calls to the host and argparse (stdlib) handles CLI argument parsing — no heavier frameworks needed for single-command tools.

**Core technologies:**
- `uv` (>=0.10): Workspace orchestration and dev toolchain — replaces pip/venv/pip-tools, 10-100x faster, single lockfile
- `Python 3.12`: Runtime — target this for compatibility across Debian Bookworm container and macOS host
- `FastAPI` (>=0.135) + `uvicorn` (>=0.42): Host server framework — async-native, auto OpenAPI, Pydantic v2 validation
- `mlx-whisper` (>=0.4.3): Speech-to-text on Apple Silicon — 30-40% faster than whisper.cpp, uses Metal GPU
- `httpx` (>=0.28): Container HTTP client — async-capable, modern defaults, replaces requests
- `hatchling`: Build backend — pip-compatible for container installs; do NOT use uv-build
- `argparse` (stdlib): CLI argument parsing — zero dependencies, sufficient for single-command tools

### Expected Features

The MVP is a complete request-response loop: agent subprocess calls `claws-transcribe`, which POSTs audio to the whisper server, which runs mlx-whisper inference and returns text to stdout. Everything else is layered on after that loop works.

**Must have (table stakes — v1):**
- `claws-common` shared client library — host resolution, HTTP client, multipart file upload, error formatting, exit codes
- Automatic Docker vs. host detection — resolves `host.docker.internal` in container, falls back to `localhost` on host
- `claws-transcribe` CLI — accepts file path, prints transcription to stdout, diagnostics to stderr
- Whisper server — `POST /transcribe` (multipart), `GET /health`, model preloaded at startup
- launchd plists — auto-start, auto-restart, log paths; every server gets one
- Structured stdout/stderr with meaningful exit codes (0=success, 1=server unreachable, 2=usage error, 3=processing error)
- pip-installable packages from git URLs with `#subdirectory=` syntax

**Should have (competitive — v1.x, add when triggered):**
- `claws` meta-CLI with entry-point discovery (trigger: second skill makes N separate commands annoying)
- `claws status` health dashboard (trigger: "is the server running?" becomes a recurring question)
- Request queuing on the whisper server (trigger: concurrent requests cause GPU OOM)
- OpenAI-compatible API format for the whisper server (trigger: considering interop)
- `--describe` / dry-run mode (trigger: dynamic tool registration exploration)

**Defer (v2+):**
- Scaffolding tool (`claws new`) — not worth building until 3+ skills prove the pattern is stable
- Correlation ID logging — manageable at small scale; add when multi-hop tracing becomes painful
- Streaming transcription progress — complex; only matters for very long audio files

### Architecture Approach

The system is two distinct runtime environments connected by HTTP. Container-side packages (`claws-common`, skill CLIs) communicate with host-side servers via `host.docker.internal:83XX`. The key boundary rule: `claws-common` and `servers-common` must never depend on each other — HTTP is the contract. The monorepo structure reflects this with separate `common/`, `skills/`, and `servers/` top-level directories, each containing pip-installable packages with `src/` layout and their own `pyproject.toml`.

**Major components:**
1. `claws-common` (container) — SkillClient base class: host resolution chain, httpx wrapper, stdout flush, error formatting
2. `servers/common` (host) — FastAPI app factory: `/health` endpoint, structured logging, error middleware; all servers inherit this
3. `claws-transcribe` (container) — thin CLI: parse args, call `SkillClient.post_file("/transcribe", path)`, print result
4. `whisper-server` (host) — `POST /transcribe` multipart endpoint, mlx-whisper inference with model preloaded at startup, MLX cache clearing after each request
5. launchd plists — process supervision with absolute paths, explicit `EnvironmentVariables` (PATH including `/opt/homebrew/bin`), `KeepAlive`, log files

### Critical Pitfalls

1. **launchd does not inherit shell environment** — Use absolute paths everywhere in plist; explicitly set PATH in `EnvironmentVariables`; never use `~`; test by rebooting, not just `launchctl kickstart`
2. **Local path dependencies break pip-from-git-URL** — List `claws-common` as a named dependency (not `{path = "..."}`); install packages in dependency order in the install script
3. **Python stdout buffering swallows output in Docker** — Set `PYTHONUNBUFFERED=1` or call `sys.stdout.reconfigure(line_buffering=True)` in every CLI entry point; provide a flush-always utility in `claws-common`
4. **host.docker.internal failures are silent and confusing** — Bind FastAPI servers to `0.0.0.0`; add actionable error messages in `claws-common` that distinguish "server not running" from "host not reachable"; document `OPENCLAW_TOOLS_HOST` override
5. **MLX GPU memory accumulation on long-running server** — Call `mlx.core.metal.clear_cache()` after each transcription; set file size limits; monitor memory in `/health` response
6. **`--break-system-packages` dependency conflicts corrupt container Python** — Keep container dependencies minimal (httpx and nothing exotic); pin versions; test on fresh `node:24-bookworm` before shipping

## Implications for Roadmap

The architecture research defines a clear build order with two parallel tracks converging at integration testing. All six critical pitfalls require Phase 1 attention — there is no safe way to defer them.

### Phase 1: Foundation — Monorepo, claws-common, Server Skeleton

**Rationale:** `claws-common` is the dependency everything else builds on. The monorepo structure (uv workspace, `pyproject.toml` per package, `src/` layout, hatchling build backend) must be correct before any skill or server is written. All six critical pitfalls are rooted here: the pip dependency chain, stdout flushing, host resolution error handling, and launchd plist patterns all need to be established in the shared tooling so every subsequent component inherits them.

**Delivers:** Working uv workspace; `claws-common` package installable from git URL in a fresh `node:24-bookworm` container; `servers/common` with app factory and `/health`; launchd plist template with correct env var and absolute path patterns; verified stdout flush behavior under non-interactive invocation

**Addresses (FEATURES.md):** claws-common shared library, host resolution, structured stdout/stderr, meaningful exit codes, health check endpoints, pip-installable packages, actionable error messages, file upload support, timeout handling

**Avoids (PITFALLS.md):** All Phase 1 pitfalls — path dependency breakage, stdout buffering, host.docker.internal failure modes, `--break-system-packages` conflicts, launchd env setup

### Phase 2: First Skill — Whisper Server + claws-transcribe

**Rationale:** The whisper server is the highest-value, most complex server (GPU inference, file uploads, memory management). Building it first proves the full request-response loop and exposes any architectural gaps before the pattern is duplicated. The `claws-transcribe` CLI is trivial once `claws-common` exists; the server is where the real work is.

**Delivers:** `whisper-server` running under launchd with model preloaded at startup; `claws-transcribe` CLI installable into the OpenClaw container; verified end-to-end transcription with a real audio file; MLX memory management with cache clearing; file size enforcement; server error messages that do not leak tracebacks

**Uses (STACK.md):** mlx-whisper (>=0.4.3), FastAPI + uvicorn, python-multipart, mlx, pydantic-settings

**Implements (ARCHITECTURE.md):** Thin CLI + fat server pattern; FastAPI app factory with health; launchd process supervision; multipart file upload data flow

**Avoids (PITFALLS.md):** MLX memory accumulation, file upload size limits (must set `--limit-max-request-size` for 50MB+ audio files), model loading on every request (load once at startup)

### Phase 3: Hardening and Developer Experience

**Rationale:** Once the first skill works end-to-end, the missing operational pieces become obvious: no easy way to check if servers are running, no meta-CLI, no test coverage verified in CI. This phase closes the gap between "works on my machine" and "reliable system."

**Delivers:** `claws status` health dashboard; `claws` meta-CLI with entry-point discovery; pytest suite covering claws-common (with pytest-httpx mocks), whisper-server endpoints, and happy/error paths in the CLI; Makefile targets for common dev tasks; install scripts for skill → container and server → host + launchd

**Addresses (FEATURES.md):** claws meta-CLI (P2), claws status dashboard (P2), actionable error messages validated end-to-end

**Uses (STACK.md):** pytest (>=9.0), pytest-httpx (>=0.35), mypy (>=1.14), ruff (>=0.15)

### Phase 4: Second Skill (Pattern Validation)

**Rationale:** The second skill (e.g., a Resy API proxy server) validates that the monorepo pattern scales cleanly — that adding a new server + CLI is as mechanical as the architecture intends. If Phase 4 requires revisiting Phase 1 conventions, catch it now before a third and fourth skill are added.

**Delivers:** Second server + CLI pair following identical conventions; port 8301 registered; confirmed that uv workspace, pip install, launchd plist, and claws-common patterns generalize without modification

**Addresses (FEATURES.md):** "Add After Validation" features triggered by the second skill — entry point discovery, status dashboard now covers multiple servers

### Phase Ordering Rationale

- `claws-common` must be built before any skill CLI — it is the foundational import
- Server skeleton (`servers/common`) can be built in parallel with `claws-common` since they have zero dependency on each other
- `whisper-server` depends on `servers-common`; `claws-transcribe` depends on `claws-common` — these are parallel tracks after Phase 1
- Hardening (Phase 3) comes after the first end-to-end loop is validated, not before — premature testing infrastructure adds friction without the reference implementation to test against
- A second skill (Phase 4) comes last to validate generalization; building it before Phase 3 test infrastructure would mean building it without test coverage

### Research Flags

Phases with well-documented patterns (skip research-phase):
- **Phase 1:** uv workspaces, hatchling build, pip-from-git-URL patterns are all fully documented with official sources and confirmed package versions
- **Phase 2:** mlx-whisper usage, FastAPI multipart uploads, launchd plist configuration are well-documented; reference implementations exist (mlx-whisper-api-server, whisper_turboapi)
- **Phase 3:** pytest, ruff, pytest-httpx are standard tooling with no research needed

Phases that may benefit from brief research during planning:
- **Phase 4:** The specific second skill domain (Resy, Spotify, etc.) may have API-specific patterns worth a short research pass before implementation

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All package versions confirmed on PyPI as of 2026-03-16/17; official docs consulted for uv workspaces, FastAPI, mlx-whisper |
| Features | HIGH | MVP feature set derived from first principles of the architecture; P1/P2/P3 priorities are well-reasoned with explicit trigger conditions |
| Architecture | HIGH | Patterns validated against multiple monorepo references; component boundaries are clean and non-overlapping; data flow is unambiguous |
| Pitfalls | HIGH | All 6 critical pitfalls are documented failure modes with known causes and proven fixes; sourced from official Apple docs, Docker docs, and real project issues |

**Overall confidence:** HIGH

### Gaps to Address

- **Second skill domain:** The project mentions resy and spotify as future skills, but no research was done on their specific APIs. When Phase 4 is planned, a brief research pass on the target external API (auth patterns, rate limits, response shapes) is recommended.
- **`launchctl bootstrap` vs `launchctl load`:** PITFALLS.md notes that `launchctl load/unload` is deprecated in favor of `bootstrap/bootout`. The install scripts should use the modern commands, but the exact syntax needs verification against the target macOS version during Phase 1.
- **OpenClaw container base image:** Research assumes `node:24-bookworm` as the container base. If this changes, the Python version, pip behavior, and `--break-system-packages` risk profile need to be re-evaluated.

## Sources

### Primary (HIGH confidence)
- [uv workspaces docs](https://docs.astral.sh/uv/concepts/projects/workspaces/) — workspace configuration, member resolution, pip compatibility
- [FastAPI PyPI](https://pypi.org/project/fastapi/) — version 0.135.1 confirmed 2026-03-01
- [mlx-whisper PyPI](https://pypi.org/project/mlx-whisper/) — version 0.4.3 confirmed 2025-08-29
- [uvicorn PyPI](https://pypi.org/project/uvicorn/) — version 0.42.0 confirmed 2026-03-16
- [httpx PyPI](https://pypi.org/project/httpx/) — version 0.28.1 confirmed
- [ruff PyPI](https://pypi.org/project/ruff/) — version 0.15.6 confirmed 2026-03-12
- [launchd.plist man page](https://keith.github.io/xcode-man-pages/launchd.plist.5.html) — official plist reference
- [Docker networking: host.docker.internal](https://docs.docker.com/desktop/features/networking/) — Docker Desktop behavior
- [Python Packaging: Creating and Discovering Plugins](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/) — entry point discovery

### Secondary (MEDIUM confidence)
- [mlx-whisper-api-server (gschmutz)](https://github.com/gschmutz/mlx-whisper-api-server) — reference FastAPI whisper server implementation
- [whisper_turboapi (kristofferv98)](https://github.com/kristofferv98/whisper_turboapi) — optimized MLX whisper server reference
- [Building a Python Monorepo with UV (Naor David Melamed)](https://medium.com/@naorcho/building-a-python-monorepo-with-uv-the-modern-way-to-manage-multi-package-projects-4cbcc56df1b4) — workspace configuration patterns
- [Where is my PATH, launchD? (Lucas Pinheiro)](https://lucaspin.medium.com/where-is-my-path-launchd-fc3fc5449864) — launchd environment variable pitfall
- [Python stdout buffering in Docker (docker-library/python #604)](https://github.com/docker-library/python/issues/604) — buffering failure mode
- [PEP 668 and --break-system-packages](https://veronneau.org/python-311-pip-and-breaking-system-packages.html) — system package conflict risks

### Tertiary (LOW confidence)
- [lightning-whisper-mlx](https://github.com/mustafaaljadery/lightning-whisper-mlx) — claims 4x faster than mlx-whisper; less maintained, not recommended for v1 but worth evaluating if latency becomes critical

---
*Research completed: 2026-03-17*
*Ready for roadmap: yes*
