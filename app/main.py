# app/main.py
import json
from collections import defaultdict
from time import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, field_validator

from app.config import settings
from app.prompts import VALID_PERSONALITIES, ERROR_MESSAGES
from app.security import (
    sanitize_input,
    verify_recaptcha_v3,
    verify_recaptcha_v2,
    check_and_increment_budget,
    get_budget_remaining,
)
from app.rag import stream_response, warmup

# ── Rate limiter ──────────────────────────────────────────────────────────────
# Simple sliding-window counter. Single-worker asyncio — no race conditions.
# Railway sits behind a reverse proxy; real client IP is in X-Forwarded-For.
_rate_store: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT = 5
RATE_WINDOW = 60  # seconds


def _real_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _is_rate_limited(ip: str) -> bool:
    now = time()
    cutoff = now - RATE_WINDOW
    timestamps = _rate_store[ip]
    timestamps[:] = [t for t in timestamps if t > cutoff]
    if len(timestamps) >= RATE_LIMIT:
        return True
    timestamps.append(now)
    return False


app = FastAPI(title="Yoko — Portfolio Chatbot API", docs_url=None, redoc_url=None)


@app.on_event("startup")
async def startup_event():
    warmup()

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["content-type"],
)


# ── User-Agent middleware ─────────────────────────────────────────────────────
@app.middleware("http")
async def require_user_agent(request: Request, call_next):
    if request.method in ("POST", "PUT", "PATCH"):
        ua = request.headers.get("user-agent", "").strip()
        if not ua:
            return JSONResponse(
                {"detail": "User-Agent header required"},
                status_code=400,
            )
    return await call_next(request)


# ── Request schema ────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    personality: str = settings.default_personality
    recaptcha_v3_token: str = ""
    recaptcha_v2_token: str = ""

    @field_validator("message")
    @classmethod
    def message_length(cls, v: str) -> str:
        if len(v) > 200:
            raise ValueError("Message exceeds 200 characters")
        return v

    @field_validator("personality")
    @classmethod
    def personality_allowed(cls, v: str) -> str:
        if v not in VALID_PERSONALITIES:
            raise ValueError(f"personality must be one of {VALID_PERSONALITIES}")
        return v


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "budget_remaining": get_budget_remaining()}


@app.post("/chat")
async def chat(request: Request, body: ChatRequest):
    # 1. Rate limit
    ip = _real_ip(request)
    if _is_rate_limited(ip):
        return JSONResponse(
            {"detail": ERROR_MESSAGES["rate_limit"]},
            status_code=429,
        )

    # 2. reCAPTCHA v3
    score = await verify_recaptcha_v3(body.recaptcha_v3_token)
    if score < 0.5:
        if not body.recaptcha_v2_token:
            return JSONResponse({"challenge": True})
        v2_ok = await verify_recaptcha_v2(body.recaptcha_v2_token)
        if not v2_ok:
            return JSONResponse({"error": ERROR_MESSAGES["recaptcha"]}, status_code=403)

    # 3. Daily budget pre-check (exact deduction happens post-stream)
    if get_budget_remaining() <= 0:
        return JSONResponse({"error": ERROR_MESSAGES["daily_budget"]}, status_code=429)

    # 4. Sanitize
    clean_message = sanitize_input(body.message)

    # 5. Stream
    async def generate():
        total_tokens = 0
        async for text, tokens in stream_response(clean_message, body.personality):
            if tokens is not None:
                total_tokens = tokens
            else:
                yield f"data: {json.dumps({'text': text})}\n\n"
        check_and_increment_budget(total_tokens)
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
