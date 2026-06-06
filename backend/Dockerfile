# Multi-stage build for YOLO Assembly Vision Backend
FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps: build tools + cadquery OpenGL/X libs + Blender deps
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    wget \
    xz-utils \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libxi6 \
    libxkbcommon0 \
    libxfixes3 \
    libxrandr2 \
    libxcursor1 \
    libx11-6 \
    && rm -rf /var/lib/apt/lists/*

# Install Blender:
#   x86_64 → official 4.4.0 portable binary
#   arm64  → apt package (Debian trixie ships Blender 3.6+, no official arm64 binary from blender.org)
ENV BLENDER_VERSION=4.4.0
ENV BLENDER_DIR=/opt/blender
RUN ARCH=$(uname -m) && echo "Architecture: $ARCH" && \
    if [ "$ARCH" = "x86_64" ]; then \
        wget -q "https://download.blender.org/release/Blender4.4/blender-${BLENDER_VERSION}-linux-x64.tar.xz" \
            -O /tmp/blender.tar.xz && \
        mkdir -p ${BLENDER_DIR} && \
        tar -xf /tmp/blender.tar.xz -C ${BLENDER_DIR} --strip-components=1 && \
        rm /tmp/blender.tar.xz && \
        ln -s ${BLENDER_DIR}/blender /usr/local/bin/blender; \
    else \
        apt-get update && \
        apt-get install -y blender && \
        rm -rf /var/lib/apt/lists/*; \
    fi

# Create app directory
WORKDIR /app

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install Python dependencies
# cadquery-ocp has no ARM64 Linux wheels; install everything else first,
# then attempt cadquery separately so the build doesn't fail on ARM64.
RUN pip install --upgrade pip && \
    grep -v "^cadquery" requirements.txt > /tmp/requirements-core.txt && \
    pip install -r /tmp/requirements-core.txt && \
    pip install cadquery || echo "cadquery unavailable for this arch — STEP feature recognition disabled"

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p storage/uploads storage/datasets storage/models logs

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
