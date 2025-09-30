# Multi-stage Dockerfile for Gong platform

# Build stage
FROM python:3.11-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.11-slim as production

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash gong

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy source code
COPY src/ ./src/
COPY README.md ./

# Change ownership to non-root user
RUN chown -R gong:gong /app

# Switch to non-root user
USER gong

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "src/gong/api/main.py"]

# Development stage
FROM builder as development

# Install development dependencies
RUN uv sync --frozen

# Copy all files for development
COPY . .

# Change ownership
RUN chown -R gong:gong /app

# Switch to non-root user
USER gong

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Default command for development
CMD ["python", "src/gong/api/main.py", "--reload"]