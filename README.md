# Yoko — Portfolio AI Chatbot (Backend)

RAG-powered chatbot backend for [Azat Shakirov's portfolio](https://portfolio-three-rho-w5f73tqssv.vercel.app/).
Built with FastAPI + LangChain + ChromaDB + Claude API. Deployed on Railway.

## Stack
- **LLM:** Claude `claude-sonnet-4-20250514` (Anthropic)
- **Embeddings:** `all-MiniLM-L6-v2` via sentence-transformers (local, free)
- **Vector store:** ChromaDB (persisted on Railway volume)
- **Framework:** FastAPI + uvicorn
- **Security:** reCAPTCHA v3→v2 fallback · SlowAPI rate limiting · 50k daily token budget · input sanitization

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

### Update Azat's info
1. Edit `data/about_me.txt`
2. Re-run `python app/ingest.py`
3. Restart server

### Run tests
```bash
pytest -v
```

## Common operations

| Task | Command |
|---|---|
| Rebuild index after editing about_me.txt | `python app/ingest.py` |
| Change Yoko's tone or rules | Edit `app/prompts.py` |
| Add a personality mode | Add one entry to `PERSONALITY_MODIFIERS` in `prompts.py` + one button in `ChatWidget.tsx` |
| Change rate limit | Edit `ALLOWED_ORIGINS` or `DEFAULT_PERSONALITY` in `.env` |
| Check token budget | `GET /health` |

## Railway Deploy

1. Create a Railway project, connect this repo
2. Add a persistent volume mounted at `/app/chroma_db`
3. Set all env vars from `.env.example` in Railway dashboard
4. Deploy — `start.sh` runs ingestion on first deploy automatically

## Frontend

The chat widget lives in the separate portfolio repo at `/components/ChatWidget.tsx`.
Frontend env vars (Vercel dashboard + `.env.local`):
```
NEXT_PUBLIC_RECAPTCHA_V3_SITE_KEY=
NEXT_PUBLIC_RECAPTCHA_V2_SITE_KEY=
NEXT_PUBLIC_BACKEND_URL=https://your-railway-url.railway.app
```

## Security model

- reCAPTCHA v3 (invisible) on every send; score < 0.5 triggers v2 checkbox fallback
- 5 requests/IP/minute (SlowAPI)
- 50k daily token budget (in-memory, resets midnight UTC)
- Input sanitized — known prompt-injection delimiter tokens stripped
- CORS restricted to portfolio domain only
- Claude API key server-side only, never in frontend
- Jailbreak-resistant system prompt (see `app/prompts.py`)
