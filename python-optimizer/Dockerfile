# KORA Optimizer Production Dockerfile
# =====================================
# Multi-stage build for minimal image size

# Stage 1: Build dependencies
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Production image
FROM python:3.11-slim as production

WORKDIR /app

# Create non-root user for security
RUN groupadd --gid 1000 kora \
    && useradd --uid 1000 --gid kora --shell /bin/bash --create-home kora

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=kora:kora . .

# Create directories for logs and results
RUN mkdir -p /app/logs /app/results /app/cache \
    && chown -R kora:kora /app

# Switch to non-root user
USER kora

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    KORA_LOG_FORMAT=json \
    KORA_LOG_LEVEL=INFO \
    KORA_CACHE_DIR=/app/cache \
    KORA_RESULTS_DIR=/app/results

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from kora.service import KoraService; print('OK')" || exit 1

# Default command: run the service
ENTRYPOINT ["python", "-m", "kora.service"]
CMD ["--json-logs", "--interval", "15"]
