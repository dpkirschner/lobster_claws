# Pitfalls Research

**Domain:** Python CLI tools monorepo with Docker container / macOS host split architecture
**Researched:** 2026-03-17
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: launchd Does Not Inherit Shell Environment

**What goes wrong:**
The whisper server (and future host servers) managed by launchd cannot find Python, mlx-whisper, or any Homebrew-installed binaries. The server fails silently or crashes on load because PATH, PYTHONPATH, and other environment variables from your shell (.zshrc) are not available to launchd-managed processes.

**Why it happens:**
launchd launches processes in a minimal environment -- not a shell. It does not source .zshrc, .bash_profile, or any shell configuration. Developers test servers by running them in a terminal (where everything works) and then are surprised when the same command fails under launchd. Shell globbing and variable expansion (like `~` or `$HOME`) also do not work in plist EnvironmentVariables.

**How to avoid:**
- Use absolute paths for everything in the plist: the executable, the working directory, log paths.
- Explicitly set PATH and any required env vars in the plist's `EnvironmentVariables` dictionary. Include `/opt/homebrew/bin` for Homebrew on Apple Silicon.
- Never use `~` in plist values -- always use `/Users/little-dank/...`.
- Test the server by launching it via `launchctl` before considering it done. Never rely on "it works from terminal."

**Warning signs:**
- Server works when started manually from terminal but not after reboot.
- `launchctl list | grep <label>` shows the service with a non-zero exit status.
- Log files (if configured) show "command not found" or import errors.

**Phase to address:**
Phase 1 (Infrastructure/Foundation) -- the launchd plist must be correct from day one or every server will inherit the same broken setup.

---

### Pitfall 2: Local Path Dependencies Break pip install from Git URLs

**What goes wrong:**
`claws-transcribe` depends on `claws-common`. If you specify this as a local path dependency in pyproject.toml (e.g., `claws-common = {path = "../claws-common"}`), then `pip install git+https://github.com/...` from inside the Docker container will fail. pip resolves git URLs by cloning the repo, but local path references resolve relative to the cloned temp directory, not the monorepo root. The install breaks with "directory does not exist."

**Why it happens:**
Python packaging standards (PEP 508, pyproject.toml) support path dependencies for local development, but these are inherently non-portable. They work with editable installs during development but fail for any remote install path (git URLs, PyPI, etc.). This is a fundamental tension in Python monorepos.

**How to avoid:**
- Publish `claws-common` as a proper dependency: either to a private PyPI index, or more practically, specify it as a separate `pip install git+https://...#subdirectory=claws-common` dependency.
- In the install instructions (or a requirements.txt / install script), install claws-common first, then claws-transcribe.
- In pyproject.toml, list `claws-common` as a normal dependency name (not a path), and ensure it is already installed before installing any claw that depends on it.
- Consider a thin install script or Makefile target that installs packages in dependency order from git URLs.

**Warning signs:**
- `pip install` works locally but fails in CI or fresh Docker containers.
- pyproject.toml contains `{path = "..."}` references.
- Install instructions require being in a specific directory to work.

**Phase to address:**
Phase 1 (Package Structure) -- getting the dependency chain right is foundational. If you get this wrong, every new claw inherits the problem.

---

### Pitfall 3: host.docker.internal Resolution Failures Are Silent and Confusing

**What goes wrong:**
The CLI tool inside the container makes an HTTP call to `host.docker.internal:8301` and gets a connection timeout, connection refused, or DNS resolution failure. The error messages from urllib/httpx/requests are generic networking errors that do not hint at the Docker-specific root cause. Debugging is painful because networking works fine from the host.

**Why it happens:**
Several failure modes: (1) `host.docker.internal` requires `extra_hosts` configuration in Docker Compose on Linux (macOS Docker Desktop adds it automatically, but OpenClaw may run on Linux too). (2) The host server is bound to `127.0.0.1` instead of `0.0.0.0`, so it rejects connections from the Docker bridge network. (3) macOS firewall silently blocks incoming connections from the container. (4) The server is not running, and the error looks identical to a networking misconfiguration.

**How to avoid:**
- In claws-common's HTTP client, add specific error handling that distinguishes "server not running" from "host not reachable" and provides actionable error messages (e.g., "Cannot reach host server. Is the whisper server running? Check: curl http://host.docker.internal:8301/health").
- Always bind FastAPI servers to `0.0.0.0`, not `127.0.0.1`.
- Add a `/health` endpoint to every server and have the CLI check it before making the real request (or at least on failure, to differentiate causes).
- Document the `OPENCLAW_TOOLS_HOST` env var override prominently for non-standard setups.

**Warning signs:**
- "Connection refused" errors that come and go.
- Works on one machine but not another.
- Adding `print(socket.getaddrinfo("host.docker.internal", 8301))` shows resolution but connection still fails.

**Phase to address:**
Phase 1 (claws-common client library) -- the shared HTTP client must handle this gracefully from the start.

---

### Pitfall 4: Python stdout Buffering Swallows CLI Output in Docker

**What goes wrong:**
The CLI tool runs, makes the HTTP call, gets the transcription result, prints it to stdout... but the agent sees no output. Or it sees partial output. The tool appears to hang or produce empty results.

**Why it happens:**
Python buffers stdout when it detects a non-interactive terminal (which is the case inside Docker containers when invoked programmatically). The buffer is 8KB by default. If the CLI prints less than 8KB and exits without flushing, the output may be lost. This is a classic Docker + Python pitfall that has bitten countless projects.

**How to avoid:**
- Set `PYTHONUNBUFFERED=1` in the environment, or use `python -u` when invoking CLIs.
- Better yet, in each CLI's entry point, explicitly call `sys.stdout.reconfigure(line_buffering=True)` or use `print(..., flush=True)`.
- In claws-common, provide a utility output function that always flushes.

**Warning signs:**
- CLI works interactively but produces no output when called by the agent.
- Output appears only after a long delay or when the process exits.
- Adding more print statements "fixes" the issue (because more output fills the buffer).

**Phase to address:**
Phase 1 (claws-common / CLI skeleton) -- this must be baked into the shared tooling so every claw inherits it.

---

### Pitfall 5: --break-system-packages Dependency Conflicts Corrupt Container Python

**What goes wrong:**
Installing claws packages with `pip install --break-system-packages` overwrites or conflicts with system Python packages in the node:24-bookworm container. A subsequent OpenClaw operation that depends on a system Python package (or another pip-installed tool) breaks because the wrong version is now installed.

**Why it happens:**
PEP 668 exists specifically because mixing pip-installed packages with distro-managed packages is dangerous. `--break-system-packages` is a "I know what I'm doing" escape hatch, not a best practice. The node:24-bookworm image may have system Python packages that claws dependencies conflict with.

**How to avoid:**
- Keep claws dependencies minimal. claws-common should depend on httpx (or requests) and nothing else exotic.
- Pin dependency versions in pyproject.toml to avoid accidental upgrades of system packages.
- Test installs on a fresh node:24-bookworm container to catch conflicts early.
- If conflicts become a problem, consider installing into a venv even inside the container (the CLI entry point would need a wrapper script).
- Never install heavy ML libraries in the container -- that is what the host servers are for.

**Warning signs:**
- pip warnings about "replacing distro-installed package" during install.
- Other Python tools in the container breaking after claw installation.
- Different behavior between fresh and repeatedly-updated containers.

**Phase to address:**
Phase 1 (Package Structure) -- dependency minimalism must be enforced from the start.

---

### Pitfall 6: MLX Whisper Memory Accumulation on Long-Running Server

**What goes wrong:**
The whisper server works great for the first few transcriptions, then slows down dramatically or crashes with memory errors. macOS shows memory pressure warnings. The Mac mini becomes sluggish.

**Why it happens:**
MLX uses Metal GPU memory (unified memory on Apple Silicon). Without explicit cache clearing between transcriptions, GPU memory accumulates across requests. Large audio files with large models (large-v3 on 16GB) can exhaust available memory in a single request. The model stays loaded in memory (which is good for latency) but intermediate buffers from previous transcriptions may not be freed.

**How to avoid:**
- Clear MPS/MLX cache after each transcription request.
- Set a maximum audio file size/duration and reject files that exceed it with a clear error.
- Monitor memory in the /health endpoint (report available memory).
- Use `mlx.core.metal.clear_cache()` (or equivalent) after each inference.
- Consider batch_size tuning -- default of 12 is fine for most cases, but reduce for the large-v3 model on 16GB machines.

**Warning signs:**
- Transcription time increases over successive requests without restart.
- `memory_pressure` command shows yellow/red state.
- Server process memory grows monotonically in Activity Monitor.

**Phase to address:**
Phase 2 (Whisper Server) -- must be implemented when building the transcription endpoint, not retrofitted.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoding `host.docker.internal` in each claw | Quick to ship first claw | Every claw duplicates host resolution logic; changing the pattern requires editing all claws | Never -- this is why claws-common exists |
| No health check endpoint | Faster server development | Cannot distinguish "server down" from "network broken" from "server overloaded" | Never -- /health is trivial to add |
| Inline error messages in each CLI | Avoids claws-common dependency | Inconsistent error formatting; agent gets confused by varying error patterns | Only in prototyping; standardize before v1 |
| Single requirements.txt instead of pyproject.toml | Simpler initial setup | No proper metadata, no version constraints, breaks pip install from git URLs | Never for installable packages |
| Skipping launchd plist validation | Faster iteration | Server silently fails on reboot, discovered days later | Never |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Docker `extra_hosts` | Assuming host.docker.internal exists everywhere | OpenClaw already configures this, but verify it in claws-common with a clear error if resolution fails |
| File paths across container/host boundary | Passing container file paths to host server | Audio files must be uploaded (multipart POST) or accessible via a shared volume mount -- do not assume path equivalence |
| launchd service management | Using `launchctl load/unload` (deprecated) | Use `launchctl bootstrap/bootout` on modern macOS (10.10+) |
| pip install from git with subdirectory | Omitting `#subdirectory=` fragment | Use `pip install "git+https://github.com/user/repo.git#subdirectory=packages/claws-common"` |
| FastAPI file upload size | Default upload limits in uvicorn | Set explicit `--limit-max-request-size` for large audio files (default is ~1MB, audio files can be 50MB+) |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Loading Whisper model on every request | First request takes 30+ seconds, all requests slow | Load model once at server startup (module-level or lifespan event), keep in memory | Immediately -- even one user notices |
| Synchronous file upload in FastAPI | Server blocks during large file upload, other requests queue | Use `async def` endpoints with `UploadFile` (FastAPI handles this correctly by default, but do not wrap in sync executor) | At 2+ concurrent requests |
| DNS resolution on every HTTP call | Adds 5-50ms latency to every CLI invocation | Resolve host once in claws-common client init, cache the result | Noticeable at high call frequency |
| Transcribing uncompressed WAV files | Huge upload times, unnecessary bandwidth | Accept compressed formats (mp3, opus, m4a); if WAV arrives, document but do not re-encode in the CLI | Files over 10MB |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Host server bound to 0.0.0.0 without any access control | Any device on the local network can hit the whisper server and run inference | Bind to 0.0.0.0 (needed for Docker) but add a simple shared secret header or restrict to Docker bridge subnet. For a Mac mini on a home network, this is low risk but still worth a middleware check. |
| No input validation on uploaded files | Malformed or malicious files could crash the server or cause excessive resource usage | Validate file type (magic bytes, not just extension), enforce size limits, set transcription timeout |
| Exposing server error tracebacks to CLI output | Internal server details leak to agent context | Use FastAPI exception handlers to return clean error messages; log full tracebacks server-side only |
| Storing API keys in plist files | Keys visible in plain text, committed to repo | Use macOS Keychain or environment variables loaded from a separate .env file excluded from git |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| CLI prints raw JSON or HTTP errors | Agent cannot parse the output; conversation degrades | Print clean, human-readable text. On error, print a single-line error message the agent can relay to the user |
| No progress indication for long transcriptions | Agent (and user) think the tool is hung | Print a brief status line before starting ("Transcribing 45s of audio...") and the result after |
| Failing silently on partial transcription | User gets incomplete text without knowing it | Always indicate if transcription was truncated or if errors occurred during processing |
| Inconsistent exit codes | Agent cannot distinguish success from failure | Exit 0 on success, exit 1 on user-fixable errors (with message), exit 2 on infrastructure errors |

## "Looks Done But Isn't" Checklist

- [ ] **launchd plist:** Often missing `EnvironmentVariables` with correct PATH -- verify server starts after full reboot (not just `launchctl kickstart`)
- [ ] **pip install from git URL:** Often works locally but fails in container -- verify install in a fresh `node:24-bookworm` container
- [ ] **File upload size:** Often tested with small files only -- verify with a 30-minute audio file (50MB+)
- [ ] **Error handling:** Often only tests the happy path -- verify behavior when server is down, when file does not exist, when audio format is unsupported
- [ ] **Host resolution:** Often only tested on macOS Docker Desktop -- verify OPENCLAW_TOOLS_HOST override works
- [ ] **stdout flushing:** Often works in interactive testing -- verify output appears when CLI is invoked non-interactively by OpenClaw agent
- [ ] **Memory after 20+ transcriptions:** Often tested with 1-2 files -- run a batch of 20 transcriptions and check server memory

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| launchd env vars wrong | LOW | Fix plist, `launchctl bootout` + `launchctl bootstrap`, verify with `launchctl print` |
| Path dependencies break remote install | MEDIUM | Restructure pyproject.toml to use named dependencies, create install script for ordering, update all install docs |
| stdout buffering eating output | LOW | Add `PYTHONUNBUFFERED=1` to container env or add flush=True to print calls |
| Memory leak in whisper server | LOW | Add cache clearing, restart server; no data loss since servers are stateless |
| --break-system-packages corruption | MEDIUM | Rebuild container (or reinstall conflicting packages). Prevent by pinning deps and testing on fresh containers |
| host.docker.internal unreachable | LOW | Check server binding (0.0.0.0), check macOS firewall, verify extra_hosts config in Docker Compose |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| launchd env vars | Phase 1: Infrastructure | Server starts correctly after full macOS reboot |
| Path dependency breakage | Phase 1: Package Structure | `pip install git+...#subdirectory=` works in fresh container |
| host.docker.internal failures | Phase 1: claws-common | Client gives actionable error messages for each failure mode |
| stdout buffering | Phase 1: CLI Skeleton | Output appears when invoked non-interactively |
| --break-system-packages conflicts | Phase 1: Package Structure | Install on fresh node:24-bookworm with no pip warnings |
| MLX memory accumulation | Phase 2: Whisper Server | Memory stable after 20 sequential transcriptions |
| File upload size limits | Phase 2: Whisper Server | 50MB file uploads succeed |
| No health endpoint | Phase 1: Server Skeleton | `curl /health` returns status on every server |
| Inconsistent error output | Phase 1: claws-common | CLI exit codes and messages follow documented contract |

## Sources

- [Python Monorepo: Structure and Tooling (Tweag)](https://www.tweag.io/blog/2023-04-04-python-monorepo-1/)
- [Where is my PATH, launchD? (Lucas Pinheiro)](https://lucaspin.medium.com/where-is-my-path-launchd-fc3fc5449864)
- [Environment variables for launchd (Apple Developer Forums)](https://developer.apple.com/forums/thread/681550)
- [Docker Networking: host.docker.internal (Docker Docs)](https://docs.docker.com/desktop/features/networking/)
- [host.docker.internal resolves but does not respond (moby/moby #46892)](https://github.com/moby/moby/issues/46892)
- [Python stdout buffering in Docker (docker-library/python #604)](https://github.com/docker-library/python/issues/604)
- [PEP 668 and --break-system-packages (Louis-Philippe Veronneau)](https://veronneau.org/python-311-pip-and-breaking-system-packages.html)
- [MLX Whisper performance and memory (lightning-whisper-mlx)](https://github.com/mustafaaljadery/lightning-whisper-mlx)
- [FastAPI production deployment patterns](https://stribny.name/posts/fastapi-production/)
- [Docker Networking Pitfalls](https://jwillmer.de/blog/programming/docker-networking-pitfalls)

---
*Pitfalls research for: Python CLI tools monorepo with Docker/host split architecture (Lobster Claws)*
*Researched: 2026-03-17*
