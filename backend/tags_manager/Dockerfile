# Build context is the `backend/` directory so that shared_libraries/ can be
# copied into the image alongside the service.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app:/app/tags_manager

WORKDIR /app

COPY tags_manager/requirements.txt /app/tags_manager/requirements.txt
RUN pip install --no-cache-dir -r /app/tags_manager/requirements.txt

COPY shared_libraries/ /app/shared_libraries/
COPY tags_manager/ /app/tags_manager/

WORKDIR /app/tags_manager
EXPOSE 8000
CMD ["python", "main.py"]
