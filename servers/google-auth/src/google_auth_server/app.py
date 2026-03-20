"""Google auth token vending server.

Loads a service account key, mints access tokens with domain-wide delegation,
caches them, and serves via POST /token. Validates delegation at startup.
"""

from __future__ import annotations

import os
import sys
import time
from contextlib import asynccontextmanager

import google.auth.transport.requests as google_auth_transport
from fastapi import FastAPI, HTTPException
from google.oauth2 import service_account
from pydantic import BaseModel

DEFAULT_PORT = 8301
DEFAULT_HOST = "127.0.0.1"

# Scopes used for startup validation
STARTUP_VALIDATION_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class TokenRequest(BaseModel):
    scopes: list[str]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load credentials and validate delegation at startup."""
    key_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_KEY")
    subject = os.environ.get("GOOGLE_DELEGATED_USER")

    if not key_path:
        print("FATAL: GOOGLE_SERVICE_ACCOUNT_KEY not set", file=sys.stderr)
        sys.exit(1)
    if not subject:
        print("FATAL: GOOGLE_DELEGATED_USER not set", file=sys.stderr)
        sys.exit(1)

    print(f"Loading service account key from: {key_path}", file=sys.stderr)
    base_creds = service_account.Credentials.from_service_account_file(
        key_path, subject=subject
    )

    # Validate delegation by minting a real token
    print(f"Validating delegation for {subject}...", file=sys.stderr)
    try:
        validation_creds = base_creds.with_scopes(STARTUP_VALIDATION_SCOPES)
        validation_creds.refresh(google_auth_transport.Request())
        print("Delegation validated successfully", file=sys.stderr)
    except Exception as e:
        print(f"FATAL: Delegation validation failed: {e}", file=sys.stderr)
        print(
            "Check: (1) Service account has domain-wide delegation enabled in GCP Console, "
            "(2) Client ID is authorized in Workspace Admin > Security > API Controls > "
            "Domain-wide Delegation with the required scopes.",
            file=sys.stderr,
        )
        sys.exit(1)

    app.state.base_creds = base_creds
    app.state.delegated_user = subject
    app.state.verified_scopes = STARTUP_VALIDATION_SCOPES
    app.state.token_cache = {}
    yield


app = FastAPI(title="google-auth-server", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health():
    """Health check with delegation info."""
    return {
        "status": "ok",
        "service": "google-auth-server",
        "subject": app.state.delegated_user,
        "verified_scopes": app.state.verified_scopes,
    }


@app.post("/token")
async def get_token(req: TokenRequest):
    """Mint or return cached access token for requested scopes."""
    if not req.scopes:
        raise HTTPException(status_code=400, detail="scopes must not be empty")

    cache_key = frozenset(req.scopes)
    now = time.time()

    # Return cached token if >60s remaining
    cached = app.state.token_cache.get(cache_key)
    if cached and cached["expires_at"] > now + 60:
        return {
            "access_token": cached["access_token"],
            "expires_in": int(cached["expires_at"] - now),
            "token_type": "Bearer",
        }

    # Mint new token with one retry for transient errors
    creds = app.state.base_creds.with_scopes(list(req.scopes))
    last_error = None
    for attempt in range(2):
        try:
            creds.refresh(google_auth_transport.Request())
            break
        except Exception as e:
            last_error = e
            if attempt == 0:
                time.sleep(0.5)
    else:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to mint token after retry: {last_error}",
        )

    expires_at = creds.expiry.timestamp()
    app.state.token_cache[cache_key] = {
        "access_token": creds.token,
        "expires_at": expires_at,
    }

    return {
        "access_token": creds.token,
        "expires_in": int(expires_at - now),
        "token_type": "Bearer",
    }


def main():
    """Entry point for google-auth-server CLI."""
    import uvicorn

    uvicorn.run(app, host=DEFAULT_HOST, port=DEFAULT_PORT)
