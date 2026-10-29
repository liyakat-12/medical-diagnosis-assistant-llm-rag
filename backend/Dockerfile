# Build context: repository root (see render.yaml dockerContext / docker-compose).
# Keep in sync with ./Dockerfile at repository root.
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=backend
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/app/.cache/huggingface
ENV SENTENCE_TRANSFORMERS_HOME=/app/.cache/sentence-transformers
ENV EMBEDDING_MODE=general
ENV EMBEDDING_BACKEND=fastembed
ENV RERANK_ENABLED=false
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV OPENBLAS_NUM_THREADS=1
ENV TOKENIZERS_PARALLELISM=false
ENV MALLOC_ARENA_MAX=2

COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY backend ./backend
COPY knowledge_base ./knowledge_base
COPY scripts ./scripts
COPY evaluation ./evaluation

# Historical Baseline/After/Batch4 JSON and embedding_eval_*.csv are copied above
# and must remain for the Evaluation Dashboard multi-run / embedding charts.
RUN mkdir -p "$HF_HOME" "$SENTENCE_TRANSFORMERS_HOME" evaluation/results \
    && EMBEDDING_BACKEND=fastembed EMBEDDING_MODE=general RERANK_ENABLED=false \
       python scripts/build_index.py general \
    && EMBEDDING_BACKEND=fastembed EMBEDDING_MODE=general RERANK_ENABLED=false \
       python -c "from src.retrieval.retriever import retrieve; hits = retrieve('persistent cough', mode='general'); assert hits, 'general Chroma index is empty after Docker build'" \
    && EMBEDDING_BACKEND=fastembed EMBEDDING_MODE=general RERANK_ENABLED=false \
       python evaluation/evaluate_kb_phase2.py --out evaluation/results/kb_phase2_production.json \
    && python -c "import json; from pathlib import Path; p=Path('evaluation/results/kb_phase2_production.json'); d=json.loads(p.read_text()); assert d.get('per_query'), 'evaluation report missing per_query'; print('eval_recall@4', d.get('recall@4'), 'mrr', d.get('mrr')); root=Path('evaluation/results'); hist=[n for n in ('kb_phase2_baseline.json','kb_phase2_after.json','kb_phase2_batch4.json') if (root/n).exists()]; emb=[n for n in ('embedding_eval_general.csv','embedding_eval_medical.csv','embedding_eval_general_rerank.csv') if (root/n).exists()]; print('packaged_historical', hist); print('packaged_embedding', emb)"

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
