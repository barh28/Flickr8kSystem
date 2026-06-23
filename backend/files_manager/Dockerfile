# Build context is the `backend/` directory so that shared_libraries/ can be
# copied into the image alongside the service.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app:/app/files_manager

WORKDIR /app

COPY files_manager/requirements.txt /app/files_manager/requirements.txt
RUN pip install --no-cache-dir -r /app/files_manager/requirements.txt

COPY shared_libraries/ /app/shared_libraries/
COPY files_manager/ /app/files_manager/

WORKDIR /app/files_manager
EXPOSE 8000
CMD ["python", "main.py"]
