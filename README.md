# UnifyRoute — LLM API Gateway

**UnifyRoute** is a self-hosted, OpenAI-compatible API gateway that aggregates multiple LLM provider accounts, routes requests intelligently across tiers, tracks costs in real time, and provides a full management dashboard.

> Point any OpenAI-compatible tool at `http://localhost:<app_port>` and UnifyRoute handles the rest — load balancing, failover, quota tracking, and OAuth credential management.

---

## Features

| Category | Details |
|----------|---------|
| **Routing** | Tier-based (lite / base / thinking), automatic failover on 429/503/timeout, fallback to brain models |
| **Providers** | OpenAI, Anthropic, Google (Gemini), Groq, Mistral, Cohere, Together, OpenRouter, HuggingFace, and 10+ more |
| **Auth** | OAuth2 (Google Antigravity / custom providers) + API key credentials with session persistence |
| **Monitoring** | Real-time token usage charts, per-provider cost tracking, audit logs with CSV export |
| **Dashboard** | React SPA — interactive setup wizard, providers, credentials, models, routing config, logs, quota gauges |
| **Deployment** | Single-process dev mode, Docker Compose full stack, or systemd service |

---

## Architecture

```
Client (curl / OpenClaw / any OpenAI-SDK)
         │
         ▼ POST /api/v1/chat/completions
┌────────────────────────────────┐
│        API Gateway :8000       │  ← Auth, routing, logging
│   FastAPI + litellm + Redis    │
└────────────────────────────────┘
         │
    ┌────┴────┐
    │ Router  │  ← Tier config (routing.yaml), candidate ranking
    └────┬────┘
         │  tries candidates in order, marks failures in Redis
         │  (fails over to brain models if all candidates are exhausted)
   ┌─────▼──────┐   ┌───────────────┐   ┌──────────────┐
   │  Provider 1│   │  Provider 2   │   │  Provider N  │
   │  (OpenAI)  │   │  (Anthropic)  │   │  (Groq…)     │
   └────────────┘   └───────────────┘   └──────────────┘

Background Services
  credential-vault :8001  → OAuth token refresh (every 10 min)
  quota-poller            → Quota polling + model sync (every 5 min)
```

---

## Project Structure

```
unifyroute/
├── api-gateway/          FastAPI app — proxy, admin CRUD, OAuth
├── credential-vault/     Internal service — decrypt credentials, refresh tokens
├── quota-poller/         Background scheduler — quota polling, model sync
├── router/               Routing logic, routing.yaml, Redis integration
├── shared/               SQLAlchemy models, Pydantic schemas, DB utils, encryption
├── gui/                  React + Vite + shadcn/ui dashboard
├── migrations/           Alembic database migrations
├── scripts/              Setup, key management, cleanup scripts
├── launcher/             Unified launcher (combines services)
├── docker-compose.yml    Production full-stack
├── docker-compose.override.yml  Dev hot-reload
└── sample.env            Environment variable template
```

---

## Quick Start

```bash
# 1. Clone and enter project
git clone <repo-url> unifyroute && cd unifyroute

# 2. Copy and configure environment
cp sample.env .env
# Edit .env — set SQLITE_PATH, VAULT_MASTER_KEY (see Installation Guide)

# 3. Run setup (installs deps, migrates DB, creates admin key)
./unifyroute setup

# 4. Run the interactive setup wizard to configure providers and brain
./unifyroute wizard

# 5. Start the gateway
./unifyroute start
```

Windows note (Git Bash): if `./unifyroute ...` reports a Python error, verify `python` or `py` works in your shell (`python --version` or `py --version`).
The launcher probes `python`, then `python3`, then `py -3` automatically to avoid broken `python3` app aliases.

The dashboard is at **http://localhost:<app_port>** — log in with the `sk-...` key from step 3. (You can also access the setup wizard at **/wizard**).

Send requests like any OpenAI client:

```bash
curl http://localhost:<app_port>/api/v1/chat/completions \
  -H "Authorization: Bearer sk-your-gateway-key" \
  -H "Content-Type: application/json" \
  -d '{"model": "base", "messages": [{"role": "user", "content": "Hello!"}]}'
```

---

## API Compatibility

UnifyRoute exposes a standard OpenAI-compatible API:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/chat/completions` | POST | Chat completions (streaming supported) |
| `/api/v1/completions` | POST | Text completions |
| `/api/v1/models` | GET | List available model aliases |

Use any OpenAI SDK by setting `OPENAI_BASE_URL=http://localhost:<app_port>/api/v1` and `UNIFYROUTE_API_KEY=sk-your-gateway-key`.

---

## Model Tiers

Configure in `router/routing.yaml`:

| Tier | Default Strategy | Use Case |
|------|-----------------|----------|
| `lite` | cheapest_available | Fast, cheap completions |
| `base` | cheapest_available | General purpose |
| `thinking` | highest_quota | Complex reasoning |

---

## Documentation

| Document | Description |
|----------|-------------|
| [Installation Guide](docs/installation.md) | Prerequisites, setup steps, environment config |
| [Usage & Commands Reference](docs/usage.md) | All CLI commands, API examples, admin tasks |
| [Architecture](docs/llm-gateway-architecture.md) | Full system design spec |
| [Progress & TODO](docs/progress-and-todo.md) | Implementation status and remaining work |

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SQLITE_PATH` | — | `data/unifyroute.db` | SQLite database file path |
| `VAULT_MASTER_KEY` | ✅ | — | 32-byte Fernet key for credential encryption |
| `REDIS_URL` | ✅ | `redis://localhost:6379/0` | Redis connection |
| `API_BASE_URL` | — | `http://localhost:<app_port>` | Public base URL (for OAuth callbacks) |
| `PORT` | — | `8000` | Listening port |
| `HOST` | — | `0.0.0.0` | Bind address |
| `ALLOWED_ORIGINS` | — | `http://localhost:5173` | CORS origins |
| `JWT_SECRET` | — | — | JWT signing secret (if using JWT auth) |
| `QUOTA_POLL_INTERVAL_SECONDS` | — | `300` | Quota poll frequency |

---

## License

MIT License © UnifyRoute Contributors
