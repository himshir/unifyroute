# Configuration Reference

Configuration is read from environment variables, typically via `.env`.

## Core Variables

| Variable | Default | Description |
|---|---|---|
| `DB_BACKEND` | `sqlite` | Database backend selector (current default workflow uses SQLite). |
| `SQLITE_PATH` | `data/unifyroute.db` | SQLite database location. |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis URL for cache and coordination. |
| `PORT` | `6565` | Gateway listen port. |
| `HOST` | `localhost` | Gateway bind host. |
| `API_BASE_URL` | `http://localhost:6565` | Public base URL used in callbacks. |

## Security Variables

| Variable | Description |
|---|---|
| `MASTER_PASSWORD` | Master password used by admin operations and setup flows. |
| `VAULT_MASTER_KEY` | Encryption key used by credential vault workflows. |
| `JWT_SECRET` | JWT signing secret for auth/session features. |

## OAuth Variables

| Variable | Description |
|---|---|
| `GOOGLE_OAUTH_CLIENT_ID` | OAuth client ID for Google flows. |
| `GOOGLE_OAUTH_CLIENT_SECRET` | OAuth client secret for Google flows. |

## Routing Config

Routing behavior is configured in `router/routing.yaml`.

Recommended practice:

- Start with conservative tier defaults.
- Keep at least one fallback provider per critical tier.
- Validate aliases used by clients (`lite`, `base`, `thinking`).
