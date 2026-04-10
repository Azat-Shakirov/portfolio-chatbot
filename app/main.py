# app/main.py
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
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
from app.rag import stream_response

# ── Rate limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["5/minute"])

app = FastAPI(title="Yoko — Portfolio Chatbot API", docs_url="/docs")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
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
    personality: str = "casual"
    recaptcha_v3_token: str = ""
    recaptcha_v2_token: str = ""

    @field_validator("message")
    @classmethod
    def message_length(cls, v: str) -> str:
        if len(v) > 500:
            raise ValueError("Message exceeds 500 characters")
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
@limiter.limit("5/minute")
async def chat(request: Request, body: ChatRequest):
    # 1. reCAPTCHA v3
    score = await verify_recaptcha_v3(body.recaptcha_v3_token)
    if score < 0.5:
        if not body.recaptcha_v2_token:
            return JSONResponse({"challenge": True})
        v2_ok = await verify_recaptcha_v2(body.recaptcha_v2_token)
        if not v2_ok:
            raise HTTPException(status_code=403, detail=ERROR_MESSAGES["recaptcha"])

    # 2. Daily budget pre-check (rough guard — exact deduction happens post-stream)
    if get_budget_remaining() < 100:
        raise HTTPException(status_code=429, detail=ERROR_MESSAGES["daily_budget"])

    # 3. Sanitize
    clean_message = sanitize_input(body.message)

    # 4. Stream
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
