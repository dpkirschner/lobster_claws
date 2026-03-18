"""Whisper transcription server using mlx-whisper on Apple Silicon.

Provides POST /transcribe (audio file upload) and GET /health endpoints.
Model is preloaded at startup via FastAPI lifespan to avoid cold-start latency.
"""

from __future__ import annotations

import sys
import tempfile
from contextlib import asynccontextmanager

import mlx_whisper
from fastapi import FastAPI, Query, UploadFile

DEFAULT_MODEL = "mlx-community/whisper-turbo"
DEFAULT_PORT = 8300


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Preload the default model at server startup."""
    print(f"Preloading model: {DEFAULT_MODEL}", file=sys.stderr)
    try:
        from mlx_whisper.transcribe import ModelHolder

        ModelHolder.get_model(DEFAULT_MODEL)
    except (ImportError, Exception):
        # Fallback: trigger model download by running a dummy transcribe
        try:
            mlx_whisper.transcribe("", path_or_hf_repo=DEFAULT_MODEL)
        except Exception:
            pass
    yield


app = FastAPI(title="whisper-server", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "whisper-server",
        "default_model": DEFAULT_MODEL,
    }


@app.post("/transcribe")
async def transcribe(file: UploadFile, model: str | None = Query(default=None)):
    """Transcribe an uploaded audio file using mlx-whisper."""
    model_id = model or DEFAULT_MODEL
    suffix = (
        "." + file.filename.rsplit(".", 1)[-1]
        if file.filename and "." in file.filename
        else ".wav"
    )

    content = await file.read()

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        tmp.write(content)
        tmp.flush()
        result = mlx_whisper.transcribe(tmp.name, path_or_hf_repo=model_id)

    # Free GPU memory after transcription
    try:
        import mlx.core as mx

        mx.metal.clear_cache()
    except (ImportError, AttributeError):
        pass

    return {"text": result["text"]}


def main():
    """Entry point for whisper-server CLI."""
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=DEFAULT_PORT)
