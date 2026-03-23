---
phase: 01
slug: add-google-tasks-contacts-sheets-and-docs-skills
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 01 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | `pyproject.toml` (root) |
| **Quick run command** | `uv run pytest skills/tasks skills/contacts skills/sheets skills/docs -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest skills/{skill} -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | TBD | unit | `uv run pytest skills/{skill} -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `skills/tasks/tests/__init__.py` — test package init
- [ ] `skills/contacts/tests/__init__.py` — test package init
- [ ] `skills/sheets/tests/__init__.py` — test package init
- [ ] `skills/docs/tests/__init__.py` — test package init

*Existing infrastructure (pytest, pytest-httpx, mock patterns) covers all framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Google API delegation | N/A | Requires live service account + Workspace setup | Configure scopes in Workspace Admin, run `claws tasks list` |

*All other behaviors have automated verification via mocked tests.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
