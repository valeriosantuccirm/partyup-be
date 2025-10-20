FROM python:3.13.2-slim

ENV LANG=C.UTF-8 \
  LC_ALL=C.UTF-8 \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONFAULTHANDLER=1

WORKDIR /app

# Install build dependencies
RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  curl \
  gcc \
  python3-dev \
  libssl-dev \
  libpq-dev \
  musl-dev && \
  rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -L https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-unknown-linux-musl.tar.gz \
  -o uv.tar.gz && \
  tar -xzf uv.tar.gz && \
  mv uv-*/uv /usr/local/bin/uv && \
  chmod +x /usr/local/bin/uv && \
  rm -rf uv.tar.gz uv-*

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install Python deps
RUN uv sync --no-dev

# Copy app code
COPY . .
