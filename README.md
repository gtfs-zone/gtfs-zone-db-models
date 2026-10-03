# gtfs-zone-db-models

[![CI](https://img.shields.io/github/actions/workflow/status/gtfs-zone/gtfs-zone-db-models/check.yml?branch=main&label=CI)](https://github.com/gtfs-zone/gtfs-zone-db-models/actions/workflows/check.yml?query=branch%3Amain) [![License: AGPL-3.0-or-later](https://img.shields.io/badge/license-AGPL--3.0--or--later-blue)](LICENSE.txt) [![Latest tag](https://img.shields.io/github/v/tag/gtfs-zone/gtfs-zone-db-models?sort=semver)](https://github.com/gtfs-zone/gtfs-zone-db-models/tags) [![Python](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fgtfs-zone%2Fgtfs-zone-db-models%2Fmain%2Fpyproject.toml)](pyproject.toml)

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
