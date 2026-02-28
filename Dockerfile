# Stock P&L Manager - Dockerfile
# Multi-stage build for optimized production image

# Stage 1: Base image with Python
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Dependencies installation
FROM base as dependencies

WORKDIR /tmp

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install --user -r requirements.txt

# Stage 3: Production image
FROM base as production

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder stage
COPY --from=dependencies /root/.local /root/.local

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data/uploads logs

# Update PATH to include user-installed packages
ENV PATH=/root/.local/bin:$PATH

# Expose port (Railway assigns PORT dynamically)
EXPOSE 8000

# Default command (overridden by railway.toml startCommand in production)
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8000", "--timeout", "120", "app:create_app('production')"]
