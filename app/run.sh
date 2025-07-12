# We should already make the migration files locally before deploying
make alembic-migrate
uv run uvicorn app.server.main:app --host 0.0.0.0 --reload
