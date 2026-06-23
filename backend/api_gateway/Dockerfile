# Build context is the `backend/` directory so that shared_libraries/ can be
# copied into the image alongside the service.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app:/app/api_gateway

WORKDIR /app

COPY api_gateway/requirements.txt /app/api_gateway/requirements.txt
RUN pip install --no-cache-dir -r /app/api_gateway/requirements.txt

COPY shared_libraries/ /app/shared_libraries/
COPY api_gateway/ /app/api_gateway/

WORKDIR /app/api_gateway
EXPOSE 8080
CMD ["python", "main.py"]
