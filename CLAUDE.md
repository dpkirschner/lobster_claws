# Lobster Claws

Python monorepo of "claws" — CLI skills for the OpenClaw AI agent. Each skill runs inside a Docker container and talks to a server on the Mac mini host. The agent is the lobster; each skill is another claw.

## Architecture

```
Container (Docker, no GPU)          Host (Mac mini, Apple Silicon)
┌─────────────────────────┐         ┌──────────────────────────┐
│  claws transcribe file  │──HTTP──▶│  whisper-server :8300    │
│  (claws-transcribe CLI) │         │  (FastAPI + mlx-whisper) │
│                         │         │                          │
│  Uses ClawsClient from  │         │  Managed by launchd      │
│  claws-common           │         │  (auto-start, restart)   │
└─────────────────────────┘         └──────────────────────────┘
```

**Pattern**: thin CLI in container → HTTP to host server → stdout result.

## Repo Structure

```
lobster_claws/
├── common/              # claws-common — shared client library
│   └── src/claws_common/
│       ├── host.py      # resolve_host() — Docker detection, env override
│       ├── client.py    # ClawsClient — HTTP wrapper with service-aware errors
│       └── output.py    # result(), fail(), crash() — stdout/stderr/exit codes
├── cli/                 # claws-cli — meta-CLI with entry-point discovery
│   └── src/claws_cli/
│       └── main.py      # `claws` command, discovers skills via claws.skills group
├── skills/
│   └── transcribe/      # claws-transcribe — audio transcription skill
│       └── src/claws_transcribe/
│           └── cli.py   # argparse CLI: file, --model, --format
├── servers/
│   └── whisper/         # whisper-server — FastAPI transcription server
│       └── src/whisper_server/
│           └── app.py   # POST /transcribe, GET /health, model preloading
├── launchd/             # macOS launchd plists for server auto-start
├── tests/               # Root-level tests (plist validation)
├── pyproject.toml       # uv workspace root (not a package itself)
└── data.md              # OpenClaw integration reference
```

## Development

```bash
uv sync            # Install all workspace members
uv run pytest      # Run all 44 tests
uv run claws       # List available skills
```

## Key Conventions

- **Package naming**: `claws-*` (claws-common, claws-transcribe, claws-cli)
- **Build backend**: hatchling (pip-compatible; container uses pip, not uv)
- **HTTP client**: httpx via `ClawsClient` — always use this, never raw requests
- **Output**: use `result()`, `fail()`, `crash()` from `claws_common.output` — they handle flush and exit codes
- **Host resolution**: `ClawsClient` calls `resolve_host()` automatically — never hardcode IPs
- **Ports**: 8300+ range (avoids OpenClaw gateway on 18789/18790)
- **Skill registration**: add `[project.entry-points."claws.skills"]` to pyproject.toml
- **Tests**: TDD with mocked boundaries — server tests mock mlx_whisper, CLI tests mock ClawsClient
- **Linting**: ruff (configured in root pyproject.toml)

## Adding a New Skill

1. Create `skills/<name>/` with pyproject.toml depending on `claws-common`
2. Write CLI in `skills/<name>/src/claws_<name>/cli.py` using `ClawsClient` and `output` helpers
3. Register entry point: `[project.entry-points."claws.skills"]` → `<name> = "claws_<name>.cli:main"`
4. Create server in `servers/<name>/` if needed
5. Add launchd plist in `launchd/` for the server
6. Add workspace member to root pyproject.toml and run `uv sync`
