# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:python3.13-alpine AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy


# Install git for potential git-based dependencies
RUN apk add --no-cache git


COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ ./src/
RUN uv sync --frozen --no-dev

# ---

FROM python:3.13-alpine

WORKDIR /app


RUN addgroup -S bridge && adduser -S bridge -G bridge


COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

ENV PATH="/app/.venv/bin:$PATH"


USER bridge


# library: not intended to be run directly

