# Build context is the `backend/` directory so that shared_libraries/ and the
# files service code can be copied in (the loader reuses files' data layer).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app:/app/files_manager

WORKDIR /app

COPY init_loader/requirements.txt /app/init_loader/requirements.txt
RUN pip install --no-cache-dir -r /app/init_loader/requirements.txt

COPY shared_libraries/ /app/shared_libraries/
COPY files_manager/ /app/files_manager/
COPY init_loader/ /app/init_loader/

WORKDIR /app/init_loader
CMD ["python", "ingest.py"]
