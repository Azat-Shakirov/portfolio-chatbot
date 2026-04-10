FROM python:3.11-slim

WORKDIR /app

# Install deps first — Docker caches this layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model during build
# (~90 MB, avoids cold-start delay on first request)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy application code and data
COPY app/ ./app/
COPY data/ ./data/
COPY start.sh .

EXPOSE 8000

CMD ["./start.sh"]
