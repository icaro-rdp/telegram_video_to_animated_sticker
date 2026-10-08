# ------------------------------------------------------------------------------
# Production Dockerfile for Telegram Video to Animated Sticker / Emoji Studio
# Compatible with Render.com, Cloud Run, and any Docker PaaS
# ------------------------------------------------------------------------------

FROM node:20-bookworm-slim

# Install system dependencies:
# - ffmpeg: provides ffprobe and libvpx-vp9 for WebM encoding
# - curl & ca-certificates: required for network operations and secure downloads
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/

# Install uv for fast Python dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Install standalone Python 3.12 via uv
ENV UV_PYTHON_INSTALL_DIR=/opt/python
ENV UV_PYTHON=3.12
RUN uv python install 3.12

WORKDIR /app

# 1. Install Python backend package and dependencies
COPY pyproject.toml README.md uv.lock* ./
COPY tg_sticker/ ./tg_sticker/
RUN uv sync --frozen || uv sync

# 2. Install Frontend Node dependencies (cached layer)
COPY frontend/package.json frontend/package-lock.json ./frontend/
RUN cd frontend && npm ci

# 3. Build Next.js application
COPY frontend/ ./frontend/
RUN cd frontend && npm run build

# 4. Ensure runtime input/output folders exist
RUN mkdir -p /app/input_videos /app/output_stickers

# 5. Environment configuration
ENV NODE_ENV=production
ENV PORT=3000

EXPOSE 3000

# 6. Start Next.js server, binding to 0.0.0.0 and dynamically using $PORT (required by Render)
CMD ["sh", "-c", "npm run start --prefix frontend -- -p ${PORT:-3000} -H 0.0.0.0"]
