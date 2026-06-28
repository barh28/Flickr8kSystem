# Build context is the `backend/` directory so shared_libraries/ can be copied
# in alongside the service (same convention as the other services).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app:/app/clip_search

WORKDIR /app

COPY clip_search/requirements.txt /app/clip_search/requirements.txt
RUN pip install --no-cache-dir -r /app/clip_search/requirements.txt

# Bake the CLIP model weights into the image at build time so the running
# container never needs network access (satisfies the "runtime is offline"
# constraint). Build-time internet is required for this one step.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('clip-ViT-B-32')"

# From here on, force offline so the library only ever uses the baked weights.
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

COPY shared_libraries/ /app/shared_libraries/
COPY clip_search/ /app/clip_search/

WORKDIR /app/clip_search
EXPOSE 8000
CMD ["python", "main.py"]
