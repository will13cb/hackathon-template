"""FastAPI entrypoint. Serves the API under /api and the static frontend at /."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import llm

WEB_DIR = Path(__file__).resolve().parents[2] / "web"

app = FastAPI(title="hackathon-app", version="0.1.0")


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)
    system: str | None = Field(default=None, max_length=4000)


class GenerateResponse(BaseModel):
    text: str
    provider: str
    model: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "provider": llm.provider_name(), "model": llm.model_name()}


@app.post("/api/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest) -> GenerateResponse:
    try:
        result = llm.generate(req.prompt, req.system)
    except llm.LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return GenerateResponse(text=result.text, provider=result.provider, model=result.model)


# Keep this last: the static mount at "/" catches everything not matched above.
if WEB_DIR.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
