# UnifyRoute Developer Guide

## Session Files

At the start of each session, read these files:
- `AGENTS.md` - This guide
- `project_context.md` - Project overview and current task context
- `project_memory.md` - Previous conversation history and decisions

At the end of each run, update both `project_context.md` and `project_memory.md` with:
- Current task progress and outcome
- Key decisions made
- Any code changes or findings worth remembering
- Next steps if applicable

## Quick Commands

```bash
# Setup (first time)
./unifyroute setup

# Start the application
./unifyroute start

# Run tests
./run-tests.sh --unit          # No server needed (~5s)
./run-tests.sh --integration    # Requires running gateway
./run-tests.sh                  # All tests

# GUI development
cd gui && npm run dev
cd gui && npm run build

# CLI
./unifyroute wizard             # Interactive setup wizard
./unifyroute create token api   # Create API token
./unifyroute create token admin # Create admin token

# Python - always use .venv virtual environment
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```

## Architecture

**Monorepo** using `uv` workspace with packages:
- `api-gateway/` - FastAPI application (entrypoint: `api-gateway/src/api_gateway/main.py`)
- `router/` - Routing engine with litellm
- `shared/` - DB models, schemas, security
- `credential-vault/` - OAuth/secret storage
- `quota-poller/` - Quota sync workers
- `launcher/` - Unified app launcher
- `brain/` - AI brain module
- `selfheal/` - Proactive failover

## Prerequisites

- Python 3.11+
- Node.js 18+, npm 9+
- `uv` (Python package manager)
- Redis (for caching)
- SQLite (default: `data/unifyroute.db`)

Run prerequisite check: `./scripts/check_prerequisites.sh`

## Testing

Tests are in `tests/` directory. **Integration tests require a running gateway**.

Token setup for tests:
1. Start gateway: `./unifyroute start`
2. Create tokens: `./unifyroute create token admin && ./unifyroute create token api`
   - Tokens are saved to `.admin_token` and `.api_token` files

Run specific test: `uv run pytest tests/test_router_core.py`

## Key Config Files

- `.env` - Environment variables (copy from `sample.env`)
- `pyproject.toml` - Workspace config at root
- `router/routing.yaml` - Routing tiers configuration

## GUI

React + Vite + TypeScript + TailwindCSS. Located in `gui/`:
- Dev server: `http://localhost:5173`
- Build: `npm run build`
- Lint: `npm run lint`

## Existing Agent Instructions

See `.agents/workflows/run-tests.md` for detailed testing workflow.
