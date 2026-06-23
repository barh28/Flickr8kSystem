# Build context is the `backend/` directory so that shared_libraries/ can be
# copied into the image alongside the service.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app:/app/user_manager

WORKDIR /app

COPY user_manager/requirements.txt /app/user_manager/requirements.txt
RUN pip install --no-cache-dir -r /app/user_manager/requirements.txt

COPY shared_libraries/ /app/shared_libraries/
COPY user_manager/ /app/user_manager/

WORKDIR /app/user_manager
EXPOSE 8000
CMD ["python", "main.py"]
