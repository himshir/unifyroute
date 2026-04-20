# UnifyRoute — Project Plan

> One self-hosted gateway that sits in front of every LLM provider, routes each request to the best available provider/model based on live credit and user-defined rules, keeps full chat history and conversation context, and ships enterprise-grade logging for when things go wrong.

Generated: 2026-04-20. Companion: `TASKS.md` (issue-ready breakdown per phase).

---

## 1. Vision (Target State)

UnifyRoute becomes the only LLM provider your apps ever talk to. Apps point at UnifyRoute's OpenAI-compatible API and UnifyRoute handles:

1. **Provider & model catalog** — every major LLM provider pluggable by API key or OAuth, with a live model registry.
2. **Continuous credit polling** — every provider credential's remaining credit (tokens and, where available, USD) is refreshed on a short interval and cached in Redis.
3. **Credit-aware, rule-driven routing** — the "brain" evaluates user-defined rules on each request to pick the provider/model, with live credit, cost, latency, and health as inputs.
4. **Full chat history + server-side context** — every request that carries a `session_id` is persisted; the gateway maintains conversation context so clients can send only the new turn.
5. **Enterprise-grade logging** — correlation IDs across services, structured system events, request/response audit, exportable and webhookable.

UnifyRoute already implements a large portion of this surface area. This plan identifies what's in place, what's partial, and what's missing — and proposes concrete schema, API, and module changes to close each gap.

---

## 2. Current Architecture (As-Built)

### 2.1 Monorepo layout

```
api-gateway/     FastAPI app; mounts /v1 (OpenAI-compat) and /admin (management)
router/          Routing engine (core.py, quota.py); routing.yaml
brain/           Internal provider selector (ranker/selector/tester/importer/health)
quota-poller/    Scheduled worker: polls credit, writes Redis + QuotaSnapshot
selfheal/        Incident tracking, adaptive cooldown, health prober, circuit breaker
credential-vault/ AES-256-GCM secret storage + OAuth refresh loop
launcher/        Unified entry point mounting all sub-apps and scheduler
shared/          SQLAlchemy models, Pydantic schemas, security helpers
gui/             React + Vite + TS dashboard (14 pages)
migrations/      Alembic migrations (001_full_schema + systemevent)
```

### 2.2 Persisted state (SQLAlchemy models in `shared/src/shared/models.py`)

| Model | Purpose | Key fields |
|---|---|---|
| `Provider` | Registered LLM provider | name, display_name, auth_type (api_key\|oauth2), base_url, oauth_meta |
| `Credential` | API key or OAuth credential for a provider | provider_id, secret_enc+iv (AES-256-GCM), status, expires_at, oauth_meta |
| `ProviderModel` | Per-provider model entry | provider_id, model_id, tier (lite\|base\|thinking), context_window, input/output_cost_per_1k, supports_streaming, supports_functions |
| `QuotaSnapshot` | Historical credit/quota snapshot | credential_id, model_id, tokens_remaining, requests_remaining, polled_at |
| `GatewayKey` | Client-facing API key | key_hash, scopes (json), rate_limit_rpm |
| `RequestLog` | Per-request audit trail | client_key_id, credential_id, model_alias, actual_model, prompt_tokens, completion_tokens, cost_usd, latency_ms, status, prompt_json, response_text |
| `BrainConfig` | Internal LLM selection | provider_id, credential_id, model_id, priority |
| `ChatSession` | Admin playground session | topic, created_at |
| `ChatMessage` | Message within ChatSession | session_id, role, content |
| `RoutingConfig` | YAML blob for tiered routing | yaml_content |
| `SystemEvent` | Structured audit events | timestamp, level, component, event_type, message, details (json) |

### 2.3 Routing (`router/src/router/core.py` + `router/routing.yaml`)

Tiered config with three selection strategies:

- `cheapest_available` — sort (cost asc, quota desc)
- `highest_quota` — sort (quota desc, cost asc)
- `brain_optimized` — composite score using the brain ranker

Four tiers ship today: `auto`, `lite`, `base`, `thinking`. The `auto` tier applies hardcoded task-type heuristics. Direct model IDs are supported via passthrough (but *do not* respect `min_quota_remaining`).

Candidates are filtered by: enabled, not currently in Redis `failed:{cred}:{model}` cooldown, above optional `min_quota_remaining`. Quota is read from Redis (`quota:{cred}:{model}`, TTL 600s).

### 2.4 Credit polling (`quota-poller/src/quota_poller/main.py`)

Three scheduled jobs:

- `poll_quotas()` every `QUOTA_POLL_INTERVAL_SECONDS` (default 300s)
- `sync_models_job()` every 6h
- `collect_usage_job()` every 24h

Per-credential, per-model: calls `adapter.get_quota(credential)`, writes Redis `quota:{cred}:{model}` (TTL 600s) and inserts a `QuotaSnapshot` row. On adapter error, falls back to a static `tokens=10000, requests=None` and logs a `quota_fetch_error` SystemEvent.

Anthropic is the only adapter that currently parses real-time remaining tokens from rate-limit response headers; most adapters either hit a provider quota endpoint or return the fallback.

### 2.5 Self-heal (`selfheal/src/selfheal/`)

- `adaptive_cooldown.py` — exponential TTL per `{cred}:{model}`: 60 → 120 → 240 → 480 → 960 → 1800s.
- `incident_tracker.py` — Redis sorted set `incidents:{cred}:{model}` (1h sliding window); opens `circuit:{cred}:{model}` for 5m at 10 failures.
- `health_prober.py` — every 2 minutes, probes each enabled credential+model; on recovery, clears `failed:`, cooldown count, and circuit.

Circuit-open state is **not** currently consulted by the router directly; recovery logic relies on health_prober to clear the `failed:` key.

### 2.6 Credential vault (`credential-vault/src/credential_vault/main.py`)

- AES-256-GCM with a 96-bit random IV per secret; master key in `VAULT_MASTER_KEY`.
- OAuth refresh loop every 10 minutes for credentials expiring within 15 minutes.
- Internal-only `/internal/decrypt/{credential_id}` endpoint.
- **No master-key rotation path, no audit log of decrypt calls.**

### 2.7 API surface (`api-gateway`)

**OpenAI-compatible:** `POST /v1/chat/completions`, `POST /v1/completions`, `GET /v1/models` (no embeddings, images, audio, files, or batches yet).

**Admin:** providers, credentials, models, keys, routing YAML, logs, system-logs, usage, usage/details, logs/timeline, logs/stats, wizard, oauth flows, brain (status/assign/import/test/ranking/select), chat/sessions.

**Auth:** Bearer `sk-…` tokens (SHA256 hashed in `gateway_keys`) for /v1; JWT cookie or admin token for /admin.

### 2.8 GUI (`gui/src`)

14 functional pages including Dashboard, Chat Playground, Providers, Credentials, Models, Model Management, Routing Strategy, Routing Config (raw YAML), Quota, Logs, Brain, Setup Wizard, Settings, Login. Central API client at `gui/src/lib/api.ts` with SWR hooks.

---

## 3. Gap Analysis — Stated Goal vs. Today

Legend: ✅ Present / 🟡 Partial / ❌ Missing.

### 3.1 Connect to any LLM provider

- ✅ 20+ provider adapters (OpenAI, Anthropic, Google, Groq, Mistral, Cohere, DeepSeek, Cerebras, xAI, Fireworks, Together, OpenRouter, Perplexity, Unify, HuggingFace, Ollama, NVIDIA, vLLM, LiteLLM, Bedrock, GitHub Copilot).
- ✅ OAuth flow for Google Antigravity / generic OAuth2 providers.
- 🟡 No "generic OpenAI-compatible" runtime registration path for bring-your-own providers via the GUI (user must code an adapter). A generic adapter + GUI form would let users register any OpenAI-compatible endpoint without a PR.

### 3.2 Catalog of all models

- ✅ `ProviderModel` table + static seed catalog + live `/v1/models` sync per provider.
- ✅ `/v1/models` endpoint.
- 🟡 No "alias" table for user-defined model names (e.g. `my-cheap-coder`) mapping to provider+model with rules attached. Today aliases are embedded in the routing YAML tiers.

### 3.3 Use any API key

- ✅ `Credential` table with AES-256-GCM, many-per-provider allowed.
- ✅ Admin CRUD + verify endpoint.
- 🟡 No master-key rotation, no credential access audit, no soft delete / purge policy.

### 3.4 Constantly fetch available credit

- 🟡 Tokens-remaining polling exists per credential+model on a 5-min schedule.
- ❌ No **USD balance** polling (e.g. OpenAI `/dashboard/billing/credit_grants`, Anthropic workspace spend, Google Cloud billing). The user said "API credit available" — for most providers the meaningful unit is USD, not tokens.
- 🟡 Fallback of 10,000 tokens when adapters can't report real quota is indistinguishable from a real low-quota credential. No explicit "unknown" state.
- ❌ No per-provider polling interval override and no adaptive polling (poll faster as a key gets close to exhaustion).
- ❌ No per-GatewayKey budget (so one client can't burn the whole account).

### 3.5 Route based on available credit (+ cost, model)

- 🟡 `min_quota_remaining` enforced on tier routes; candidate ranking uses token quota.
- ❌ Direct model IDs bypass `min_quota_remaining`.
- ❌ No USD-aware routing (e.g. "stop using this provider if balance < $1"), no per-model cost caps, no daily spend budgets.
- ❌ Strategy vocabulary limited to 3 presets.

### 3.6 Brain that decides based on user-defined rules

- 🟡 A module called "brain" exists, but it selects providers for **internal** system tasks using a health/quota/priority/latency score. It is **not** a rules engine for user routing.
- ❌ No rule DSL, no conditional logic, no predicate evaluator, no per-request rule matching, no rule priority, no per-key / per-tenant rules.
- ❌ `brain_optimized` strategy name exists in router but brain ranker isn't wired to external request flows.

This is the single largest missing piece relative to the stated vision.

### 3.7 Enterprise logging

- ✅ `SystemEvent` table, indexed by timestamp/level/component; `RequestLog` for per-request audit.
- ✅ GUI Logs page with filtering.
- 🟡 No **correlation id** linking a `RequestLog` row to the `SystemEvent` rows emitted while handling that request. Hard to trace "what happened with request X".
- ❌ No external sinks (syslog, ELK, Loki, Datadog, OpenTelemetry) — enterprise deployments will want this.
- ❌ No webhook/Slack/email alerting on error-rate or low-credit thresholds.
- ❌ No log export / retention UI; prune job deletes logs older than 90 days unconditionally.
- ❌ No per-environment log level control at runtime.

### 3.8 History of all chats

- 🟡 `ChatSession` + `ChatMessage` exist but are scoped to the admin playground (`/admin/chat/*`).
- ❌ `/v1/chat/completions` does **not** persist client-origin chats. Any real external app using the gateway has no history.
- ❌ No association from `ChatSession` to the `GatewayKey` that created it — so no per-tenant / per-user history.
- ❌ No full-text search, tagging, or PII redaction of stored chats.

### 3.9 Keep the context of all chat

- ❌ No server-side conversation context. Clients must resend every message each turn.
- ❌ No context window management, no summarization / truncation, no prefix cache.
- ❌ No "send only the new turn and let UnifyRoute assemble the history" mode.

### 3.10 One solution for all AI-related requirements

- 🟡 Chat + completions + models done.
- ❌ No `/v1/embeddings`, `/v1/images`, `/v1/audio`, `/v1/files`, `/v1/batches`. A true "one solution" gateway should at least cover embeddings (very widely used) and images.
- ❌ No native tool-use passthrough / agent loop orchestration.

---

## 4. Concrete Proposals

Each proposal is sized so it can be implemented incrementally without breaking the current product. Where a proposal touches the DB, use a new Alembic migration (never edit `001_full_schema`).

### 4.1 Rules-engine-powered Brain (v2)

Replace the current single-purpose brain with a user-facing rule pipeline. The existing brain module stays (renamed conceptually to `brain.system_selector`) and runs as one rule among many.

#### 4.1.1 New tables

```sql
-- A user-defined routing rule
CREATE TABLE routing_rules (
    id            UUID PRIMARY KEY,
    name          TEXT NOT NULL,
    description   TEXT,
    priority      INTEGER NOT NULL DEFAULT 100,  -- lower runs first
    enabled       BOOLEAN NOT NULL DEFAULT TRUE,
    match         JSONB NOT NULL,                -- predicate tree (see 4.1.3)
    action        JSONB NOT NULL,                -- action object (see 4.1.4)
    scope         JSONB NOT NULL DEFAULT '{}',   -- {client_key_ids: [], tags: []}
    tags          JSONB NOT NULL DEFAULT '[]',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_routing_rules_enabled_priority ON routing_rules (enabled, priority);

-- Per-request rule evaluation trace (for debugging & audit)
CREATE TABLE rule_evaluations (
    id             UUID PRIMARY KEY,
    request_id     UUID NOT NULL,                -- correlation id (see 4.4)
    rule_id        UUID REFERENCES routing_rules(id) ON DELETE SET NULL,
    matched        BOOLEAN NOT NULL,
    action_applied JSONB,
    reason         TEXT,
    evaluated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_rule_evals_request_id ON rule_evaluations (request_id);
```

#### 4.1.2 New service module

`brain/src/brain/rules/` containing:
- `schema.py` — Pydantic models for rule/match/action.
- `evaluator.py` — pure predicate evaluator (tree walker, no side effects).
- `context.py` — `RequestContext` dataclass built in the gateway (see 4.1.5).
- `pipeline.py` — orchestrator: load enabled rules by priority, evaluate, apply first match (or merge depending on `action.mode`).

Unit tests live in `tests/test_brain_rules_*.py`.

#### 4.1.3 Match DSL (JSON predicate tree)

```json
{
  "all": [
    { "field": "model_alias", "op": "in", "value": ["code-auto"] },
    { "field": "prompt_tokens_estimate", "op": ">", "value": 4000 },
    { "any": [
        { "field": "client_key.tags", "op": "contains", "value": "internal" },
        { "field": "hour_of_day", "op": "between", "value": [0, 6] }
    ]}
  ]
}
```

Supported operators: `=`, `!=`, `in`, `not_in`, `contains`, `>`, `>=`, `<`, `<=`, `between`, `regex`, `exists`.

Supported context fields (computed once per request):
- `model_alias`, `messages_count`, `prompt_tokens_estimate`, `has_functions`, `has_tools`, `stream`, `temperature`
- `client_key.id`, `client_key.tags`, `client_key.scopes`
- `session_id`, `conversation_length`
- `hour_of_day`, `day_of_week`
- `credit.{provider}.tokens_remaining`, `credit.{provider}.usd_remaining`
- `task_type` (from existing auto-detect heuristic — now reused as a field)

#### 4.1.4 Action shape

```json
{
  "mode": "select",               // "select" | "filter" | "annotate"
  "route_tier": "thinking",       // optional
  "route_model": "claude-3-5-sonnet-20241022", // optional direct model
  "prefer_providers": ["anthropic", "openai"], // ordered preference
  "exclude_providers": ["google"],
  "require_features": ["functions"],
  "min_usd_remaining": 0.50,
  "min_tokens_remaining": 5000,
  "max_cost_usd": 0.02,
  "strategy": "cheapest_available", // override tier strategy
  "set_tags": ["high-stakes"],
  "stop_on_match": true
}
```

#### 4.1.5 Router integration

`get_ranked_candidates()` gains a prelude step:

```python
context = build_request_context(session, request, current_key)
rule_result = rules_pipeline.apply(session, context)
# rule_result: effective tier / direct model / filter lambda / strategy / limits
candidates = resolve_candidates(session, rule_result.alias or request.model, request)
candidates = [c for c in candidates if rule_result.allows(c)]
candidates = rank(candidates, strategy=rule_result.strategy or tier.strategy)
```

Rule evaluations are persisted to `rule_evaluations` with the request correlation id and surfaced in the Logs UI on request detail.

#### 4.1.6 GUI page (`gui/src/pages/Rules.tsx`)

- List view with drag-reorder priority, enable/disable toggle, tag filter.
- Rule editor: structured (form) + JSON modes.
- "Test rule" dialog: paste sample request JSON → see matched rules + resulting candidates + chosen one.

---

### 4.2 Credit tracking — USD + thresholds

#### 4.2.1 Schema additions

```sql
-- USD-level balance per credential (distinct from token-level quota)
CREATE TABLE credit_balances (
    id               UUID PRIMARY KEY,
    credential_id    UUID NOT NULL REFERENCES credentials(id) ON DELETE CASCADE,
    usd_remaining    NUMERIC(12,4),            -- null if provider doesn't expose
    usd_granted      NUMERIC(12,4),
    usd_used         NUMERIC(12,4),
    source           TEXT NOT NULL,            -- "provider_api" | "computed_from_usage"
    polled_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_credit_balances_cred_polled ON credit_balances (credential_id, polled_at DESC);

-- Per-gateway-key spend budgets
CREATE TABLE key_budgets (
    id                 UUID PRIMARY KEY,
    key_id             UUID NOT NULL REFERENCES gateway_keys(id) ON DELETE CASCADE,
    window             TEXT NOT NULL,          -- "daily" | "monthly" | "lifetime"
    limit_usd          NUMERIC(12,4) NOT NULL,
    spent_usd          NUMERIC(12,4) NOT NULL DEFAULT 0,
    resets_at          TIMESTAMPTZ,
    action_on_exceed   TEXT NOT NULL DEFAULT 'block',  -- "block" | "warn" | "throttle"
    enabled            BOOLEAN NOT NULL DEFAULT TRUE
);
```

#### 4.2.2 Adapter contract extension

Each adapter gets an optional `get_credit_balance(credential) -> CreditBalance | None`. Adapters that can't implement this return `None` (rather than fabricating a token count). Known-implementable today: OpenAI, Anthropic (workspace spend), OpenRouter, Unify, Together, Fireworks, Groq.

#### 4.2.3 Polling behavior

In `quota-poller/main.py`:

- Extend `poll_quotas()` to call `adapter.get_credit_balance()` alongside `get_quota()` and persist `credit_balances` + Redis key `credit:{cred}:usd` (TTL matches poll interval × 2).
- Introduce adaptive polling: if a credential's `usd_remaining / usd_granted < 0.10`, drop its poll interval to 60s; if `< 0.25`, 120s; otherwise default.
- Explicit "unknown" state: when both token and USD polling fail or are unsupported, Redis stores `quota:{cred}:{model} = UNKNOWN` (sentinel) rather than a fabricated 10,000. Router treats UNKNOWN as "allowed, score neutral" instead of "plenty available".

#### 4.2.4 Routing

New match context fields available to rules:
- `credit.{cred}.usd_remaining`
- `credit.{cred}.usd_remaining_pct`
- `credit.{cred}.unknown`

Action-level enforcement:
- `min_usd_remaining` filters candidates before ranking.
- `max_cost_usd` per request (pre-estimated from prompt tokens × per-1k cost).

Per-key budget pre-check middleware: before routing, read the summed `cost_usd` of `request_logs` in the current window for the `client_key_id`. If over limit, return `402 Payment Required` style response.

---

### 4.3 Chat history + server-side context

#### 4.3.1 Schema changes

Non-breaking additions on existing tables:

```sql
ALTER TABLE chat_sessions ADD COLUMN client_key_id UUID REFERENCES gateway_keys(id) ON DELETE SET NULL;
ALTER TABLE chat_sessions ADD COLUMN external_session_key TEXT UNIQUE;  -- client-supplied id
ALTER TABLE chat_sessions ADD COLUMN metadata JSONB NOT NULL DEFAULT '{}';
CREATE INDEX ix_chat_sessions_client_key ON chat_sessions (client_key_id);

ALTER TABLE chat_messages ADD COLUMN tokens INTEGER;
ALTER TABLE chat_messages ADD COLUMN request_id UUID;     -- correlation (4.4)
ALTER TABLE chat_messages ADD COLUMN redacted BOOLEAN NOT NULL DEFAULT FALSE;

-- Rolling summaries for long conversations
CREATE TABLE conversation_summaries (
    id            UUID PRIMARY KEY,
    session_id    UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    up_to_message_id UUID NOT NULL REFERENCES chat_messages(id),
    summary       TEXT NOT NULL,
    tokens        INTEGER NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### 4.3.2 OpenAI-compat surface changes (additive; clients that don't use it are unaffected)

`POST /v1/chat/completions` accepts new optional fields (under the existing extra-allowed schema):

```jsonc
{
  "model": "auto",
  "messages": [{ "role": "user", "content": "What about that?" }],
  "session_id": "my-app-thread-42",           // optional, any string
  "session_mode": "append",                   // "append" | "replace" | "none" (default none)
  "context_policy": "summarize_when_over_80pct"  // see 4.3.4
}
```

Response gains (additively) `session_id` and `message_ids` at the top level.

New native endpoints (non-OpenAI, under `/api/v1/sessions`, scoped to the calling `GatewayKey`):

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/sessions` | List sessions for current key |
| POST | `/api/v1/sessions` | Create new session |
| GET | `/api/v1/sessions/{id}` | Session + messages |
| PATCH | `/api/v1/sessions/{id}` | Update topic/metadata |
| DELETE | `/api/v1/sessions/{id}` | Delete (cascade messages) |
| POST | `/api/v1/sessions/{id}/redact` | Scrub content on matching messages |

#### 4.3.3 Session persistence flow

1. Request arrives with `session_id`. Gateway resolves: existing `external_session_key` → row; else creates one, attaching `client_key_id`.
2. If `session_mode=append`, server prepends stored messages (trimmed to fit context budget — see 4.3.4) to the outgoing `messages`.
3. On response, both the user turn and assistant turn are inserted as `ChatMessage` rows with `request_id = <correlation id>`.

#### 4.3.4 Context window management

Config in `routing.yaml` (new top-level key):

```yaml
context:
  default_budget_pct: 0.7      # use up to 70% of model context for history
  overflow_policy: summarize   # "truncate_oldest" | "summarize" | "error"
  summary_model: "lite"        # used to produce rolling summary
  keep_last_n_messages: 6      # always keep the last N verbatim
```

Summaries are produced lazily when a request would overflow and then reused via `conversation_summaries` to avoid recomputation.

---

### 4.4 Enterprise logging

#### 4.4.1 Correlation id

Add `request_id UUID` column to `request_logs`, `system_events`, `chat_messages`, `rule_evaluations`. A single middleware generates the id at request entry and attaches it to `contextvars` so every downstream log/emit picks it up automatically (`shared/logging_ctx.py`).

#### 4.4.2 External sinks

`shared/src/shared/log_sinks/` with pluggable sinks:
- `syslog.py`
- `otlp.py` (OpenTelemetry HTTP — covers Datadog, Honeycomb, Grafana Tempo, etc.)
- `loki.py`
- `webhook.py` (generic HTTP POST on matching events)

Configuration in `.env` / via admin API:

```yaml
logging:
  sinks:
    - type: otlp
      endpoint: https://otel.example.com
      headers: { authorization: "Bearer ..." }
      levels: [INFO, WARNING, ERROR]
    - type: webhook
      endpoint: https://hooks.slack.com/...
      filter: { level: ERROR, component: [router, quota] }
```

Emission is fire-and-forget via a bounded `asyncio.Queue` with a background drainer; sink failures never block the request path.

#### 4.4.3 Alerting

New `alerts` table and a simple evaluator run on a 60s tick:

```sql
CREATE TABLE alerts (
    id           UUID PRIMARY KEY,
    name         TEXT NOT NULL,
    condition    JSONB NOT NULL,  -- e.g. {"metric":"error_rate","window":"5m","gt":0.05}
    sinks        JSONB NOT NULL,  -- list of sink configs or names
    enabled      BOOLEAN NOT NULL DEFAULT TRUE,
    last_fired_at TIMESTAMPTZ
);
```

Built-in conditions: `error_rate_gt`, `p95_latency_gt`, `credit_usd_below`, `provider_circuit_open`, `budget_exceeded`.

#### 4.4.4 Retention & export

- New `/admin/logs/export?format=json|csv&since=...&until=...` streaming endpoint.
- Replace the hardcoded 90-day prune with a `retention` config block (per-table retention in days) that the scheduler reads on startup.

#### 4.4.5 Request detail view

In the GUI Logs page, clicking a request opens a drawer showing: request body, response, cost, chosen provider + candidate list with scores, rule evaluations (from `rule_evaluations`), and every `SystemEvent` sharing that `request_id`.

---

### 4.5 Router hardening

Beyond the rule-engine integration (4.1.5) and the USD-aware filters (4.2.4):

- Consult `circuit:{cred}:{model}` Redis key in `get_ranked_candidates()` (skip candidates whose circuit is open). Today this is only cleared by the health prober; the router never checks it.
- Apply `min_quota_remaining` / `min_usd_remaining` to direct-model passthroughs, not only tier routes.
- Replace the hardcoded `quota = 999_999_999` unknown fallback in `router/quota.py` with the explicit UNKNOWN sentinel so ranking stays sane when providers don't report quota.

---

### 4.6 Provider & API surface expansion

Optional but matches the "one solution" goal. Each can be staged independently.

- **Generic OpenAI-compatible adapter + GUI** — register any `POST /v1/chat/completions`-compatible endpoint without writing code.
- **Embeddings** — `POST /v1/embeddings` with tier routing (`embed-fast`, `embed-quality`); add `input_cost_per_1k_embed` to `ProviderModel`.
- **Images** — `POST /v1/images/generations` / `/edits`. Add a dedicated tier and per-image cost fields.
- **Audio** — `/v1/audio/transcriptions` and `/v1/audio/speech`.
- **Tool use passthrough tests** — treat tool calls as first-class in rule context fields (`has_tools`, `tool_call_count`).

---

### 4.7 Credential vault improvements

- **Master key rotation** — a one-shot script (`scripts/rotate_vault_key.py`) that decrypts all credentials with the old key and re-encrypts with the new, gated by a maintenance window flag.
- **Decrypt audit** — every `/internal/decrypt/{id}` call emits a `SystemEvent` with `event_type=credential_decrypt`, `component=vault`, and the calling service name.
- **Soft delete + purge** — `Credential.deleted_at` and a scheduled purge job that respects configurable retention.

---

## 5. Phased Roadmap

Phases are ordered so each one delivers user-visible value and nothing later blocks on something earlier landing badly. Estimates assume one focused engineer; parallelize where possible.

### Phase 0 — Foundations (1–2 weeks)

1. Add `request_id` correlation id + middleware + columns on `request_logs` and `system_events`.
2. Introduce UNKNOWN quota sentinel in quota-poller + router.
3. Wire circuit-breaker check into router candidate filtering.
4. Apply `min_quota_remaining` to direct-model passthroughs.
5. Add `client_key_id` and `external_session_key` columns on `chat_sessions` (no behavior change yet).

Why first: tiny footprint, no GUI changes, unblocks every later phase.

### Phase 1 — USD credit tracking (2 weeks)

1. `credit_balances` table + Redis `credit:{cred}:usd` keys.
2. `get_credit_balance()` on adapters (start: OpenAI, OpenRouter, Together, Anthropic; others NO-OP).
3. Adaptive polling (faster when low).
4. Admin API + GUI tiles for USD-per-credential.

Outcome: you can actually see remaining dollars per key, and polling gets more aggressive as balances drop.

### Phase 2 — Rules engine (Brain v2) (3–4 weeks)

1. `routing_rules` + `rule_evaluations` tables and Pydantic schema.
2. `brain/rules/` evaluator + pipeline, unit tests on predicate operators.
3. Router prelude step: rules → effective tier/model/filter → rank.
4. Admin API: CRUD rules, "test rule" endpoint.
5. GUI `Rules.tsx` page (structured + JSON editors, drag priority, test dialog).

Outcome: the "brain that decides based on user rules" is a reality. Internal system selection (current brain) becomes one rule named "system_llm_selector".

### Phase 3 — Chat history + context continuity (2–3 weeks)

1. Session scoping to `GatewayKey`; `external_session_key` flow.
2. Optional `session_id` / `session_mode` on `/v1/chat/completions`.
3. `conversation_summaries` + overflow policies from `routing.yaml`.
4. Per-key `/api/v1/sessions` endpoints.
5. GUI updates on Chat page (reuse most of the playground).

Outcome: any client sending `session_id` gets server-side history and automatic context window management.

### Phase 4 — Enterprise logging (2 weeks)

1. Log sinks (`syslog`, `otlp`, `loki`, `webhook`).
2. Alerts table + evaluator + built-in conditions.
3. Log export endpoint + UI button.
4. Retention config block, replace hardcoded 90-day prune.
5. Request-detail drawer in GUI.

Outcome: ops teams can ship logs to existing backends, get Slack alerts on errors/low credit, export audit bundles for compliance.

### Phase 5 — Budgets + vault hardening + provider expansion (2+ weeks, flexible)

1. `key_budgets` + middleware enforcement.
2. Vault key rotation script + decrypt audit + credential soft delete.
3. Generic OpenAI-compatible provider (code + GUI).
4. `/v1/embeddings` (highest-ROI of the extra surfaces).
5. `/v1/images` and `/v1/audio` as follow-on.

---

## 6. Risks & Open Decisions

- **Rule engine performance.** Rules evaluated on every request; cap enabled rule count (e.g. 200) and compile predicate trees once per change. Benchmark target: < 1ms overhead per request for 50 rules.
- **Session-aware API compatibility.** Accepting `session_id` inside `/v1/chat/completions` is additive but non-standard. Document clearly; keep "no session" the default.
- **USD balance availability.** Few providers expose real-time USD; be honest with UNKNOWN rather than guess. Consider computed balances from `usd_granted - sum(request_logs.cost_usd)` as a fallback.
- **Context summarization quality.** Summarizing with a `lite` model may drop detail. Make policy configurable per session and always keep the last N messages verbatim.
- **Backwards compatibility of `brain_optimized`.** The existing `brain_optimized` strategy should keep working as a rule-free fallback; when Rules v2 lands, it becomes sugar for "apply brain_ranker.score()".
- **SQLite vs PostgreSQL.** The schema uses JSONB in proposals. SQLite has JSON1 functions but no JSONB; the Alembic migrations should use `sa.JSON()` and rely on SQLAlchemy's cross-dialect handling (as the codebase already does for existing JSON columns).

---

## 7. Success Criteria

The plan is "delivered" when all of the following are true:

1. Any user can add a new LLM provider in the GUI (via the generic OpenAI-compatible adapter) and use it from `/v1/chat/completions` without code changes.
2. The dashboard shows live USD remaining (where available) per credential, refreshed at least every 5 minutes, and polling accelerates for low balances.
3. A user can write a plain-English-style rule in the GUI ("if prompt > 4000 tokens and client tag is 'premium', use thinking tier, never use google") and see it applied with a visible trace in the request detail view.
4. An external app calling `/v1/chat/completions` with `session_id=foo` across 50 turns can send only the latest user message and receive responses that remember earlier context, with tokens staying below the model window.
5. Every request has a `request_id` that joins a `RequestLog`, a chain of `SystemEvent`s, and its `rule_evaluations`; those events can be streamed to an external OTLP backend.
6. Per-key USD budgets block or throttle runaway clients.

---

## 8. Appendix — Key File Pointers

- Routing engine: `router/src/router/core.py`, `router/src/router/quota.py`, `router/routing.yaml`
- Brain today: `brain/src/brain/{config,ranker,selector,tester,health,importer,errors}.py`
- Quota poller: `quota-poller/src/quota_poller/main.py`
- Self-heal: `selfheal/src/selfheal/{adaptive_cooldown,incident_tracker,health_prober}.py`
- Credential vault: `credential-vault/src/credential_vault/main.py`, `shared/src/shared/security.py`
- Models/schemas: `shared/src/shared/models.py`, `shared/src/shared/schemas.py`
- Request flow: `api-gateway/src/api_gateway/routes/completions.py`
- Admin API: `api-gateway/src/api_gateway/routes/admin.py`
- Chat (admin playground today): `api-gateway/src/api_gateway/routes/chat.py`
- Launcher: `launcher/src/launcher/main.py`, `launcher/src/launcher/scheduler.py`
- GUI pages: `gui/src/pages/*.tsx`
- GUI API client: `gui/src/lib/api.ts`

See `TASKS.md` for the issue-ready task list by phase.
