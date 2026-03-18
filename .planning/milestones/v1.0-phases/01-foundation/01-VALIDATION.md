---
phase: 1
slug: foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-17
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | Root `pyproject.toml` `[tool.pytest.ini_options]` — Wave 0 installs |
| **Quick run command** | `uv run pytest common/tests/ -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest common/tests/ -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | INFR-02 | manual | Visual inspection | N/A | ⬜ pending |
| 1-01-02 | 01 | 1 | INFR-03 | integration | `uv sync --frozen` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 1 | LIB-01 | unit | `uv run pytest common/tests/test_host.py -x` | ❌ W0 | ⬜ pending |
| 1-02-02 | 02 | 1 | LIB-02 | unit | `uv run pytest common/tests/test_client.py -x` | ❌ W0 | ⬜ pending |
| 1-02-03 | 02 | 1 | LIB-03 | unit | `uv run pytest common/tests/test_output.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `common/tests/test_host.py` — stubs for LIB-01
- [ ] `common/tests/test_client.py` — stubs for LIB-02
- [ ] `common/tests/test_output.py` — stubs for LIB-03
- [ ] Root `pyproject.toml` with `[tool.pytest.ini_options]` — test config
- [ ] `pytest` and `pytest-httpx` in dev dependency group

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| .gitignore contains standard Python patterns | INFR-02 | Static file, visual check sufficient | Verify file exists and contains `__pycache__/`, `*.egg-info/`, `.venv/` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
