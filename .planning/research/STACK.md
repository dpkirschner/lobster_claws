# Stack Research

**Domain:** Python tools monorepo -- CLI skills in Docker + FastAPI servers on Apple Silicon host
**Researched:** 2026-03-17
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| uv | >=0.10 | Package/project manager, workspace orchestration | The standard Python toolchain in 2025-2026. Replaces pip/pip-tools/virtualenv for development. Workspaces give monorepo support with a single lockfile. 10-100x faster than pip. Written by Astral (same team as ruff). |
| Python | 3.12 | Runtime | Bookworm container ships 3.12. macOS Homebrew ships 3.12/3.13. Target 3.12 for compatibility across both environments. |
| FastAPI | >=0.135 | HTTP server framework for host services | The standard for Python APIs. Async-native, auto-generates OpenAPI docs, built-in validation via Pydantic. Same ecosystem as Typer (tiangolo). |
| uvicorn | >=0.42 | ASGI server for FastAPI | The default ASGI server paired with FastAPI. Lightweight, fast, production-ready for single-process servers. |
| mlx-whisper | >=0.4.3 | Speech-to-text on Apple Silicon | Apple's MLX framework optimized for Metal GPU. 30-40% faster than whisper.cpp on Apple Silicon. Directly loads Hugging Face whisper models. |
| httpx | >=0.28 | HTTP client for CLI-to-server communication | Modern replacement for requests. Supports both sync and async APIs, HTTP/2, timeouts by default. Used in claws-common for all server calls. |
| Pydantic | v2 (>=2.10) | Data validation and serialization | Ships with FastAPI. Use for request/response models and configuration. v2 is 5-50x faster than v1. |

### CLI Framework

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| argparse | stdlib | CLI argument parsing | Zero dependencies -- critical for container installs. Each claw is a thin CLI that takes a file path and prints output. argparse is sufficient; no need for Click/Typer overhead when the CLI is just `claws-transcribe <file>`. |

**Why NOT Typer/Click:** Each claw CLI is a single-command tool (e.g., `claws-transcribe audio.mp3`). Typer and Click add dependencies and complexity for multi-command apps. argparse from stdlib means zero extra packages in the container. If a claw ever needs subcommands, reassess then.

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-multipart | >=0.0.18 | Multipart form data parsing | Required by FastAPI for file upload endpoints (`POST /transcribe`). Install alongside FastAPI on the server side. |
| mlx | >=0.31 | Apple Silicon ML framework | Dependency of mlx-whisper. Provides Metal-accelerated array operations. Only on host (macOS). |
| pydantic-settings | >=2.7 | Configuration from env vars | Server configuration (port, model name, log level). Loads from environment with type validation. |

### Development Tools

| Tool | Version | Purpose | Notes |
|------|---------|---------|-------|
| uv | >=0.10 | Package management, virtual envs, workspace | Use `uv sync` for development, `uv run` to execute. Replaces pip/venv/pip-tools. |
| ruff | >=0.15 | Linting + formatting | Single tool replaces flake8, isort, black, pyflakes. Astral ecosystem (same as uv). Configure in root `pyproject.toml`. |
| pytest | >=9.0 | Testing | Standard Python test runner. Use with `uv run pytest`. |
| pytest-httpx | >=0.35 | Mock HTTP calls in tests | For testing CLI packages that call servers via httpx. Cleaner than unittest.mock patching. |
| mypy | >=1.14 | Type checking | Optional but recommended. FastAPI + Pydantic are fully typed. Catches real bugs. |

## Monorepo Structure

Use **uv workspaces** for the monorepo. Each package is a workspace member with its own `pyproject.toml`.

```
lobster_claws/
  pyproject.toml              # Root workspace config (virtual, not a package itself)
  uv.lock                     # Single lockfile for all members
  packages/
    claws-common/
      pyproject.toml           # Shared client library
      src/claws_common/
    claws-transcribe/
      pyproject.toml           # CLI skill package
      src/claws_transcribe/
  servers/
    whisper-server/
      pyproject.toml           # FastAPI server package
      src/whisper_server/
```

### Root pyproject.toml Pattern

```toml
[project]
name = "lobster-claws"
version = "0.1.0"
requires-python = ">=3.12"

[tool.uv]
package = false               # Virtual root, not installable

[tool.uv.workspace]
members = ["packages/*", "servers/*"]

[dependency-groups]
dev = ["ruff", "pytest", "pytest-httpx", "mypy"]
```

### Package pyproject.toml Pattern (CLI skill)

```toml
[project]
name = "claws-transcribe"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["claws-common"]

[project.scripts]
claws-transcribe = "claws_transcribe.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv.sources]
claws-common = { workspace = true }
```

### Container Installation (pip, not uv)

The OpenClaw container uses pip, not uv. Packages install via git URL with subdirectory:

```bash
pip install --break-system-packages \
  "claws-common @ git+https://github.com/user/lobster_claws.git#subdirectory=packages/claws-common" \
  "claws-transcribe @ git+https://github.com/user/lobster_claws.git#subdirectory=packages/claws-transcribe"
```

**Critical:** Each package's `pyproject.toml` must work standalone with pip. The `[tool.uv.sources]` section is uv-specific and ignored by pip. Therefore, `claws-common` must be listed as a normal dependency in `[project.dependencies]` AND as a workspace source in `[tool.uv.sources]`. When pip installs from git, it resolves `claws-common` as a PyPI package name -- so install `claws-common` first, or pin it as a git dependency too.

**Build backend:** Use `hatchling` (not `uv-build`). hatchling is the standard, works with pip out of the box, and does not require uv on the consumer side. `uv-build` is newer and less battle-tested for pip-only consumers.

## Installation

```bash
# Development setup (macOS host)
curl -LsSf https://astral.sh/uv/install.sh | sh
cd lobster_claws
uv sync                       # Creates venv, installs all workspace members + dev deps

# Run a specific package
uv run --package claws-transcribe claws-transcribe audio.mp3

# Run tests
uv run pytest

# Run a server
uv run --package whisper-server python -m whisper_server

# Lint and format
uv run ruff check .
uv run ruff format .
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| uv workspaces | Poetry monorepo | Never. Poetry's monorepo support is weak and its resolver is slow. uv has won. |
| uv workspaces | Standalone pyproject per package (no workspace) | If packages truly have no shared dev tooling. Not this project. |
| hatchling (build backend) | setuptools | If you need C extensions or complex build steps. setuptools is heavier but more battle-tested for edge cases. |
| hatchling (build backend) | uv-build | When all consumers use uv. Our container uses pip, so hatchling is safer. |
| argparse | Click/Typer | If a claw needs subcommands, interactive prompts, or rich help formatting. Not needed for single-command tools. |
| httpx | requests | Never for new code. requests lacks async support and modern defaults. httpx is the successor. |
| mlx-whisper | whisper.cpp | If you need CPU-only inference or non-Apple platforms. On Apple Silicon, mlx-whisper is faster. |
| mlx-whisper | lightning-whisper-mlx | If you need streaming/real-time transcription. Claims 4x faster than mlx-whisper but less maintained. Evaluate if latency matters. |
| FastAPI | Flask | Never for new async APIs. Flask is sync-first and lacks built-in validation. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Poetry | Slow resolver, weak monorepo support, losing ecosystem share to uv | uv |
| setuptools for simple packages | Verbose, requires setup.cfg or setup.py alongside pyproject.toml | hatchling |
| requests | No async, no HTTP/2, no timeout defaults, maintenance-mode | httpx |
| Flask | Sync-first, no built-in validation, no auto OpenAPI docs | FastAPI |
| openai-whisper (original) | Requires PyTorch (huge), no Metal optimization, slow on Apple Silicon | mlx-whisper |
| Gunicorn | Overkill for single-server-process host services. Adds process management complexity when launchd already handles restarts. | uvicorn directly |
| Docker Compose for servers | Servers need Metal GPU access. Docker has no Metal passthrough. Servers must run on bare macOS host. | launchd plists |

## Stack Patterns by Variant

**If adding a non-ML server (e.g., Resy API proxy):**
- Same pattern: FastAPI + uvicorn + httpx (for outbound API calls)
- No mlx dependency
- Assign next port in 8300+ range

**If a CLI skill needs no server (pure local computation):**
- Still follow the claw pattern with claws-common
- Skip the server, have the CLI do work directly
- Rare case -- most skills proxy through host for consistency

**If container needs to install from private repo:**
- Use deploy keys or GitHub App tokens
- pip supports `git+https://<token>@github.com/...` syntax
- Do NOT bake tokens into Docker images; pass via build args or runtime env

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| FastAPI >=0.135 | Pydantic v2 only | FastAPI dropped Pydantic v1 support. Always use v2. |
| mlx-whisper >=0.4 | mlx >=0.31, Python 3.10+ | macOS only. Requires Apple Silicon (M1+). |
| httpx >=0.28 | Python 3.8+ | No compatibility concerns. |
| uv >=0.10 | Python 3.8+ for managed projects | uv itself is a standalone binary, not a Python package in your venv. |
| hatchling | pip >=21.3 | Bookworm ships pip 23+. No issues. |

## Dual-Environment Constraint

This project has a split-brain architecture:

- **Container (consumer):** Python 3.12, pip only, no GPU, Debian Bookworm. Installs `claws-*` packages via `pip install` from git URLs. Cannot use uv features.
- **Host (developer + server runner):** macOS, Apple Silicon, uv for development, Metal GPU for ML.

Every packaging decision must work in BOTH environments. This means:
1. Build backend must be pip-compatible (hatchling, not uv-build)
2. Dependencies in `[project.dependencies]` must be real PyPI packages (not workspace-only references)
3. `[tool.uv.sources]` overrides are development-only and ignored by pip
4. Test that `pip install` from git subdirectory works in CI or a clean Docker container

## Sources

- [uv PyPI](https://pypi.org/project/uv/) -- version 0.10.11 confirmed (2026-03-16)
- [uv workspaces docs](https://docs.astral.sh/uv/concepts/projects/workspaces/) -- workspace configuration, member resolution
- [FastAPI PyPI](https://pypi.org/project/fastapi/) -- version 0.135.1 confirmed (2026-03-01)
- [mlx-whisper PyPI](https://pypi.org/project/mlx-whisper/) -- version 0.4.3 confirmed (2025-08-29)
- [httpx PyPI](https://pypi.org/project/httpx/) -- version 0.28.1 confirmed
- [uvicorn PyPI](https://pypi.org/project/uvicorn/) -- version 0.42.0 confirmed (2026-03-16)
- [ruff PyPI](https://pypi.org/project/ruff/) -- version 0.15.6 confirmed (2026-03-12)
- [pytest PyPI](https://pypi.org/project/pytest/) -- version 9.0.2 confirmed (2025-12-06)
- [pip install docs](https://pip.pypa.io/en/stable/cli/pip_install/) -- git URL with #subdirectory syntax
- [uv pip compatibility](https://docs.astral.sh/uv/pip/compatibility/) -- what uv supports vs pip

---
*Stack research for: Python tools monorepo (Docker CLI + Apple Silicon servers)*
*Researched: 2026-03-17*
