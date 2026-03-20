# Stack Research

**Domain:** Google auth server + Gmail skill additions to claws monorepo
**Researched:** 2026-03-19
**Confidence:** HIGH

## Recommended Stack (New Dependencies Only)

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| google-auth | >=2.49 | Service account credentials, JWT signing, domain-wide delegation | Official Google library. Provides `Credentials.from_service_account_file()`, `.with_subject()`, `.with_scopes()` -- the exact primitives needed for domain-wide delegation. Actively maintained (2.49.1 released 2026-03-12). No alternative exists for this task. |
| requests | >=2.32 | HTTP transport for google-auth token refresh | `google.auth.transport.requests.Request` is the standard transport for exchanging JWTs for access tokens at Google's token endpoint. google-auth has built-in transports for `requests` and `aiohttp` but NOT for httpx. Only needed in the auth server on the host -- never in the container. |

### Reused from Existing Stack (No Changes)

| Technology | Purpose in v1.1 |
|------------|-----------------|
| FastAPI >=0.135 | Auth server framework (same pattern as whisper-server) |
| uvicorn >=0.42 | ASGI server for auth server |
| httpx >=0.28 | Auth server calls Gmail REST API; Gmail skill calls auth server via ClawsClient |
| claws-common | Gmail skill uses ClawsClient and output helpers (unchanged) |
| argparse | Gmail skill CLI argument parsing |
| hatchling | Build backend for both new packages |
| pytest + pytest-httpx | Testing both new packages |
| ruff | Linting both new packages |

## Key Architecture Decision: Direct REST vs google-api-python-client

**Decision: Use direct Gmail REST API via httpx. Do NOT use google-api-python-client.**

Rationale:
- The Gmail REST API is simple and well-documented: `GET /gmail/v1/users/{userId}/messages` (list/search), `GET .../messages/{id}` (read), `POST .../messages/send` (send)
- The auth server already holds credentials and produces access tokens -- it makes Gmail API calls directly with httpx and a bearer token header
- `google-api-python-client` pulls in `uritemplate`, `google-api-core`, `google-auth-httplib2`, `httplib2`, and `protobuf` -- heavy dependencies for what amounts to adding an `Authorization` header to REST calls
- The existing codebase uses httpx everywhere; adding httplib2 via the Google client would introduce a second HTTP stack
- The Gmail skill in the container stays thin (just calls the auth server via ClawsClient) -- no Google libraries needed in the container at all

## Key Architecture Decision: Auth Server as API Proxy

**Decision: The auth server makes Gmail API calls on behalf of the skill. It is NOT a token vending machine.**

Rationale:
- Keeps all Google credentials, token management, and API complexity on the host
- The skill in the container never touches Google auth, tokens, or Gmail API endpoints
- Consistent with the whisper-server pattern: skill sends a request, server does the heavy lifting, returns clean JSON
- Token refresh, caching, and error handling are centralized in one place
- Adding Calendar later means adding endpoints to the same server, not shipping Google libraries to the container

## Token Flow

```
Container (Gmail skill)              Host (google-auth server :8301)        Google APIs
+-------------------+               +---------------------------+          +------------------+
| claws gmail read  |--GET /gmail-->| 1. Load service account   |          |                  |
|                   |   inbox       |    key from disk           |          |                  |
| (ClawsClient,     |               | 2. .with_subject(user)    |          |                  |
|  no Google libs)  |               | 3. .with_scopes([gmail])  |          |                  |
|                   |               | 4. credentials.refresh()  |--JWT---->| Token endpoint   |
|                   |               |    (via requests transport)|<-token---|                  |
|                   |               | 5. httpx GET gmail API    |--------->| Gmail REST API   |
|                   |<--JSON result-|    with bearer token       |<-JSON---|                  |
+-------------------+               +---------------------------+          +------------------+
```

## Installation

### Auth Server (servers/google-auth/)

```toml
[project]
name = "google-auth-server"
version = "0.1.0"
description = "Google API proxy server with service account domain-wide delegation"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.135",
    "uvicorn>=0.42",
    "google-auth>=2.49",
    "requests>=2.32",
    "httpx>=0.28",
]

[project.scripts]
google-auth-server = "google_auth_server.app:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### Gmail Skill (skills/gmail/)

```toml
[project]
name = "claws-gmail"
version = "0.1.0"
description = "Gmail skill for Lobster Claws"
requires-python = ">=3.12"
dependencies = ["claws-common"]

[project.scripts]
claws-gmail = "claws_gmail.cli:main"

[project.entry-points."claws.skills"]
gmail = "claws_gmail.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv.sources]
claws-common = { workspace = true }
```

### Root pyproject.toml additions

```toml
[dependency-groups]
dev = [
    # ... existing entries ...
    "google-auth-server",
    "claws-gmail",
]

[tool.uv.sources]
# ... existing entries ...
google-auth-server = { workspace = true }
claws-gmail = { workspace = true }
```

## Why requests Is Acceptable Here

Adding `requests` alongside `httpx` seems like a violation of the "one HTTP library" principle. It is not, because:

1. `requests` is used exclusively as a transport adapter for `google-auth`'s `credentials.refresh()` method. It is never used directly for making API calls.
2. `google-auth` only ships transports for `requests` and `aiohttp`. There is no httpx transport.
3. This dependency is confined to the auth server on the host. It never enters the container.
4. The alternative (writing a custom httpx transport for google-auth) adds complexity and maintenance burden for no user-facing benefit.

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| google-auth + httpx (direct REST) | google-api-python-client | If you need complex Google API features like batch requests, resumable media upload, or discovery-based endpoint generation. Gmail read/send/search does not need these. |
| requests (for google-auth transport) | aiohttp (google-auth has async transport) | If the auth server needs high-concurrency token refresh. For a single-user agent making sequential requests, sync transport is simpler. |
| Single auth server for all Google APIs | Separate servers per Google service | Never. The auth server holds one service account key and serves any Google API. Adding Calendar later means adding endpoints, not a new server. |
| Auth server as API proxy | Auth server as token vending machine | Never for this project. Token vending leaks complexity into the container (token expiry handling, direct Google API calls, Gmail-specific error handling). |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| google-api-python-client | Pulls in httplib2, protobuf, uritemplate, google-api-core. Adds ~15MB+ of dependencies for 3 REST endpoints. Creates a second HTTP stack alongside httpx. | Direct httpx calls to Gmail REST API with bearer token from google-auth credentials. |
| google-auth-httplib2 | Only needed if using google-api-python-client. httplib2 is a legacy HTTP library. | httpx for outbound API calls. |
| google-auth-oauthlib | For interactive OAuth consent flows. Service accounts with domain-wide delegation do not use OAuth consent. | google-auth with `service_account.Credentials` directly. |
| oauth2client | Deprecated since 2017. Replaced by google-auth. | google-auth. |
| simplegmail | Third-party wrapper with heavy dependencies, assumes interactive OAuth user flow. | Direct REST calls via httpx. |
| Any Google library in the container | Container should stay thin. All Google complexity belongs on the host. | ClawsClient calling the auth server. |

## Port Assignment

| Server | Port | Status |
|--------|------|--------|
| whisper-server | 8300 | Existing |
| google-auth-server | 8301 | New -- next in 8300+ range |

## Gmail API Scopes Needed

| Scope | Purpose |
|-------|---------|
| `https://www.googleapis.com/auth/gmail.readonly` | Read inbox, search messages |
| `https://www.googleapis.com/auth/gmail.send` | Send emails |

These scopes must be authorized for the service account's client ID in the Google Workspace Admin Console under domain-wide delegation settings.

## Gmail REST API Endpoints Used

| Operation | Method | Endpoint |
|-----------|--------|----------|
| List/search messages | GET | `https://gmail.googleapis.com/gmail/v1/users/{userId}/messages?q={query}` |
| Get message | GET | `https://gmail.googleapis.com/gmail/v1/users/{userId}/messages/{id}` |
| Send message | POST | `https://gmail.googleapis.com/gmail/v1/users/{userId}/messages/send` |

The `userId` is the delegated user's email address (the `subject` in service account credentials). Can also use `me` when the access token is scoped to a specific user.

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| google-auth >=2.49 | Python >=3.10 | Python 3.8/3.9 EOL. Project requires >=3.12, well within support. |
| google-auth >=2.49 | requests >=2.20 | google-auth's requests transport has minimal version requirements. |
| requests >=2.32 | Python >=3.8 | No compatibility concerns with Python 3.12. |
| FastAPI >=0.135 | uvicorn >=0.42 | Same versions already used by whisper-server. |
| httpx >=0.28 | Python >=3.12 | Already in use via claws-common. |

## Service Account Setup (Prerequisites, Not Code)

The auth server needs a service account JSON key file on the host:
1. Google Cloud project with Gmail API enabled
2. Service account created with domain-wide delegation enabled in GCP console
3. Google Workspace Admin Console: authorize service account client ID for Gmail scopes listed above
4. Key file downloaded to host (e.g., `~/.config/lobster-claws/service-account.json`)
5. Path to key file configured via environment variable (e.g., `GOOGLE_SERVICE_ACCOUNT_KEY`)

## Sources

- [google-auth PyPI](https://pypi.org/project/google-auth/) -- version 2.49.1, released 2026-03-12 (HIGH confidence)
- [google.oauth2.service_account docs](https://googleapis.dev/python/google-auth/latest/reference/google.oauth2.service_account.html) -- Credentials API, with_subject(), with_scopes() (HIGH confidence)
- [Gmail REST API reference](https://developers.google.com/gmail/api/reference/rest) -- endpoint URLs for messages list/get/send (HIGH confidence)
- [Google OAuth2 server-to-server guide](https://developers.google.com/identity/protocols/oauth2/service-account) -- domain-wide delegation flow (HIGH confidence)
- [google-auth user guide](https://googleapis.dev/python/google-auth/latest/user-guide.html) -- transport requirements for credential refresh (HIGH confidence)
- [google-auth transport.requests docs](https://google-auth.readthedocs.io/en/latest/reference/google.auth.transport.requests.html) -- Request class for token refresh (HIGH confidence)
- [google-auth GitHub issue #1785](https://github.com/googleapis/google-auth-library-python/issues/1785) -- confirms no ADC shortcut for domain-wide delegation; explicit credential management required (HIGH confidence)

---
*Stack research for: Google auth server + Gmail skill*
*Researched: 2026-03-19*
