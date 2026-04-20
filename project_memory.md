# Project Memory

## Session History

### Session Date: 2026-04-20
**Task**: Initial project setup
**Outcome**: Successfully set up UnifyRoute project from scratch
**Key Decisions**: 
- Installed uv package manager to satisfy prerequisites
- Generated secrets manually and added to .env (MASTER_PASSWORD, VAULT_MASTER_KEY, JWT_SECRET)
- Created API tokens directly in SQLite database (bypassed interactive CLI which doesn't work in non-TTY)

**Changes**: 
- Created `AGENTS.md` - developer guide
- Created `project_context.md` - project overview
- Created `project_memory.md` - session history
- Created `.env` from sample.env
- Created `.venv/` virtual environment
- Created `data/unifyroute.db` with schema
- Created `.admin_token` and `.api_token` files

**Next Steps**: 
- Run wizard to add providers
- Run test suite to verify everything works

## Decisions & Patterns

- Always use `.venv/bin/activate` for Python commands
- Use `uv run` or activate venv before running Python commands
- Redis runs via Docker Compose for the project
- GUI is built automatically when starting the server if not present

## Open Questions

- Docker Compose v2 not available (optional)