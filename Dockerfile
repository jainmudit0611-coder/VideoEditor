# ==============================================================================
# Brand Guardian AI — Backend Production Container Image (Phase 7)
# ==============================================================================
# Shared base image supporting:
#   1. FastAPI API server (uvicorn)
#   2. Asynchronous background task worker
#   3. Alembic database migration runner
# ==============================================================================

FROM python:3.12-slim

# Set environment flags for optimal container execution
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies required for OpenCV, FFmpeg, and healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create a dedicated non-root application user for production security
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

# Upgrade pip and install production Python packages
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    fastapi \
    uvicorn \
    sqlalchemy \
    psycopg2-binary \
    redis \
    alembic \
    pydantic \
    pydantic-settings \
    bcrypt \
    pyjwt \
    langchain \
    langchain-community \
    langchain-openai \
    langgraph \
    opencv-python \
    yt-dlp \
    python-dotenv \
    azure-identity \
    azure-search-documents \
    requests

# Copy application source code and migration scripts
COPY backend/ ./backend/
COPY alembic.ini .
COPY alembic/ ./alembic/
COPY main.py .

# Ensure directory permissions are granted to non-root appuser
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose FastAPI service port
EXPOSE 8000

# Default command: run FastAPI production ASGI server
CMD ["uvicorn", "backend.src.api.server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
