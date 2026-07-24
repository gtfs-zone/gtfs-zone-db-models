# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Lint and format
ruff check . --fix
ruff format .

# Run database migrations
DATABASE_URL="postgresql+asyncpg://user:pass@localhost/dbname" alembic upgrade head

# Generate a new migration (after modifying models)
DATABASE_URL="..." alembic revision --autogenerate -m "description"

# Commit (enforces conventional commits)
cz commit
```

## Rules

- Never add Co-Authored-By trailers to commit messages.

## Architecture

This is a Python 3.13+ library (no web framework) providing SQLModel ORM models and Alembic migrations for a GTFS transit feed management system. The package lives in `src/railroad_club/`.

**Key entities and relationships:**
- `User` — provider-based OAuth identity (provider + provider_subject unique pair, e.g. "dex")
- `Feed` — a GTFS feed owned by a User; has many Drivers, ServiceAlerts, and one optional GtfsStaticFeed
- `Driver` — credentials for accessing a feed (username/password)
- `ServiceAlert` → `InformedEntity` — GTFS-RT service alerts with normalized entity selectors
- `GtfsStaticFeed` → `GtfsStop`, `GtfsRoute`, `GtfsTrip`, `GtfsStopTime` — loaded GTFS static data scoped per feed

**GtfsStopTime rule:** `arrival_time` and `departure_time` must never be null.

**Validation approach:** Pydantic field validators on SQLModel classes plus database-level check constraints (e.g. `ck_informed_entity_has_specifier` requires at least one entity specifier field to be set).

**Migrations:** Alembic with async support via `asyncpg`. The `alembic/env.py` imports all models through `railroad_club.models` to enable autogenerate.

**Tooling:** Ruff (lint + format, line length 88, rules E/F/I/UP/B/SIM), Commitizen (conventional commits, tag format `v$version`), pre-commit hooks enforcing both.
