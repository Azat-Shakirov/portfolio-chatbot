#!/bin/bash
set -e

# Run ingestion on first deploy (when volume is empty)
if [ ! -f "/app/chroma_db/chroma.sqlite3" ]; then
    echo "ChromaDB not found — running ingestion..."
    python app/ingest.py
    echo "Ingestion complete."
else
    echo "ChromaDB found — skipping ingestion."
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
