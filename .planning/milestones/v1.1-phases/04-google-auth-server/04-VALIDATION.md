---
phase: 4
slug: google-auth-server
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | `pyproject.toml` (root — testpaths configured) |
| **Quick run command** | `uv run pytest common/tests servers/google-auth/tests -x -q` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest common/tests servers/google-auth/tests -x -q`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | CLI-01 | unit | `uv run pytest common/tests -x -q` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | CLI-02 | unit | `uv run pytest common/tests -x -q` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 1 | AUTH-01, AUTH-02 | unit | `uv run pytest servers/google-auth/tests -x -q` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 1 | AUTH-03 | unit | `uv run pytest servers/google-auth/tests -x -q` | ❌ W0 | ⬜ pending |
| 04-02-03 | 02 | 1 | AUTH-04 | unit | `uv run pytest servers/google-auth/tests -x -q` | ❌ W0 | ⬜ pending |
| 04-02-04 | 02 | 1 | AUTH-05, AUTH-06 | unit | `uv run pytest servers/google-auth/tests -x -q` | ❌ W0 | ⬜ pending |
| 04-02-05 | 02 | 1 | AUTH-07 | unit | `uv run pytest tests/ -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `servers/google-auth/tests/test_app.py` — stubs for AUTH-01 through AUTH-07
- [ ] `common/tests/test_client.py` — add stubs for post_json and get-with-params (CLI-01, CLI-02)

*Existing test infrastructure covers framework and fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Launchd auto-start on boot | AUTH-07 | Requires macOS reboot or launchctl load | Load plist with `launchctl load`, verify server starts, check logs |
| End-to-end Google token minting | AUTH-02 | Requires real service account + Workspace delegation | POST /token with valid scopes, verify returned token works against Gmail API |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
