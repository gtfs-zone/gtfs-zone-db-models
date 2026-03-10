FROM python:3.13-slim
WORKDIR /app
RUN pip install uv
COPY pyproject.toml .
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .
RUN uv pip install --system -e .
CMD ["alembic", "upgrade", "head"]
