"""The single place model calls happen.

LLM_PROVIDER selects the backend:
  mock    - offline echo, used for local dev and tests (default)
  vertex  - Gemini on Vertex AI via google-genai (uses ADC / Cloud Run service account)
  bedrock - Amazon Bedrock Converse API via boto3 (uses AWS profile / Lambda role)

SDKs are imported lazily, so you only need credentials for the provider you use.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


class LLMError(RuntimeError):
    """Raised when the upstream model call fails."""


@dataclass(frozen=True)
class LLMResult:
    text: str
    provider: str
    model: str


def provider_name() -> str:
    return os.getenv("LLM_PROVIDER", "mock").lower()


def model_name() -> str:
    p = provider_name()
    if p == "vertex":
        return os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    if p == "bedrock":
        return os.getenv("BEDROCK_MODEL_ID", "us.amazon.nova-lite-v1:0")
    return "mock"


def generate(prompt: str, system: str | None = None, max_tokens: int = 1024) -> LLMResult:
    p = provider_name()
    try:
        if p == "vertex":
            text = _vertex(prompt, system, max_tokens)
        elif p == "bedrock":
            text = _bedrock(prompt, system, max_tokens)
        elif p == "mock":
            text = f"[mock] You said: {prompt[:200]}"
        else:
            raise LLMError(f"Unknown LLM_PROVIDER={p!r} (use mock|vertex|bedrock)")
    except LLMError:
        raise
    except Exception as exc:  # surface SDK/auth errors as one type the API can map to 502
        raise LLMError(f"{p} call failed: {type(exc).__name__}: {exc}") from exc
    return LLMResult(text=text, provider=p, model=model_name())


# --- Vertex AI (Gemini) -------------------------------------------------------


@lru_cache(maxsize=1)
def _vertex_client():
    from google import genai

    return genai.Client(
        vertexai=True,
        project=os.environ["GOOGLE_CLOUD_PROJECT"],
        location=os.getenv("GOOGLE_CLOUD_LOCATION", "global"),
    )


def _vertex(prompt: str, system: str | None, max_tokens: int) -> str:
    from google.genai import types

    resp = _vertex_client().models.generate_content(
        model=model_name(),
        contents=prompt,
        config=types.GenerateContentConfig(system_instruction=system, max_output_tokens=max_tokens),
    )
    return resp.text or ""


# --- Amazon Bedrock -----------------------------------------------------------


@lru_cache(maxsize=1)
def _bedrock_client():
    import boto3

    return boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))


def _bedrock(prompt: str, system: str | None, max_tokens: int) -> str:
    kwargs = {
        "modelId": model_name(),
        "messages": [{"role": "user", "content": [{"text": prompt}]}],
        "inferenceConfig": {"maxTokens": max_tokens},
    }
    if system:
        kwargs["system"] = [{"text": system}]
    resp = _bedrock_client().converse(**kwargs)
    blocks = resp["output"]["message"]["content"]
    return "".join(b.get("text", "") for b in blocks)
