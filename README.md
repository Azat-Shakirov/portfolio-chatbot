# Yoko — Portfolio AI Chatbot (Backend)

RAG-powered chatbot backend for [my portfolio](https://portfolio-three-rho-w5f73tqssv.vercel.app/).
FastAPI + LangChain + ChromaDB + Claude API. Deployed on Railway.

## Stack
- **LLM:** Claude `claude-sonnet-4-20250514` (Anthropic)
- **Embeddings:** `all-MiniLM-L6-v2` via sentence-transformers (local, free)
- **Vector store:** ChromaDB (persisted on Railway volume)
- **Framework:** FastAPI + uvicorn
- **Security:** reCAPTCHA v3→v2 fallback · custom sliding-window rate limiter · 50k daily token budget · input sanitization

## Local Setup

### Prerequisites
- Python 3.11+
- Docker (for Railway deploy testing)
- A Claude API key from console.anthropic.com
- reCAPTCHA v3 + v2 keys from google.com/recaptcha (free)

### Run locally

```bash
# 1. Clone and install
git clone <this-repo>
cd portfolio-chatbot
pip install -r requirements.txt

# 2. Configure env
cp .env.example .env
# Edit .env and fill in CLAUDE_API_KEY, RECAPTCHA_V3_SECRET_KEY, RECAPTCHA_V2_SECRET_KEY

# 3. Build ChromaDB index
python app/ingest.py

# 4. Start server
uvicorn app.main:app --reload --port 8000

# 5. Verify
curl http://localhost:8000/health
```

### Update the portfolio data
1. Edit `data/about_me.txt`
2. Re-run `python app/ingest.py`
3. Restart the server (or trigger a Railway redeploy — `start.sh` re-ingests automatically if the ChromaDB volume is cleared)

## Common operations

| Task | Command / Location |
|---|---|
| Rebuild index after editing about_me.txt | `python app/ingest.py` |
| Change Yoko's tone or rules | Edit `app/prompts.py` |
| Add a personality mode | Add entry to `PERSONALITY_MODIFIERS` in `prompts.py` |
| Change rate limit | Edit `RATE_LIMIT` / `RATE_WINDOW` in `app/main.py` |
| Change daily token budget | Set `DAILY_TOKEN_BUDGET` in Railway env vars |
| Check token budget | `GET /health` |
| Suppress ChromaDB telemetry logs | Set `ANONYMIZED_TELEMETRY=false` in Railway env vars |

## Railway Deploy

1. Create a Railway project, connect this repo (`master` branch)
2. Add a persistent volume mounted at `/app/chroma_db`
3. Set all env vars (see below) in Railway dashboard
4. Set start command to `bash start.sh`
5. Deploy — `start.sh` runs ingestion on first deploy automatically

### Required environment variables

```
CLAUDE_API_KEY=
RECAPTCHA_V3_SECRET_KEY=
RECAPTCHA_V2_SECRET_KEY=
ALLOWED_ORIGINS=https://your-vercel-domain.vercel.app
DAILY_TOKEN_BUDGET=50000
DEFAULT_PERSONALITY=azat
SKIP_RECAPTCHA=false
```

## Frontend

The chat widget lives in the separate portfolio repo at `/components/ChatWidget.tsx`.
Frontend env vars (Vercel dashboard + `.env.local`):
```
NEXT_PUBLIC_RECAPTCHA_V3_SITE_KEY=
NEXT_PUBLIC_RECAPTCHA_V2_SITE_KEY=
NEXT_PUBLIC_BACKEND_URL=https://your-railway-url.up.railway.app
```

`NEXT_PUBLIC_BACKEND_URL` must include `https://` — the full URL, not just the hostname.

## Security model

I had to make every one of these decisions without a playbook. They hold up in production, but I documented the reasoning in case something breaks later.

- **reCAPTCHA v3** (invisible) on every send. Score < 0.5 triggers v2 checkbox fallback.
- **Rate limiting:** 5 requests/IP/minute. Custom sliding-window counter reading real client IP from `X-Forwarded-For` — Railway's reverse proxy sets this correctly. The default SlowAPI integration was silently doing nothing; see `challenges.txt`.
- **Daily token budget:** 50k tokens/day in-memory counter, resets midnight UTC.
- **Input sanitization:** known prompt-injection delimiter tokens stripped before reaching the LLM.
- **CORS:** restricted to portfolio domain only, with an explicit header allowlist.
- **Claude API key:** server-side only, never exposed to frontend.
- **Jailbreak-resistant system prompt:** see `app/prompts.py`. Topic restrictions enforced at the API role level, not just string matching.
- **API surface:** `/docs` and `/redoc` disabled in production.

## Known limitations

The token budget is in-memory — it resets on server restart and doesn't persist across Railway redeploys unless you add a Redis store. The rate limiter is also per-instance; it wouldn't scale correctly across multiple Railway replicas. Currently running one replica, so this isn't a problem yet.

## Engineering notes

See `challenges.txt` for a detailed account of the actual problems I ran into during development and deployment — Docker image size, dependency version conflicts, CORS misconfigurations, and the silent rate-limiter failure.
