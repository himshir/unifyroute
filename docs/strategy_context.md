# LLMWay Strategy & Context

## Core Objective
The core of this project is to use the best available model as per the executed routing strategy. 
We iterate through the configured models until all options are exhausted. 
If all models are exhausted, the system **does not return an error**, but rather a graceful message indicating that no model or quota is available.

## Routing Strategy
The key component of the system is the **Routing Strategy**. It must be designed to be highly configurable and intuitive for the user to set up and modify.

## Connecting to Providers (OpenClaw Replication)
The `openclaw` folder contains tested code for connecting to various LLM providers.
**Crucial Rule**: We do not change anything inside the `openclaw` folder as it is copied only for quick reference.
Instead, we extract and replicate the *way* OpenClaw connects to its providers (the HTTP/socket connectivity patterns) and implement those patterns inside the LLMWay core adapters.

## Port Configurations
**Crucial Rule**: The application does not use standard ports. Do not revert ports back to standard ports (like 8000, 3000, etc) when making changes. Always respect the currently configured dynamically bound ports.

## Developer Tooling Rules

### Database Queries
**Crucial Rule**: Before running any raw SQL or DB inspection commands, always check which database is in use:
- Check `.env` for `DATABASE_URL` — if it starts with `sqlite`, use `.venv/bin/python3` with the `sqlalchemy` async session (as shown in the codebase).
- If it is a PostgreSQL URL, use `docker exec` to run `psql` inside the appropriate container, or use `psql` directly.
- **Never** assume `sqlite3` CLI is available — it is not installed in this environment.
- Preferred approach for any DB inspection: use `.venv/bin/python3` with SQLAlchemy models.

### Python Commands
**Crucial Rule**: Always use `.venv/bin/python3` when running Python scripts or one-liners. The system `python`/`python3` is not guaranteed to have project dependencies installed.
```bash
# Correct
.venv/bin/python3 -c "..."
.venv/bin/python3 script.py

# Wrong
python3 -c "..."
python -c "..."
```

### Docker
Docker version **29.2.1** (build a5c7197) is available. Use modern Docker CLI syntax:
- `docker compose` (not `docker-compose`)
- `docker exec <container> <cmd>` for running commands inside containers
