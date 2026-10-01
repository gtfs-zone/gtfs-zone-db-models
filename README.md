# gtfs-zone-db-models

SQLModel ORM models and Alembic migrations for a GTFS transit feed management system.

## Requirements

- Python 3.13+
- PostgreSQL

## Installation

```bash
uv sync
```

## Database Setup

```bash
DATABASE_URL="postgresql+asyncpg://user:pass@localhost/dbname" alembic upgrade head
```

## Development

```bash
# Lint and format
ruff check . --fix
ruff format .

# Tests (moto stands in for S3; no container needed)
pytest

# Create a new migration after modifying models
DATABASE_URL="..." alembic revision --autogenerate -m "description"

# Commit (conventional commits enforced)
cz commit
```
