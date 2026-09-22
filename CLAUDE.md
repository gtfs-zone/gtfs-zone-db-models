# CLAUDE.md

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

## Architecture

This is a Python 3.13+ library (no web framework) providing SQLModel ORM models and Alembic migrations for a GTFS transit feed management system. The package lives in `src/railroad_club/`.

**Key entities and relationships:**
- `User`: provider-based OAuth identity (provider + provider_subject unique pair, e.g. "dex")
- `Feed`: a GTFS feed owned by a User; has many Drivers, ServiceAlerts, and one optional GtfsStaticFeed
- `Driver`: credentials for accessing a feed (username/password)
- `ServiceAlert` → `InformedEntity`: GTFS-RT service alerts with normalized entity selectors
- `GtfsStaticFeed` → `GtfsStop`, `GtfsRoute`, `GtfsTrip`, `GtfsStopTime`: loaded GTFS static data scoped per feed

**GtfsStopTime rule:** `arrival_time` and `departure_time` must never be null.

**The upload store seam:** `GtfsUpload` (`models/gtfs_upload.py`) is one row
per uploaded GTFS zip, append-only so a bad upload can be rolled back to a
prior one. `object_key_for(feed_id, upload_id)` is the only place the bucket
layout is written down (`feeds/{feed_id}/{upload_id}.zip`); `feed_object_prefix`
is what a feed delete removes wholesale. `object_store.py`'s `ObjectStore` /
`AsyncObjectStore` are the shared S3-compatible client (boto3 against Garage's
S3 API) that both cafe-car and schedule-foamer use to read and write those
objects — it lives here, beside the models the objects belong to, so neither
app owns the other's copy.

**Validation approach:** Pydantic field validators on SQLModel classes plus database-level check constraints (e.g. `ck_informed_entity_has_specifier` requires at least one entity specifier field to be set).

**Migrations:** Alembic with async support via `asyncpg`. The `alembic/env.py` imports all models through `railroad_club.models` to enable autogenerate.

**Tooling:** Ruff (lint, line length 88, rules E/F/I/UP/B/SIM/ANN/TC/RUF), Commitizen (conventional commits, tag format `v$version`), pre-commit hooks enforcing both.

## Rules

- Module loggers are named `log`, never `logger`: `log = logging.getLogger(__name__)`
