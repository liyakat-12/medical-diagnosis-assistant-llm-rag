# Build context: repository root (see render.yaml dockerContext / docker-compose).
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=backend
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Cache roots used by the installed libraries (no secrets):
# - SentenceTransformer reads SENTENCE_TRANSFORMERS_HOME as cache_folder
# - CrossEncoder / Transformers / huggingface_hub use HF_HOME (hub under $HF_HOME/hub)
ENV HF_HOME=/app/.cache/huggingface
ENV SENTENCE_TRANSFORMERS_HOME=/app/.cache/sentence-transformers
ENV EMBEDDING_MODE=general

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY knowledge_base ./knowledge_base
COPY scripts ./scripts

# Create cache dirs, then bake retrieval into the image (no Mongo/Groq/JWT):
# 1) general Chroma index (loads MiniLM via SentenceTransformer into SENTENCE_TRANSFORMERS_HOME)
# 2) assert the index is queryable
# 3) preload cross-encoder via src.retrieval.reranker._load_model into HF_HOME hub cache
RUN mkdir -p "$HF_HOME" "$SENTENCE_TRANSFORMERS_HOME" \
    && python scripts/build_index.py general \
    && python -c "from src.retrieval.retriever import retrieve; hits = retrieve('persistent cough', mode='general'); assert hits, 'general Chroma index is empty after Docker build'" \
    && python -c "from src.retrieval.reranker import _load_model; _load_model(); print('reranker cached under HF_HOME')"

EXPOSE 8000
# Render sets PORT; default 8000 matches render.yaml.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
