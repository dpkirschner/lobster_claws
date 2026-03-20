---
phase: 5
slug: gmail-skill
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | `pyproject.toml` (root — testpaths configured) |
| **Quick run command** | `uv run pytest skills/gmail/tests -x -q` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~3 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest skills/gmail/tests -x -q`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 3 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | GMAIL-01, GMAIL-04 | unit | `uv run pytest skills/gmail/tests -x -q` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | GMAIL-02 | unit | `uv run pytest skills/gmail/tests -x -q` | ❌ W0 | ⬜ pending |
| 05-01-03 | 01 | 1 | GMAIL-03 | unit | `uv run pytest skills/gmail/tests -x -q` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 1 | GMAIL-05, GMAIL-06 | unit | `uv run pytest skills/gmail/tests -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `skills/gmail/tests/test_gmail.py` — stubs for GMAIL-01 through GMAIL-06
- [ ] `skills/gmail/tests/conftest.py` — shared fixtures (mock httpx responses, mock ClawsClient)

*Existing test infrastructure covers framework and fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end inbox listing | GMAIL-01 | Requires real Gmail account with delegation | Run `claws gmail inbox`, verify JSON output matches inbox |
| End-to-end email send | GMAIL-03 | Requires real Gmail delegation + recipient mailbox | Run `claws gmail send --to test@... --subject Test --body Hi`, verify email received |
| Gmail search syntax | GMAIL-04 | Requires real inbox with searchable messages | Run `claws gmail search "from:known-sender"`, verify results match |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 3s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
