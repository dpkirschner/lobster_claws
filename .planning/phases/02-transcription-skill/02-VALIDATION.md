---
phase: 2
slug: transcription-skill
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-17
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0+ |
| **Config file** | Root `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest skills/transcribe/tests servers/whisper/tests -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest skills/transcribe/tests servers/whisper/tests -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 1 | WHSP-01 | unit | `uv run pytest servers/whisper/tests/test_app.py::test_transcribe -x` | ❌ W0 | ⬜ pending |
| 2-01-02 | 01 | 1 | WHSP-02 | unit | `uv run pytest servers/whisper/tests/test_app.py::test_health -x` | ❌ W0 | ⬜ pending |
| 2-01-03 | 01 | 1 | WHSP-03 | unit | `uv run pytest servers/whisper/tests/test_app.py::test_model_selection -x` | ❌ W0 | ⬜ pending |
| 2-01-04 | 01 | 1 | WHSP-04 | unit | `uv run pytest servers/whisper/tests/test_app.py::test_model_preload -x` | ❌ W0 | ⬜ pending |
| 2-02-01 | 02 | 2 | TRNS-01 | unit | `uv run pytest skills/transcribe/tests/test_cli.py::test_transcribe_success -x` | ❌ W0 | ⬜ pending |
| 2-02-02 | 02 | 2 | TRNS-02 | unit | `uv run pytest skills/transcribe/tests/test_cli.py::test_format_flag -x` | ❌ W0 | ⬜ pending |
| 2-02-03 | 02 | 2 | TRNS-03 | unit | `uv run pytest skills/transcribe/tests/test_cli.py::test_model_flag -x` | ❌ W0 | ⬜ pending |
| 2-02-04 | 02 | 2 | TRNS-04 | unit | `uv run pytest skills/transcribe/tests/test_cli.py::test_output_flushed -x` | ❌ W0 | ⬜ pending |
| 2-03-01 | 03 | 3 | INFR-01 | unit | `uv run pytest tests/test_launchd.py::test_plist_valid -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `servers/whisper/tests/test_app.py` — stubs for WHSP-01, WHSP-02, WHSP-03, WHSP-04
- [ ] `skills/transcribe/tests/test_cli.py` — stubs for TRNS-01, TRNS-02, TRNS-03, TRNS-04
- [ ] `tests/test_launchd.py` — stubs for INFR-01 (plist validation)
- [ ] Update root `pyproject.toml` testpaths to include `tests/`
- [ ] Server tests need FastAPI TestClient (`httpx`)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Server auto-starts after reboot | INFR-01 | Requires macOS reboot | Load plist, reboot, verify server responds at port |
| Model stays in memory between requests | WHSP-04 | Requires running mlx-whisper | Send two requests, verify second is faster (no cold start) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
