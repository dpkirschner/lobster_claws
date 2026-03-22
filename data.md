OpenClaw Tools Integration Cheatsheet

For the Claude agent building the openclaw-tools Python monorepo.
This documents every assumption, constraint, and integration point
you need to know about the OpenClaw Docker environment.

⸻

1. Where Your Code Runs

Skills (Python CLIs) run INSIDE the OpenClaw Docker container
	•	Base image: node:24-bookworm (Debian Bookworm)
	•	User: non-root node (uid 1000) — or overridden to 502:20 in docker-compose
	•	Python: python3 and python3-pip are installed via build arg:

--build-arg OPENCLAW_DOCKER_APT_PACKAGES="python3 python3-pip"


	•	Working directory: /app (the OpenClaw Node.js app lives here)
	•	Home directory: /home/node
	•	Node.js: v24 (present but irrelevant for your Python tools)
	•	No GPU: the container has no CUDA/GPU access. All ML inference
must happen on the host (Mac mini) via the servers layer.

Servers (FastAPI) run ON THE HOST (Mac mini)
	•	OS: macOS (Darwin)
	•	Hardware: Apple Silicon Mac mini (M-series, ARM64)
	•	Python: whatever is installed on the host (use pyenv/homebrew)
	•	GPU: Apple Neural Engine / Metal available for mlx-whisper etc.
	•	Managed via: launchd plists (not systemd, not Docker)

⸻

2. Container → Host Networking

This is the critical integration point. Skills in the container need to
reach servers on the Mac mini host.

How to resolve the host from inside Docker

Docker Desktop for Mac provides host.docker.internal automatically.
However, the OpenClaw docker-compose.yml does NOT set extra_hosts,
so you cannot rely on this unless you add it yourself.

Recommended approach for common/ SkillClient host resolution:

import os, socket

def resolve_host() -> str:
    """Resolve the Mac mini host from inside or outside Docker."""
    # Explicit override (always wins)
    if host := os.environ.get("OPENCLAW_TOOLS_HOST"):
        return host

    # Detect if we're in Docker
    if _in_docker():
        return "host.docker.internal"

    # Running directly on host
    return "127.0.0.1"

def _in_docker() -> bool:
    """Detect Docker environment."""
    return (
        os.path.exists("/.dockerenv")
        or os.environ.get("container") == "docker"
        or _cgroup_is_docker()
    )

If you modify docker-compose.yml

To guarantee host.docker.internal resolution, add to the gateway service:

extra_hosts:
  - "host.docker.internal:host-gateway"

OpenClaw’s sandbox containers already use this pattern (extraHosts: ["host.docker.internal:host-gateway"]).

Port conventions
	•	OpenClaw gateway: 18789 (WebSocket), 18790 (bridge) — DO NOT collide
	•	Your whisper server: pick a port like 8300+ to avoid conflicts
	•	The host firewall must allow connections from Docker’s bridge network

⸻

3. Environment Variables Available in the Container

Set by docker-compose.yml (always available)

Variable	Value	Purpose
HOME	/home/node	User home directory
TERM	xterm-256color	Terminal type
OPENCLAW_GATEWAY_TOKEN	(from .env)	Gateway auth token
OPENCLAW_ALLOW_INSECURE_PRIVATE_WS	(from .env)	Allow ws:// on private nets
OPENCLAW_GATEWAY_URL	ws://openclaw-gateway:18789	CLI→gateway WebSocket URL (cli service only)
CLAUDE_AI_SESSION_KEY	(from .env)	Claude.ai session auth
CLAUDE_WEB_SESSION_KEY	(from .env)	Claude web session auth
CLAUDE_WEB_COOKIE	(from .env)	Claude web cookie

Set by Dockerfile (baked into image)

Variable	Value	Purpose
NODE_ENV	production	Node environment mode
COREPACK_HOME	/usr/local/share/corepack	Corepack path

Loaded from .env file (host-side, passed through)

These live in the repo root .env (gitignored). The container gets them
via docker-compose ${VAR:-} interpolation:

Variable	Purpose
OPENCLAW_CONFIG_DIR	Host path mounted to /home/node/.openclaw
OPENCLAW_WORKSPACE_DIR	Host path mounted to /home/node/.openclaw/workspace
OPENCLAW_GATEWAY_PORT	Host port mapped to container 18789
OPENCLAW_BRIDGE_PORT	Host port mapped to container 18790
OPENCLAW_GATEWAY_BIND	Gateway bind mode (lan/loopback/custom)
OPENCLAW_IMAGE	Docker image name (default: openclaw:local)

Provider API keys (may or may not be set)

These are in .env and passed if configured. Your tools probably don’t
need these directly, but be aware they exist:
	•	OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY
	•	BRAVE_API_KEY, ELEVENLABS_API_KEY, DEEPGRAM_API_KEY
	•	TELEGRAM_BOT_TOKEN, DISCORD_BOT_TOKEN, SLACK_BOT_TOKEN, SLACK_APP_TOKEN

Your custom env vars (you define these)

For the tools monorepo, define your own env vars. Suggested convention:

Variable	Purpose	Default
OPENCLAW_TOOLS_HOST	Override host resolution	host.docker.internal in Docker, 127.0.0.1 on host
WHISPER_SERVER_PORT	Whisper server port	8300
WHISPER_MODEL	Default whisper model	small

Pass these to the container by adding them to docker-compose.yml’s
environment: block or the .env file.

⸻

4. Volume Mounts & File Paths

Inside the container

/app/                           # OpenClaw app (read-only-ish, owned by root)
/home/node/                     # User home
/home/node/.openclaw/           # bind mount from host OPENCLAW_CONFIG_DIR
/home/node/.openclaw/workspace/ # bind mount from host OPENCLAW_WORKSPACE_DIR
/home/node/.openclaw/openclaw.json   # Main config (JSON5)
/home/node/.openclaw/sessions/  # Session logs (JSONL)
/home/node/.openclaw/media/     # Temporary media files
/home/node/.openclaw/credentials/ # OAuth/credential files

Where to install Python tools

Since the container user is node (or 502), pip install to user site:

pip install --user --break-system-packages <package>

Or better: mount a volume with pre-built wheels/venvs. The cleanest
approach is to add a build stage to the Dockerfile that pip-installs
your skills.

Recommended Dockerfile addition

RUN pip3 install --break-system-packages \
    git+https://github.com/yourorg/openclaw-tools.git#subdirectory=common \
    git+https://github.com/yourorg/openclaw-tools.git#subdirectory=skills/transcribe


⸻

5. Docker Build & Run

Current Makefile

build:
    docker build \
        --build-arg OPENCLAW_EXTENSIONS="slack openshell memory-core" \
        --build-arg OPENCLAW_INSTALL_BROWSER=1 \
        --build-arg OPENCLAW_DOCKER_APT_PACKAGES="python3 python3-pip" \
        -t openclaw:local .

run:
    docker compose down
    docker compose up -d --force-recreate

Note: python3 and python3-pip are already being installed.
Your skills just need to be pip-installed on top.

docker-compose services

Service	Purpose	Network
openclaw-gateway	WebSocket gateway, channel management, agent dispatch	Own bridge network, ports 18789/18790 exposed
openclaw-cli	Interactive CLI	Shares gateway’s network namespace

Health check

GET http://127.0.0.1:18789/healthz
GET http://127.0.0.1:18789/readyz


⸻

6. OpenClaw Config System

Config lives at ~/.openclaw/openclaw.json (JSON5 format).

Relevant config paths

{
  "gateway": {
    "mode": "local",
    "auth": { "token": "..." },
    "controlUi": { }
  },
  "agents": {
    "defaults": {
      "sandbox": { }
    }
  },
  "plugins": { },
  "channels": {
    "telegram": { },
    "discord": { }
  }
}

CLI config commands

openclaw config get gateway.mode
openclaw config set gateway.mode local
openclaw config validate


⸻

7. Media Pipeline
	•	Media store: ~/.openclaw/media/ (temporary files)
	•	HTTP endpoint: GET /media/:id
	•	Supported types: images, audio, documents

Transcribe flow
	1.	Channel downloads audio → media store
	2.	Agent receives media reference
	3.	Skill downloads file → sends to whisper server → returns text

⸻

8. Plugin/Extension System
	•	Plugin manifest: openclaw.plugin.json
	•	Entry point exports register(api)
	•	Plugins can register tools, CLI commands, routes, channels

⸻

9. Security Constraints
	•	Non-root container user
	•	no-new-privileges: true
	•	Auth token required for gateway
	•	Never commit .env

⸻

10. Common Gotchas
	•	No extra_hosts by default
	•	UID mismatch between container and host
	•	pip requires --break-system-packages
	•	No GPU in container
	•	Port conflicts with 18789/18790
	•	Media files are ephemeral
	•	Config is JSON5
	•	Gateway auto-restarts
	•	.env must be in repo root
	•	Docker build cache nuances

⸻

11. Quick Reference: Integration Checklist
	•	Host resolution logic implemented
	•	Ports avoid conflicts
	•	pip install works
	•	Media files accessible
	•	Servers bind to 0.0.0.0
	•	launchd configs correct
	•	Env vars passed correctly
	•	No hardcoded IPs
	•	Graceful error handling
	•	Dependencies use git URLs
