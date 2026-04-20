# Project Context

## Overview
UnifyRoute is a self-hosted, OpenAI-compatible gateway for routing requests across multiple LLM providers with failover, quota awareness, and a management UI.

## Current Task
Initial project setup completed successfully

## Environment
- Python: 3.12.3
- Node.js: 25.9.0
- Platform: Linux
- Redis: Running (Docker)

## Key Files
- Entry point: `api-gateway/src/api_gateway/main.py`
- Config: `.env`, `pyproject.toml`, `router/routing.yaml`
- Launcher: `launcher/src/launcher/main.py`

## Dependencies
- uv (Python package manager) - installed at ~/.local/bin
- Redis - running via Docker
- SQLite - data/unifyroute.db

## Setup Completed
1. ✅ Installed uv
2. ✅ Created .venv with uv
3. ✅ Installed all Python dependencies
4. ✅ Created .env from sample.env with generated secrets
5. ✅ Ran database migrations
6. ✅ Installed GUI dependencies
7. ✅ Server running at http://localhost:6565
8. ✅ Created admin and API tokens

## API Tokens
- Admin token saved to: `.admin_token`
- API token saved to: `.api_token`

## Next Steps
- Run `./unifyroute wizard` to configure providers
- Run tests with `./run-tests.sh --unit` or `./run-tests.sh --integration`