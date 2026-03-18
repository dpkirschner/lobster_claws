"""Tests for whisper-server FastAPI application.

All tests mock mlx_whisper so no GPU or model download is required.
"""

from __future__ import annotations

import io
import struct
import sys
from contextlib import asynccontextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def _make_wav_bytes(duration_ms: int = 100, sample_rate: int = 16000) -> bytes:
    """Create a minimal valid WAV file in memory."""
    num_samples = int(sample_rate * duration_ms / 1000)
    data_size = num_samples * 2  # 16-bit mono
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,  # chunk size
        1,  # PCM
        1,  # mono
        sample_rate,
        sample_rate * 2,  # byte rate
        2,  # block align
        16,  # bits per sample
        b"data",
        data_size,
    )
    return header + b"\x00" * data_size


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# We need to mock mlx_whisper before importing app, since app imports it at
# module level (or uses it in lifespan).

_mock_mlx_whisper = MagicMock()
_mock_mlx_whisper.transcribe.return_value = {"text": " hello world"}

# Mock mx module for metal cache clearing
_mock_mx = MagicMock()
_mock_mx.metal = MagicMock()
_mock_mx.metal.clear_cache = MagicMock()


@pytest.fixture()
def client():
    """Create a TestClient with mlx_whisper mocked out."""
    with patch.dict(
        sys.modules,
        {
            "mlx_whisper": _mock_mlx_whisper,
            "mlx_whisper.transcribe": MagicMock(ModelHolder=MagicMock()),
            "mx": _mock_mx,
            "mlx.core": _mock_mx,
        },
    ):
        # Reset call counts between tests
        _mock_mlx_whisper.transcribe.reset_mock()
        _mock_mx.metal.clear_cache.reset_mock()

        # Force re-import so the app picks up our mocks
        if "whisper_server.app" in sys.modules:
            del sys.modules["whisper_server.app"]

        from whisper_server.app import app

        with TestClient(app) as tc:
            yield tc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_health(client: TestClient):
    """GET /health returns status, service name, and default model (WHSP-02)."""
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "whisper-server"
    assert body["default_model"] == "mlx-community/whisper-turbo"


def test_transcribe(client: TestClient):
    """POST /transcribe with audio file returns transcription text (WHSP-01)."""
    wav = _make_wav_bytes()
    resp = client.post(
        "/transcribe",
        files={"file": ("test.wav", io.BytesIO(wav), "audio/wav")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "text" in body
    assert body["text"].strip() == "hello world"
    # Verify mlx_whisper.transcribe was called with default model
    _mock_mlx_whisper.transcribe.assert_called_once()
    call_kwargs = _mock_mlx_whisper.transcribe.call_args
    assert call_kwargs[1]["path_or_hf_repo"] == "mlx-community/whisper-turbo"


def test_transcribe_with_model(client: TestClient):
    """POST /transcribe?model=... passes custom model to mlx_whisper (WHSP-03)."""
    wav = _make_wav_bytes()
    custom_model = "mlx-community/whisper-large-v3-mlx"
    resp = client.post(
        f"/transcribe?model={custom_model}",
        files={"file": ("test.wav", io.BytesIO(wav), "audio/wav")},
    )
    assert resp.status_code == 200
    call_kwargs = _mock_mlx_whisper.transcribe.call_args
    assert call_kwargs[1]["path_or_hf_repo"] == custom_model


def test_model_preload(client: TestClient):
    """Lifespan event triggers model preloading at startup (WHSP-04)."""
    # The TestClient context manager triggers lifespan events.
    # We verify that either ModelHolder.get_model was called or
    # mlx_whisper.transcribe was called during startup.
    # Since we mock mlx_whisper.transcribe.ModelHolder, check that path.
    mlx_whisper_mod = sys.modules.get("mlx_whisper.transcribe")
    if mlx_whisper_mod and hasattr(mlx_whisper_mod, "ModelHolder"):
        # ModelHolder.get_model should have been called during lifespan
        assert mlx_whisper_mod.ModelHolder.get_model.called


def test_transcribe_clears_cache(client: TestClient):
    """After transcription, mx.metal.clear_cache() is called to free GPU memory."""
    wav = _make_wav_bytes()
    client.post(
        "/transcribe",
        files={"file": ("test.wav", io.BytesIO(wav), "audio/wav")},
    )
    _mock_mx.metal.clear_cache.assert_called()
