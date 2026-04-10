# app/security.py
import httpx
from datetime import datetime, timezone
from app.config import settings
from app.prompts import INJECTION_TOKENS

# ── Token budget ──────────────────────────────────────────────────────────────
# In-memory counter. Resets on new UTC day or server restart.
# Acceptable for portfolio traffic — production would use Redis.
_budget_state: dict = {"date": None, "used": 0}


def get_today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def check_and_increment_budget(tokens: int) -> bool:
    """Return True and increment if budget allows. Return False if exceeded."""
    today = get_today_utc()
    if _budget_state["date"] != today:
        _budget_state["date"] = today
        _budget_state["used"] = 0
    # No await between check and increment — safe under single-worker asyncio (no race condition)
    if _budget_state["used"] + tokens > settings.daily_token_budget:
        return False
    _budget_state["used"] += tokens
    return True


def get_budget_remaining() -> int:
    today = get_today_utc()
    if _budget_state["date"] != today:
        return settings.daily_token_budget
    return max(0, settings.daily_token_budget - _budget_state["used"])


# ── Input sanitization ────────────────────────────────────────────────────────

def sanitize_input(text: str) -> str:
    """Strip known prompt-injection delimiter tokens. Silently — never error."""
    text = text.strip()
    for token in INJECTION_TOKENS:
        text = text.replace(token, "")
    return text


# ── reCAPTCHA ─────────────────────────────────────────────────────────────────

async def verify_recaptcha_v3(token: str) -> float:
    """Verify reCAPTCHA v3 token. Returns score 0.0–1.0. Returns 0.0 on any failure."""
    if not token:
        return 0.0
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={"secret": settings.recaptcha_v3_secret_key, "response": token},
            )
            data = resp.json()
            if data.get("success"):
                return float(data.get("score", 0.0))
    except Exception:
        pass
    return 0.0


async def verify_recaptcha_v2(token: str) -> bool:
    """Verify reCAPTCHA v2 token. Returns True if valid, False otherwise."""
    if not token:
        return False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={"secret": settings.recaptcha_v2_secret_key, "response": token},
            )
            data = resp.json()
            return bool(data.get("success", False))
    except Exception:
        pass
    return False
