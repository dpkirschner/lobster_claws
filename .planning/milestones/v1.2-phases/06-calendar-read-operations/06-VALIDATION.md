---
phase: 6
slug: calendar-read-operations
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | `pyproject.toml` (root — testpaths configured) |
| **Quick run command** | `uv run pytest skills/calendar/tests -x -q` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~3 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest skills/calendar/tests -x -q`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 3 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | CAL-01, CAL-02, CAL-06 | unit | `uv run pytest skills/calendar/tests -x -q` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 2 | CAL-01, CAL-02, CAL-07 | unit | `uv run pytest skills/calendar/tests -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `skills/calendar/tests/test_calendar_api.py` — stubs for CAL-01, CAL-02, CAL-06
- [ ] `skills/calendar/tests/test_calendar_cli.py` — stubs for CAL-07

*Existing test infrastructure covers framework and fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end event listing | CAL-01 | Requires real Calendar with delegation | Run `claws calendar list`, verify JSON matches actual calendar |
| End-to-end event details | CAL-02 | Requires real Calendar with events | Run `claws calendar get <id>`, verify details match |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 3s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
