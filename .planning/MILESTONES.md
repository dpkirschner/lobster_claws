# Milestones

## v1.0 MVP (Shipped: 2026-03-18)

**Phases completed:** 3 phases, 7 plans, 38 commits, 904 LOC Python

**Key accomplishments:**
- Monorepo foundation with uv workspaces and hatchling build backend for dual pip/uv compatibility
- Shared client library (claws-common) with Docker-aware host resolution, service-named HTTP errors, flush-safe structured output
- Whisper transcription server (FastAPI + mlx-whisper) with model preloading and MLX cache clearing on Apple Silicon
- Transcribe CLI skill with --model and --format flags, proxying through ClawsClient
- launchd plist for whisper server auto-start and crash recovery on Mac mini
- Meta-CLI with entry-point skill discovery and 233-line project README

---

