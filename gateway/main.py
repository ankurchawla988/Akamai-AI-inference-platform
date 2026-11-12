"""FastAPI AI Gateway — routes requests to vLLM (OpenAI-compatible) and proxies SSE token streams."""
import os, time, logging
from contextlib import asynccontextmanager
from typing import List, Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("gateway")

VLLM_URL = os.getenv("VLLM_URL", "http://vllm.ai-platform.svc.cluster.local:8000")
MODEL_NAME = os.getenv("MODEL_NAME", "mistralai/Mistral-7B-Instruct-v0.2")

REQS = Counter("gateway_requests_total", "Requests handled", ["endpoint", "status"])
E2E = Histogram("gateway_request_seconds", "End-to-end request latency", ["endpoint"],
                buckets=(.25, .5, 1, 2, 4, 8, 16, 32, 64))
TTFT = Histogram("gateway_ttft_seconds", "Time to first streamed token",
                 buckets=(.05, .1, .25, .5, 1, 2, 4, 8))
ACTIVE = Gauge("gateway_active_streams", "In-flight streaming requests")


class Message(BaseModel):
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str = Field(..., min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    messages: List[Message]
    max_tokens: int = Field(256, ge=1, le=2048)
    temperature: float = Field(0.7, ge=0, le=2)
    top_p: Optional[float] = Field(0.95, ge=0, le=1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.client = httpx.AsyncClient(base_url=VLLM_URL, timeout=httpx.Timeout(300.0, connect=5.0))
    yield
    await app.state.client.aclose()


app = FastAPI(title="AI Inference Gateway", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _payload(req: ChatRequest, stream: bool) -> dict:
    return {"model": MODEL_NAME, "messages": [m.model_dump() for m in req.messages],
            "max_tokens": req.max_tokens, "temperature": req.temperature,
            "top_p": req.top_p, "stream": stream}


@app.get("/health")
async def health():
    """Gateway liveness + upstream vLLM readiness."""
    try:
        r = await app.state.client.get("/health", timeout=3.0)
        upstream = r.status_code == 200
    except httpx.HTTPError:
        upstream = False
    if not upstream:
        raise HTTPException(503, detail={"gateway": "ok", "vllm": "unavailable"})
    return {"gateway": "ok", "vllm": "ok", "model": MODEL_NAME}


@app.post("/chat")
async def chat(req: ChatRequest):
    """Non-streaming completion."""
    t0 = time.perf_counter()
    try:
        r = await app.state.client.post("/v1/chat/completions", json=_payload(req, False))
        r.raise_for_status()
    except httpx.HTTPError as e:
        REQS.labels("chat", "error").inc()
        raise HTTPException(502, detail=f"vLLM error: {e}")
    data = r.json()
    dt = time.perf_counter() - t0
    E2E.labels("chat").observe(dt)
    REQS.labels("chat", "ok").inc()
    usage = data.get("usage", {})
    return {"content": data["choices"][0]["message"]["content"], "usage": usage,
            "latency_s": round(dt, 3), "model": MODEL_NAME,
            "tokens_per_sec": round(usage.get("completion_tokens", 0) / dt, 1) if dt else 0}


@app.post("/stream")
async def stream(req: ChatRequest):
    """Streaming completion — proxies vLLM's SSE chunks token by token."""
    async def gen():
        ACTIVE.inc()
        t0 = time.perf_counter()
        first = True
        status = "ok"
        try:
            async with app.state.client.stream("POST", "/v1/chat/completions",
                                               json=_payload(req, True)) as r:
                if r.status_code != 200:
                    status = "error"
                    yield f'data: {{"error": "vLLM returned {r.status_code}"}}\n\n'
                    return
                async for line in r.aiter_lines():
                    if not line:
                        continue
                    if first and line.startswith("data:") and "[DONE]" not in line:
                        TTFT.observe(time.perf_counter() - t0)
                        first = False
                    yield line + "\n\n"
        except httpx.HTTPError as e:
            status = "error"
            log.error("stream error: %s", e)
            yield 'data: {"error": "upstream failure"}\n\n'
        finally:
            ACTIVE.dec()
            E2E.labels("stream").observe(time.perf_counter() - t0)
            REQS.labels("stream", status).inc()

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
