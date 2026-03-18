# Feature Research

**Domain:** Python CLI tool monorepo for AI agent skills (container CLI + host server pairs)
**Researched:** 2026-03-17
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features the AI agent (consumer) and developer (author) assume exist. Missing these = skills are unreliable or painful to build.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Shared HTTP client library (`claws-common`) | Every skill makes the same container-to-host HTTP call; duplicating this per skill is a maintenance nightmare | LOW | Base class with host resolution, timeout, retry, error formatting. This is the foundation everything else builds on |
| Automatic host resolution | Skills must find the host server without manual config. Docker vs local detection is the first thing that breaks | LOW | Check `.dockerenv` / cgroup for Docker, fall back to `localhost`, allow `OPENCLAW_TOOLS_HOST` env override |
| Structured stdout / stderr separation | AI agents parse stdout for results. Mixing diagnostic output into stdout breaks the agent's ability to use the tool | LOW | stdout = result text only, stderr = logs/diagnostics. Agent reads stdout, developer reads stderr |
| Meaningful exit codes | Agent needs machine-readable success/failure signals to decide next action. Exit 0 = worked, nonzero = didn't | LOW | 0=success, 1=server unreachable, 2=usage error, 3=processing error. Document and keep stable |
| Health check endpoints (`GET /health`) | Operator needs to verify servers are running. launchd needs to know if restart is required. Agent can pre-check before slow operations | LOW | Return JSON with status, model loaded state, uptime. Every server gets one |
| Server auto-start via launchd | Host servers must survive reboots and crashes without human intervention. Manual `python server.py` is not operations | MEDIUM | launchd plist per server in `~/Library/LaunchAgents/`, with `KeepAlive`, `StandardOutPath`, `StandardErrorPath` |
| pip-installable packages from git | Skills install into the OpenClaw container via `pip install git+https://...`. If this doesn't work cleanly, nothing works | LOW | Each skill has its own `pyproject.toml` with proper entry points and dependencies on `claws-common` |
| Actionable error messages | When transcription fails, the agent needs to know WHY (file not found? server down? wrong format?) not just "error" | LOW | Include error type, failing input echoed back, and suggested recovery action in stderr |
| File upload support (multipart) | The first skill (transcribe) sends audio files. File upload is the primary data transfer pattern for media skills | LOW | `claws-common` provides a `post_file()` method that handles multipart encoding |
| Timeout handling | ML inference can take seconds to minutes. Skills must not hang forever, and agents need to know when something timed out vs failed | LOW | Configurable timeout with sensible defaults (30s for transcribe). Timeout = specific exit code so agent can retry or give up |

### Differentiators (Competitive Advantage)

Features that make this system notably better than ad-hoc tool scripts. Not required for v1 but create real value.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| `claws` meta-CLI with skill discovery | Single `claws` command that discovers all installed skills and routes to them. Agent gets one entry point instead of remembering N different commands | MEDIUM | Use `pkg_resources` / `importlib.metadata` entry points for discovery. `claws transcribe file.wav` instead of `claws-transcribe file.wav` |
| Server status dashboard CLI | `claws status` checks health of all known servers in one call. Agent can pre-flight check before attempting operations | LOW | Hit each server's `/health` endpoint, report up/down/model-loaded in a table or JSON |
| Warm model preloading on server start | MLX-Whisper model loads take 5-15 seconds. Loading on first request means the first transcription is painfully slow | MEDIUM | Server loads model at startup, health endpoint reports `model_loaded: true/false`. launchd starts server at login so model is ready before agent needs it |
| Streaming transcription progress | Long audio files can take 30+ seconds. Without progress, the agent (and user) don't know if it's working or hung | MEDIUM | Server sends chunked response or the CLI polls a status endpoint. Print progress to stderr so stdout stays clean for final result |
| Server-side request queuing | If two transcription requests arrive simultaneously, the server needs to handle it gracefully rather than OOM or corrupt | MEDIUM | Single-worker FastAPI with a queue. Return 429 or queue position if busy. Prevents Apple Silicon GPU memory issues |
| Scaffolding tool for new skills | `claws new my-skill` generates the boilerplate: CLI entry point, server template, pyproject.toml, launchd plist template, tests | MEDIUM | Reduces friction for adding new claws. Cookie-cutter style templates with the naming convention baked in |
| Unified logging with correlation IDs | When debugging, trace a request from agent invocation through CLI to server and back. Without correlation, multi-hop debugging is guesswork | MEDIUM | CLI generates a request ID, passes as header, server logs with it, CLI includes in stderr output |
| OpenAI-compatible API format | Whisper server uses same request/response format as OpenAI's audio API. Makes it a drop-in replacement if agent platform adds native API support | LOW | Follow OpenAI's `/v1/audio/transcriptions` spec for the endpoint shape. Already common in mlx-whisper community |
| Dry-run / describe mode | `claws transcribe --describe` outputs what the tool does, expected inputs, output format. Helps agents self-discover capabilities without docs | LOW | JSON schema output describing the tool's interface. Useful for dynamic tool registration |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems for this specific architecture.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Direct external API calls from container | Simpler than proxying through host server | Breaks the security model (container stays "dumb"), scatters auth credentials, loses centralized logging and rate limiting | Always proxy through host servers, even for simple REST APIs. The extra hop is the feature, not a bug |
| MCP server protocol | It's the industry standard for AI tool integration in 2025-2026 | OpenClaw invokes tools as CLI commands, not MCP. Adding MCP means running an MCP server inside the container alongside the existing tool system. Premature abstraction for a single-user system | Keep CLI-based tools. If OpenClaw adds MCP support later, write a thin MCP wrapper around existing CLIs |
| Plugin auto-discovery via filesystem scanning | Avoids entry point registration, just drop a file in a directory | Fragile, depends on install paths, breaks in containerized environments where packages install to different locations | Use Python entry points (`[project.scripts]` in pyproject.toml). Standard, portable, works everywhere pip does |
| Centralized tool registry / database | Track which skills are installed, their versions, capabilities | Over-engineering for a monorepo where you control all the code. Adds state management complexity for no benefit at this scale | `pip list \| grep claws` or entry point discovery. The package manager IS the registry |
| GPU sharing / multi-model serving | Run whisper + other ML models simultaneously on Apple Silicon | Apple Silicon unified memory is limited (16-64GB). Model swapping and GPU contention create unpredictable latency and OOM risks | One server per model, one model loaded at a time per server. Sequential, predictable, debuggable |
| WebSocket-based communication | Real-time bidirectional communication between CLI and server | CLI tools are request-response by nature. WebSockets add connection management complexity for no benefit when the agent just wants stdout | HTTP POST + response. Use chunked transfer encoding if streaming is needed |
| Container-side caching of results | Cache transcription results in the container to avoid re-processing | Container is ephemeral (can be recreated). Cache invalidation is hard. Media files can be large | Cache on the server side if needed, keyed by file hash. Server persists across container rebuilds |
| Async/concurrent skill execution | Run multiple skills in parallel from the agent | The agent already handles concurrency at its level. Adding concurrency inside individual skills creates complexity without benefit | Let the agent orchestrate parallelism. Each skill invocation is a simple, synchronous, single-purpose call |

## Feature Dependencies

```
[claws-common (shared client library)]
    |
    |--requires--> [Host resolution logic]
    |--requires--> [HTTP client with file upload]
    |--requires--> [Error formatting / exit codes]
    |
    +--enables--> [claws-transcribe CLI]
    |                 |--requires--> [Whisper server running on host]
    |                 |--requires--> [File upload support in claws-common]
    |
    +--enables--> [Future skills (resy, spotify, etc.)]

[Whisper server (FastAPI)]
    |--requires--> [mlx-whisper installed on host]
    |--requires--> [Health check endpoint]
    |--enhances--> [Model preloading at startup]
    |
    +--managed-by--> [launchd plist]

[claws meta-CLI] --enhances--> [claws-common]
    |--requires--> [Entry point discovery]
    |--enables--> [claws status (health dashboard)]
    |--enables--> [claws new (scaffolding)]

[Structured output] --enables--> [Agent error recovery loops]
[Meaningful exit codes] --enables--> [Agent error recovery loops]
```

### Dependency Notes

- **claws-transcribe requires claws-common:** All skills depend on the shared client for host resolution and HTTP calls. Build common first.
- **claws-transcribe requires Whisper server:** The CLI is useless without the server running. Both must ship together.
- **claws meta-CLI requires entry points:** Skills must register as entry points before discovery works. This means pyproject.toml must be correct first.
- **Model preloading enhances Whisper server:** Not required for function, but dramatically improves first-request latency. Add after server works.
- **launchd plist managed by server package:** Ship the plist template with the server code, not separately.

## MVP Definition

### Launch With (v1)

Minimum viable product -- what's needed for the agent to successfully transcribe audio.

- [ ] `claws-common` package -- host resolution, HTTP client, error formatting, exit codes
- [ ] `claws-transcribe` CLI -- accepts audio file path, POSTs to whisper server, prints transcription to stdout
- [ ] Whisper server (FastAPI) -- `POST /transcribe` accepts file upload, returns text; `GET /health` returns status
- [ ] launchd plist for whisper server -- auto-start, auto-restart, log to file
- [ ] Structured output -- stdout for result, stderr for diagnostics, meaningful exit codes
- [ ] pip installable from git URLs -- `pip install git+https://...#subdirectory=skills/transcribe`

### Add After Validation (v1.x)

Features to add once the first skill works end-to-end.

- [ ] `claws` meta-CLI with entry point discovery -- trigger: when adding the second skill makes N separate commands annoying
- [ ] `claws status` health dashboard -- trigger: when debugging "is the server running?" becomes frequent
- [ ] Model preloading at server startup -- trigger: when cold-start latency complaints emerge
- [ ] OpenAI-compatible API format for whisper -- trigger: when considering interop with other tools
- [ ] Request queuing on server -- trigger: when concurrent requests cause issues
- [ ] `--describe` / dry-run mode -- trigger: when exploring dynamic tool registration

### Future Consideration (v2+)

Features to defer until the pattern is proven and more skills exist.

- [ ] Scaffolding tool (`claws new`) -- defer: not worth building until 3+ skills exist and the pattern is truly stable
- [ ] Correlation ID logging -- defer: debugging is manageable at small scale; add when multi-hop tracing becomes painful
- [ ] Streaming transcription progress -- defer: nice UX but complex; only matters for very long audio files
- [ ] Unified configuration system -- defer: each server can have its own config until config sprawl becomes a real problem

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| claws-common shared library | HIGH | LOW | P1 |
| Host resolution (auto-detect Docker) | HIGH | LOW | P1 |
| claws-transcribe CLI | HIGH | LOW | P1 |
| Whisper server (FastAPI) | HIGH | MEDIUM | P1 |
| Health check endpoints | HIGH | LOW | P1 |
| Structured stdout/stderr | HIGH | LOW | P1 |
| Meaningful exit codes | HIGH | LOW | P1 |
| launchd plist management | HIGH | LOW | P1 |
| pip installable packages | HIGH | LOW | P1 |
| Actionable error messages | MEDIUM | LOW | P1 |
| File upload (multipart) | HIGH | LOW | P1 |
| Timeout handling | MEDIUM | LOW | P1 |
| claws meta-CLI | MEDIUM | MEDIUM | P2 |
| claws status dashboard | MEDIUM | LOW | P2 |
| Model preloading | MEDIUM | MEDIUM | P2 |
| OpenAI-compatible API | LOW | LOW | P2 |
| Request queuing | MEDIUM | MEDIUM | P2 |
| Dry-run / describe mode | LOW | LOW | P2 |
| Scaffolding tool | LOW | MEDIUM | P3 |
| Correlation ID logging | LOW | MEDIUM | P3 |
| Streaming progress | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | mlx-whisper-api-server (gschmutz) | whisper_turboapi (kristofferv98) | Our Approach |
|---------|----------------------------------|----------------------------------|--------------|
| API format | OpenAI-compatible | OpenAI-compatible | Simple custom first, OpenAI-compat later (P2) |
| Model management | Manual model selection | Turbo model hardcoded | Configurable model, preloaded at startup |
| Health checks | None apparent | None apparent | Full health endpoint with model-loaded status |
| Service management | Manual process | Manual process | launchd with auto-restart, log rotation |
| Client library | None (direct HTTP) | None (direct HTTP) | Shared `claws-common` with host auto-detection |
| Error handling | Basic HTTP errors | Basic HTTP errors | Structured errors with exit codes for agent consumption |
| Multi-skill support | N/A (single purpose) | N/A (single purpose) | Monorepo pattern designed for adding new skills |

## Sources

- [Writing CLI Tools That AI Agents Actually Want to Use](https://dev.to/uenyioha/writing-cli-tools-that-ai-agents-actually-want-to-use-39no) - Core patterns for agent-friendly CLI design
- [Keep the Terminal Relevant: Patterns for AI Agent Driven CLIs](https://www.infoq.com/articles/ai-agent-cli/) - AI agent CLI architecture patterns
- [Python Packaging: Creating and Discovering Plugins](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/) - Entry point discovery patterns
- [mlx-whisper-api-server](https://github.com/gschmutz/mlx-whisper-api-server) - Reference FastAPI whisper server implementation
- [whisper_turboapi](https://github.com/kristofferv98/whisper_turboapi) - Optimized MLX whisper server
- [FastAPI Health Check Patterns](https://microservices.io/patterns/observability/health-check-api.html) - Health check API design
- [Python Monorepo Patterns (Tweag)](https://www.tweag.io/blog/2023-04-04-python-monorepo-1/) - Monorepo structure and shared libraries
- [Building a Python Monorepo with UV](https://medium.com/@naorcho/building-a-python-monorepo-with-uv-the-modern-way-to-manage-multi-package-projects-4cbcc56df1b4) - Modern Python monorepo tooling
- [MCP vs Skills Architecture](https://apacheseatunnel.medium.com/mcp-vs-skills-how-ai-agents-connect-to-tools-and-real-world-systems-b4f698c04b76) - Understanding tool vs protocol approaches

---
*Feature research for: Python CLI tool monorepo for AI agent skills*
*Researched: 2026-03-17*
