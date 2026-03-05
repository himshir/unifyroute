# Development Guide

## Local Development

1. Install dependencies:

```bash
./unifyroute setup
```

2. Start app:

```bash
./unifyroute start
```

3. Run tests:

```bash
./run-tests.sh
# or
./run-tests.sh --unit
./run-tests.sh --integration
```

## Project Areas

- `api-gateway/`: API endpoints and orchestration.
- `router/`: provider selection and fallback logic.
- `shared/`: DB models, schemas, and security utilities.
- `gui/`: React frontend.

## Database Migrations

Migrations live under `migrations/` and are applied during setup.

## Code Style

- Keep changes scoped and testable.
- Add/adjust tests with behavior changes.
- Avoid hardcoded secrets and provider credentials.

## Pull Request Checklist

- Tests pass locally.
- Docs updated for behavior/config changes.
- No secrets in commits.
- Breaking changes are clearly documented.
