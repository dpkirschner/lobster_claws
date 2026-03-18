# Requirements: Lobster Claws

**Defined:** 2026-03-17
**Core Value:** Every skill follows the same pattern: thin CLI in container -> HTTP call to host server -> stdout result. Adding a new capability means adding a new claw + server pair, nothing else changes.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Shared Library

- [x] **LIB-01**: Host resolution auto-detects Docker vs host environment via `.dockerenv`, cgroup check, and `OPENCLAW_TOOLS_HOST` env var override
- [x] **LIB-02**: HTTP client wrapper provides POST/GET with configurable timeouts, connection error messages including service name and URL
- [x] **LIB-03**: Structured output convention: result JSON to stdout, errors/diagnostics to stderr, exit codes 0/1/2
- [x] **LIB-04**: Meta-CLI `claws` command discovers installed skills via Python entry points and routes to them

### Whisper Server

- [x] **WHSP-01**: FastAPI server exposes `POST /transcribe` accepting audio file upload, returns transcription text
- [x] **WHSP-02**: Server exposes `GET /health` returning server status and loaded model info
- [x] **WHSP-03**: Model selection parameter on `/transcribe` allows choosing whisper model per request
- [x] **WHSP-04**: Model preloading keeps the default model in memory between requests for faster response

### Transcribe Skill

- [x] **TRNS-01**: `claws-transcribe` CLI accepts audio file path, POSTs to whisper server, prints transcription to stdout
- [x] **TRNS-02**: `--format` flag switches output between plain text and JSON
- [x] **TRNS-03**: `--model` flag allows choosing whisper model for the request
- [x] **TRNS-04**: Runs with `PYTHONUNBUFFERED=1` for Docker compatibility

### Infrastructure

- [x] **INFR-01**: launchd plist auto-starts and restarts whisper server on Mac mini
- [x] **INFR-02**: Standard Python `.gitignore` for monorepo
- [x] **INFR-03**: uv workspace configuration with root `pyproject.toml` managing all packages
- [x] **INFR-04**: Top-level README covering repo structure, skill installation, server setup, and how to add new skills

## v2 Requirements

### Operations

- **OPS-01**: `claws status` health dashboard checking all registered servers
- **OPS-02**: Request queuing for concurrent whisper calls
- **OPS-03**: MLX memory cache clearing between requests

### Additional Skills

- **SKILL-01**: Resy reservation skill + server
- **SKILL-02**: Spotify control skill + server

## Out of Scope

| Feature | Reason |
|---------|--------|
| Direct external API calls from container | All skills proxy through host servers -- centralized auth/logging |
| MCP protocol support | OpenClaw uses CLI-based tool invocation, not MCP |
| GPU in container | No CUDA/GPU access; ML inference runs on host Apple Silicon |
| Docker image modifications | Skills install via pip; Dockerfile changes are OpenClaw repo's concern |
| Plugin auto-discovery via filesystem | Over-engineered; entry points are the right mechanism |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| LIB-01 | Phase 1: Foundation | Complete |
| LIB-02 | Phase 1: Foundation | Complete |
| LIB-03 | Phase 1: Foundation | Complete |
| LIB-04 | Phase 3: Discovery and Documentation | Complete |
| WHSP-01 | Phase 2: Transcription Skill | Complete |
| WHSP-02 | Phase 2: Transcription Skill | Complete |
| WHSP-03 | Phase 2: Transcription Skill | Complete |
| WHSP-04 | Phase 2: Transcription Skill | Complete |
| TRNS-01 | Phase 2: Transcription Skill | Complete |
| TRNS-02 | Phase 2: Transcription Skill | Complete |
| TRNS-03 | Phase 2: Transcription Skill | Complete |
| TRNS-04 | Phase 2: Transcription Skill | Complete |
| INFR-01 | Phase 2: Transcription Skill | Complete |
| INFR-02 | Phase 1: Foundation | Complete |
| INFR-03 | Phase 1: Foundation | Complete |
| INFR-04 | Phase 3: Discovery and Documentation | Complete |

**Coverage:**
- v1 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0

---
*Requirements defined: 2026-03-17*
*Last updated: 2026-03-17 after roadmap creation*
