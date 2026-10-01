# AGENTS.md

Shared Python library: the SQLModel models, Alembic migrations and S3 client
used by rt-api, static-importer and the rt workers. No deployment of its own;
consumers pin it by git tag.

## Commands

```bash
DATABASE_URL="..." alembic revision --autogenerate -m "description"
```

## Architecture

Models are in `src/gtfs_zone_db_models/models/`; `alembic/env.py` imports them
all through `gtfs_zone_db_models.models` so autogenerate sees every table.
Migrations ship in the package and run via the `gtfs-zone-db-models-migrate`
script (rt-api's migrate job), never from the consumers.

- `GtfsStopTime.arrival_time` and `departure_time` are never null.
- Validation is Pydantic field validators plus DB check constraints (e.g.
  `ck_informed_entity_has_specifier`). Add both for a new rule.
- `GtfsUpload` is append-only, one row per uploaded zip, so a bad upload can be
  rolled back. `object_key_for` is the only place the bucket layout
  (`feeds/{feed_id}/{upload_id}.zip`) is written down.
- `object_store.py` is the one S3 client (boto3 against Garage) for rt-api and
  static-importer. It lives here so neither app owns the other's copy.

## Conventions

- **Commits**: Conventional Commits, enforced by the `commit-msg` hook. Setup and
  release are in [CONTRIBUTING.md](CONTRIBUTING.md).
- **Logging**: module loggers are named `log`, never `logger`.
- **Plans**: write plans to `CURRENT_PLAN.md` at the repo root as a
  checklist (`- [ ]`), ticked off as work lands. It is neither tracked nor
  gitignored: never stage or commit it.
