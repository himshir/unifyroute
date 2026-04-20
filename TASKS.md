# UnifyRoute — Task Breakdown

Companion to `PROJECT_PLAN.md`. Each task is sized to be issue-ready: clear scope, touched files, acceptance criteria. Task IDs use the form `P<phase>-<n>`.

Legend:
- **Touches:** files/modules expected to change
- **Depends on:** other task IDs
- **Acceptance:** how to know it's done

---

## Phase 0 — Foundations

### P0-1. Introduce request correlation id

- **Why:** Prereq for enterprise logging, rule evaluation trace, session persistence linkage.
- **Touches:**
  - New: `shared/src/shared/logging_ctx.py` (contextvar + helpers)
  - New: `api-gateway/src/api_gateway/middleware/request_id.py`
  - `api-gateway/src/api_gateway/main.py` (register middleware)
  - `shared/src/shared/models.py` (add `request_id UUID` to `RequestLog`, `SystemEvent`)
  - New Alembic migration `migrations/versions/xxxx_add_request_id.py`
  - `shared/src/shared/events.py` or wherever SystemEvent is emitted (pull id from contextvar)
  - `api-gateway/src/api_gateway/routes/completions.py` (stamp id on RequestLog)
- **Acceptance:**
  - Every incoming `/v1/*` request produces a UUID returned in the `X-Request-Id` response header.
  - A single request produces correlated rows across `request_logs` and `system_events` with the same `request_id`.
  - Existing unit tests still pass; new tests cover middleware + contextvar propagation.

### P0-2. UNKNOWN quota sentinel

- **Why:** Remove the lie of "10,000 tokens available" when a provider doesn't expose quota.
- **Touches:**
  - `quota-poller/src/quota_poller/main.py` (write sentinel `-1` or literal string `UNKNOWN` on failure)
  - `router/src/router/quota.py` (recognize sentinel, return `QuotaState.UNKNOWN`)
  - `router/src/router/core.py` (rank UNKNOWN neutrally; don't filter on `min_quota_remaining` when UNKNOWN)
- **Acceptance:**
  - Forcing an adapter's `get_quota` to raise results in Redis holding the sentinel (not 10000).
  - Router still routes to that credential (not filtered as "out of quota"), but its quota score is neutral (0.5) in composite strategies.

### P0-3. Consult circuit breaker in router

- **Why:** Today the router only checks `failed:` keys; `circuit:` keys are ignored.
- **Touches:**
  - `router/src/router/core.py`
  - `selfheal/src/selfheal/incident_tracker.py` (expose `is_circuit_open(cred_id, model_id)` if missing)
- **Acceptance:**
  - When circuit is open for a (cred, model), the router excludes it and diagnostics reports `circuit_open: n`.
  - Integration test: inject 10 errors in a window, next request skips that provider.

### P0-4. Enforce `min_quota_remaining` on direct model passthrough

- **Touches:** `router/src/router/core.py`
- **Acceptance:** Setting `min_quota_remaining` in a tier config also applies when a client sends the bare `model: "gpt-4o-mini"` — matching credential is filtered if below threshold.

### P0-5. Add chat session scoping columns (no behavior change)

- **Touches:**
  - `shared/src/shared/models.py` (`ChatSession.client_key_id`, `external_session_key`, `metadata`)
  - New Alembic migration
  - `shared/src/shared/schemas.py` (expose new fields)
- **Acceptance:** Migration runs clean on a seeded DB; existing admin chat flow unaffected.

---

## Phase 1 — USD Credit Tracking

### P1-1. `credit_balances` table + migration

- **Touches:** `shared/src/shared/models.py`, new Alembic migration.
- **Acceptance:** Table exists with the schema from PROJECT_PLAN §4.2.1. Cascade delete works.

### P1-2. Adapter `get_credit_balance()` contract

- **Touches:** `router/src/router/adapters/base.py` (or equivalent), all adapters.
- **Acceptance:**
  - Base adapter defines the interface returning `CreditBalance | None`.
  - All existing adapters have a concrete or `None`-returning implementation (no `NotImplementedError` at runtime).

### P1-3. Concrete credit adapters

- **Scope:** Implement `get_credit_balance()` for OpenAI (`/dashboard/billing/credit_grants` + `/usage`), OpenRouter, Together, Fireworks, Groq, Anthropic workspace spend where available.
- **Depends on:** P1-2
- **Acceptance:** Each adapter returns a populated `CreditBalance` in a live integration test against a real key (mock the HTTP layer for unit tests).

### P1-4. Quota-poller USD polling + adaptive interval

- **Touches:** `quota-poller/src/quota_poller/main.py`
- **Depends on:** P1-1, P1-2
- **Acceptance:**
  - Every poll, USD balance is fetched when supported and written to Redis (`credit:{cred}:usd`) and `credit_balances`.
  - Adaptive: when a credential's `usd_remaining / usd_granted < 0.10`, its next poll is scheduled in ≤60s.
  - SystemEvent emitted on threshold crossing (`low_credit_warning`).

### P1-5. Per-key budget schema + middleware

- **Touches:**
  - `shared/src/shared/models.py` (`key_budgets` table)
  - New Alembic migration
  - `api-gateway/src/api_gateway/middleware/budget.py`
  - `api-gateway/src/api_gateway/main.py` (register middleware before completions)
- **Acceptance:**
  - A daily $1 budget on key X blocks the request when cumulative spend in the window exceeds $1 (returns 402 + structured error).
  - `action_on_exceed = warn` logs a SystemEvent but allows the request.
  - `throttle` returns 429 with Retry-After header.

### P1-6. GUI — credit tiles + budgets

- **Touches:**
  - `gui/src/pages/Quota.tsx` (add USD panel)
  - `gui/src/pages/Settings.tsx` (budgets per key)
  - `gui/src/lib/api.ts` (new hooks for `/admin/credit_balances`, `/admin/key_budgets`)
- **Acceptance:** Dashboard shows USD remaining for each credential that supports it; budget UI CRUD works end-to-end.

---

## Phase 2 — Rules Engine (Brain v2)

### P2-1. Schema: `routing_rules` + `rule_evaluations`

- **Touches:** `shared/src/shared/models.py`, new Alembic migration.
- **Acceptance:** Migration applies cleanly; unique/index constraints from PROJECT_PLAN §4.1.1 present.

### P2-2. Rule schema (Pydantic) + evaluator

- **Touches:**
  - New: `brain/src/brain/rules/schema.py`
  - New: `brain/src/brain/rules/evaluator.py`
  - New: `brain/src/brain/rules/context.py`
  - New: `tests/test_brain_rules_evaluator.py`
- **Acceptance:**
  - Predicate operators `=, !=, in, not_in, contains, >, >=, <, <=, between, regex, exists` all have passing unit tests.
  - `all/any/not` composite nodes supported.
  - Missing context fields on `exists` op return `false`; on other ops raise a structured `RuleEvaluationError`.

### P2-3. Request context builder

- **Touches:**
  - `brain/src/brain/rules/context.py`
  - `api-gateway/src/api_gateway/routes/completions.py` (invoke builder)
- **Acceptance:** `RequestContext` exposes every field listed in PROJECT_PLAN §4.1.3; unit tests verify derived fields (`prompt_tokens_estimate`, `task_type`, etc.).

### P2-4. Rules pipeline + router integration

- **Touches:**
  - New: `brain/src/brain/rules/pipeline.py`
  - `router/src/router/core.py` (prelude step)
  - `tests/test_router_rules_integration.py`
- **Depends on:** P2-1, P2-2, P2-3
- **Acceptance:**
  - With zero rules, router behaviour is identical to current (regression suite passes).
  - A rule that sets `route_tier: thinking` overrides the incoming `model: "auto"`.
  - `rule_evaluations` rows are written per request with the correct `request_id`.

### P2-5. Admin API for rules

- **Touches:**
  - New: `api-gateway/src/api_gateway/routes/rules.py`
  - `api-gateway/src/api_gateway/main.py` (mount)
  - `shared/src/shared/schemas.py` (response schemas)
- **Acceptance:**
  - CRUD endpoints: `GET/POST/PATCH/DELETE /admin/rules`, `POST /admin/rules/reorder`, `POST /admin/rules/test`.
  - `POST /admin/rules/test` accepts `{ request: {...}, rule: {...} }` and returns which rules match + final effective decision without side effects.

### P2-6. GUI — Rules page

- **Touches:**
  - New: `gui/src/pages/Rules.tsx`
  - `gui/src/App.tsx` (route)
  - `gui/src/lib/api.ts` (hooks)
  - `gui/src/components/` (rule editor sub-components)
- **Acceptance:**
  - List view with priority drag-reorder, enable/disable, tag filter.
  - Rule editor with structured form + JSON tab + schema validation.
  - "Test rule" dialog shows matched rules and chosen candidate.

### P2-7. Retire `brain_optimized` as a manual strategy

- **Touches:** `router/routing.yaml` (default seed), `router/src/router/core.py`, docs.
- **Depends on:** P2-4
- **Acceptance:** `brain_optimized` becomes a thin shim that delegates to a preset rule named `system.brain_rank`; docs note deprecation but keep backward compat.

---

## Phase 3 — Chat History + Context Continuity

### P3-1. ChatMessage tokens + request_id + redacted columns

- **Touches:** `shared/src/shared/models.py`, new Alembic migration.
- **Depends on:** P0-1
- **Acceptance:** Migration adds the columns; existing admin playground keeps working.

### P3-2. `conversation_summaries` table

- **Touches:** `shared/src/shared/models.py`, new Alembic migration.

### P3-3. Session resolver module

- **Touches:** New: `api-gateway/src/api_gateway/services/sessions.py`
- **Acceptance:**
  - `resolve_session(client_key_id, external_session_key, create=True)` returns a `ChatSession`.
  - Unit tests cover: new key→new session, same key same ext key→same session, key A can't read key B's session by ext key.

### P3-4. `/v1/chat/completions` session_id + session_mode

- **Touches:**
  - `api-gateway/src/api_gateway/routes/completions.py`
  - `shared/src/shared/schemas.py` (extend `ChatCompletionRequest` with extra-allowed fields)
  - Tests: `tests/test_chat_completions_session.py`
- **Depends on:** P3-1, P3-3
- **Acceptance:**
  - Request with `session_id=foo, session_mode=append, messages=[latest user msg]` responds as if the full prior history were sent.
  - Both turns are persisted as `ChatMessage` rows tagged with `request_id`.
  - Default behavior (no `session_id`) unchanged.

### P3-5. Context window management

- **Touches:**
  - New: `api-gateway/src/api_gateway/services/context_window.py`
  - `router/routing.yaml` (new `context:` block)
  - `api-gateway/src/api_gateway/routes/completions.py` (invoke)
- **Depends on:** P3-4
- **Acceptance:**
  - With `overflow_policy: summarize`, a session longer than the chosen model's context gets automatically summarized (rolling summary cached in `conversation_summaries`).
  - `keep_last_n_messages` respected verbatim.

### P3-6. Native session endpoints

- **Touches:**
  - New: `api-gateway/src/api_gateway/routes/sessions.py` (mounted at `/api/v1/sessions`)
- **Depends on:** P3-3
- **Acceptance:** CRUD + `/redact` work scoped to the calling `GatewayKey`; a key cannot see another key's sessions.

### P3-7. GUI — session list per key + external sessions

- **Touches:** `gui/src/pages/Chat.tsx`, possibly new `gui/src/pages/Sessions.tsx`
- **Acceptance:** Operator can browse sessions per API key, view the history, redact or delete.

---

## Phase 4 — Enterprise Logging

### P4-1. Log sinks framework

- **Touches:**
  - New: `shared/src/shared/log_sinks/__init__.py`
  - New sink modules: `syslog.py`, `otlp.py`, `loki.py`, `webhook.py`
  - `shared/src/shared/events.py` (route events through sink queue)
- **Acceptance:**
  - Enabling an OTLP sink in config makes every emitted SystemEvent appear in the collector within 5s (validated with local otel-collector).
  - Sink failure does not block request handling; failures themselves emit a `sink_failure` event (to other sinks only, no loop).

### P4-2. Alerts schema + evaluator

- **Touches:**
  - `shared/src/shared/models.py` (`alerts` table)
  - New Alembic migration
  - New: `selfheal/src/selfheal/alert_evaluator.py` (runs on scheduler tick)
  - `launcher/src/launcher/scheduler.py` (register job)
- **Acceptance:**
  - Alert `error_rate_gt > 0.05` over 5m window fires a sink emission exactly once per breach (suppresses until recovery).
  - Built-in conditions listed in PROJECT_PLAN §4.4.3 are implemented and unit-tested.

### P4-3. Logs export endpoint

- **Touches:** `api-gateway/src/api_gateway/routes/admin.py`
- **Acceptance:**
  - `GET /admin/logs/export?format=json&since=...&until=...` streams NDJSON.
  - `format=csv` streams a header + rows; fields fixed.
  - Large ranges (>100k rows) do not load everything into memory (validated by peak memory test).

### P4-4. Retention config

- **Touches:**
  - `router/routing.yaml` (new `retention:` block) OR new `config/retention.yaml`
  - Quota-poller / scheduler prune job updated to read config
- **Acceptance:** Setting `retention.request_logs_days: 30` causes rows older than 30 days to be deleted on the next prune tick; default remains 90 days.

### P4-5. Request detail drawer in Logs UI

- **Touches:** `gui/src/pages/Logs.tsx`, API client.
- **Depends on:** P0-1, P2-4
- **Acceptance:**
  - Clicking a log row opens a drawer with: request JSON, response, cost/latency, chosen candidate + full candidate list with scores, rule evaluations, and linked SystemEvents (via `request_id`).

---

## Phase 5 — Vault Hardening + API Surface Expansion

### P5-1. Vault master key rotation script

- **Touches:** New: `scripts/rotate_vault_key.py`, docs entry in `docs/operations.md`.
- **Acceptance:**
  - Running with `--dry-run` reports counts without writing.
  - Running with `--old-key` and `--new-key` decrypts all credentials and re-encrypts in a single DB transaction.
  - Audit event emitted for rotation start/end.

### P5-2. Credential decrypt audit

- **Touches:** `credential-vault/src/credential_vault/main.py`
- **Acceptance:** Every `POST /internal/decrypt/{id}` emits a `credential_decrypt` SystemEvent with the `request_id`, calling service identity, and credential id (never the secret).

### P5-3. Soft delete credentials

- **Touches:** `shared/src/shared/models.py` (`deleted_at`), admin delete endpoint (soft-delete instead of hard-delete).
- **Acceptance:** Deleted credentials are excluded from all routing and polling but retained for audit; a scheduled purge removes them after configurable retention.

### P5-4. Generic OpenAI-compatible provider

- **Touches:**
  - New adapter: `router/src/router/adapters/openai_compat_generic.py`
  - `gui/src/pages/Providers.tsx` (GUI form: base_url + auth header template)
- **Acceptance:** User can add a new provider via GUI (e.g. pointing at a local vLLM or a custom host) without any code change, and complete a test call.

### P5-5. `/v1/embeddings` endpoint

- **Touches:**
  - New: `api-gateway/src/api_gateway/routes/embeddings.py`
  - Router: add embedding tier resolution
  - `ProviderModel` schema: add `supports_embeddings`, `embedding_cost_per_1k`
  - Alembic migration
- **Acceptance:** OpenAI's embeddings SDK works against UnifyRoute and is tier-routed exactly as chat completions.

### P5-6. `/v1/images` and `/v1/audio` (optional)

- **Acceptance:** Same test: drop-in replacement of OpenAI base URL works for image generation and audio transcription/TTS for configured providers.

---

## Cross-cutting (ongoing, not part of a phase)

### X-1. Keep `project_context.md` and `project_memory.md` current

- Every multi-step change updates these per `AGENTS.md` instructions.

### X-2. Documentation

- Update `docs/architecture.md` (or create it) reflecting each phase as it lands.
- Document rule DSL grammar in `docs/brain/rules.md`.
- Document session/context continuity in `docs/sessions.md`.

### X-3. Test coverage targets

- Unit tests per phase: evaluator (P2-2) ≥ 95%, session resolver (P3-3) ≥ 90%.
- Integration tests: add one end-to-end scenario per phase (e.g. P3 scenario: 20-turn conversation that triggers summarization).

---

## Quick Reference

| Phase | Headline | Rough duration | Depends on |
|---|---|---|---|
| 0 | Foundations | 1–2 weeks | — |
| 1 | USD credit tracking | 2 weeks | P0 |
| 2 | Rules engine (Brain v2) | 3–4 weeks | P0 |
| 3 | Chat history + context | 2–3 weeks | P0 |
| 4 | Enterprise logging | 2 weeks | P0, P2 |
| 5 | Vault hardening + API expansion | flexible | P0 |

Phases 1, 2, 3 can largely run in parallel once Phase 0 lands.
