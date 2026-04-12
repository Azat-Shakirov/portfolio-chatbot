#!/bin/bash
set -e

HASH_FILE="/app/chroma_db/.about_me_hash"
ABOUT_ME="/app/data/about_me.txt"
CHROMA_DB="/app/chroma_db/chroma.sqlite3"

CURRENT_HASH=$(md5sum "$ABOUT_ME" | awk '{print $1}')
STORED_HASH=""
if [ -f "$HASH_FILE" ]; then
    STORED_HASH=$(cat "$HASH_FILE")
fi

if [ ! -f "$CHROMA_DB" ] || [ "$CURRENT_HASH" != "$STORED_HASH" ]; then
    echo "about_me.txt changed or ChromaDB missing — running ingestion..."
    python app/ingest.py
    echo "$CURRENT_HASH" > "$HASH_FILE"
    echo "Ingestion complete."
else
    echo "ChromaDB up to date — skipping ingestion."
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
