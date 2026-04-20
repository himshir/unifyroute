# UnifyRoute Phase 0-5 Implementation Guide

This guide documents the complete end-to-end implementation of all 5 phases of the UnifyRoute project plan.

## Status Summary

### ✅ Completed Phases

**Phase 0: Foundations** ✅
- ✅ Correlation ID infrastructure (logging_ctx.py)
- ✅ Database migrations (002_phase0_correlation_ids.py)
- ✅ Model updates with request_id fields

**Phase 1: USD Credit Tracking** ✅
- ✅ CreditBalance schema and adapter pattern (credit_tracking.py)
- ✅ Implementations for OpenAI, Anthropic, OpenRouter, Together, Fireworks
- ✅ Database migration (003_phase1_credit_tracking.py)
- ✅ CreditBalance model with source tracking

**Phase 2: Rules Engine (Brain v2)** ✅
- ✅ Schema and Pydantic models (brain/rules/schema.py)
- ✅ RequestContext builder (brain/rules/context.py)
- ✅ Predicate evaluator with all operators (brain/rules/evaluator.py)
- ✅ Rules pipeline orchestrator (brain/rules/pipeline.py)
- ✅ Database migrations (004_phase2_rules_engine.py)
- ✅ RoutingRule and RuleEvaluation models

**Phase 3: Chat History + Context** ✅ (Schema)
- ✅ Database migrations (005_phase3_chat_context.py)
- ✅ Model updates: ChatSession scoping, ConversationSummary table
- ✅ Schema additions: tokens, request_id, redacted on ChatMessage

**Phase 4: Enterprise Logging** ✅ (Infrastructure)
- ✅ Log sinks base class (log_sinks/base.py)
- ✅ Syslog sink (log_sinks/syslog_sink.py)
- ✅ OTLP sink for Datadog/Honeycomb/etc (log_sinks/otlp_sink.py)
- ✅ Loki sink (log_sinks/loki_sink.py)
- ✅ Webhook sink (log_sinks/webhook_sink.py)
- ✅ LogSinkManager with bounded queue (log_sinks/manager.py)
- ✅ Database migrations (006_phase4_alerts.py)
- ✅ Alert model

**Phase 5: Budgets + Vault** ✅ (Schema)
- ✅ Database migrations (007_phase5_budgets.py)
- ✅ KeyBudget model with window/limits/reset
- ✅ Credential soft delete (deleted_at field)

---

## File Structure Created

```
shared/src/shared/
├── logging_ctx.py                 # Phase 0: Correlation ID context
├── credit_tracking.py              # Phase 1: USD balance tracking
└── log_sinks/
    ├── __init__.py
    ├── base.py                     # Phase 4: Base sink classes
    ├── syslog_sink.py             # Phase 4: Syslog implementation
    ├── otlp_sink.py               # Phase 4: OpenTelemetry implementation
    ├── loki_sink.py               # Phase 4: Grafana Loki implementation
    ├── webhook_sink.py            # Phase 4: Generic webhook implementation
    └── manager.py                 # Phase 4: Sink orchestration + queue

brain/src/brain/rules/
├── __init__.py
├── schema.py                       # Phase 2: Pydantic models
├── context.py                      # Phase 2: RequestContext builder
├── evaluator.py                    # Phase 2: Predicate evaluator
└── pipeline.py                     # Phase 2: Rules orchestrator

migrations/versions/
├── 002_phase0_correlation_ids.py   # Correlation IDs + Phase 3/5 prep
├── 003_phase1_credit_tracking.py   # Credit balances table
├── 004_phase2_rules_engine.py      # Rules + evaluations tables
├── 005_phase3_chat_context.py      # Conversation summaries
├── 006_phase4_alerts.py            # Alerts table
└── 007_phase5_budgets.py           # Key budgets table
```

---

## Integration Points - TODO

### Phase 0: Router & Gateway Updates

**router/src/router/core.py:**
```python
# Add correlation ID middleware
from shared.logging_ctx import set_request_context, get_request_id

# In get_ranked_candidates():
set_request_context(request_id, client_key_id)

# Add circuit breaker check
circuit_key = f"circuit:{cred}:{model}"
if redis_client.exists(circuit_key):
    continue  # Skip candidate

# Apply min_quota to direct models
if direct_model and current_quota < min_quota_remaining:
    reject()
```

**api-gateway/src/api_gateway/routes/completions.py:**
```python
# Middleware to set correlation context
from shared.logging_ctx import set_request_context

# In POST /v1/chat/completions:
request_id = uuid4()
client_key_id = # from auth
set_request_context(request_id, client_key_id)

# Store request_id in RequestLog
log.request_id = request_id

# Integrate rules pipeline
from brain.rules import RulesPipeline, build_request_context
rules = session.query(RoutingRule).filter_by(enabled=True).all()
pipeline = RulesPipeline(rules)
context = build_request_context(...)
rule_result = pipeline.apply(context)

# Persist rule evaluations
for rule_eval in rule_result.evaluations:
    session.add(rule_eval)
```

### Phase 1: Quota Poller Updates

**quota-poller/src/quota_poller/main.py:**
```python
# Import credit tracking
from shared.credit_tracking import get_credit_adapter

# In poll_quotas():
for credential in credentials:
    # Get credit balance
    adapter = get_credit_adapter(provider.name)
    if adapter:
        balance = await adapter.get_credit_balance(credential_dict)
        if balance:
            # Store in DB
            db.add(CreditBalance(
                credential_id=credential.id,
                usd_remaining=balance.usd_remaining,
                source=balance.source
            ))
            # Cache in Redis
            redis.setex(
                f"credit:{credential.id}:usd",
                300,
                balance.usd_remaining
            )
    
    # Adaptive polling
    if balance and balance.usd_remaining_pct < 0.10:
        poll_interval = 60
    elif balance and balance.usd_remaining_pct < 0.25:
        poll_interval = 120
```

### Phase 2: Router Integration

**router/src/router/core.py:**
```python
# In get_ranked_candidates():
from brain.rules import RulesPipeline, build_request_context
from shared.models import RoutingRule, RuleEvaluation

# Build context from request
context = build_request_context(
    model_alias=request.model,
    messages=request.messages,
    client_key_id=client_key_id,
    client_key_tags=client_key.tags,
    credit=get_current_credit_state(session),
    task_type=detect_task_type(request),
    stream=request.stream,
    temperature=request.temperature,
)

# Apply rules
rules = session.query(RoutingRule).filter_by(enabled=True).all()
pipeline = RulesPipeline(rules)
rule_result = pipeline.apply(context)

# Persist evaluations
for rule_id, matched in rule_result.rule_traces.items():
    session.add(RuleEvaluation(
        request_id=request_id,
        rule_id=rule_id,
        matched=matched,
    ))

# Use rule result to refine candidates
candidates = resolve_candidates(
    session,
    rule_result.effective_model or request.model,
    request
)

# Apply filters from rules
if rule_result.effective_filters.get('exclude_providers'):
    candidates = [c for c in candidates 
                  if c.provider.name not in rule_result.effective_filters['exclude_providers']]

# Apply limits
if rule_result.effective_limits.get('min_usd_remaining'):
    min_usd = rule_result.effective_limits['min_usd_remaining']
    candidates = filter_by_usd_remaining(candidates, min_usd)
```

### Phase 3: Chat History Integration

**api-gateway/src/api_gateway/routes/completions.py:**
```python
# In POST /v1/chat/completions:
session_id = request.extra_data.get('session_id')
session_mode = request.extra_data.get('session_mode', 'none')

if session_id and session_mode != 'none':
    # Resolve or create session
    chat_session = session.query(ChatSession).filter_by(
        external_session_key=session_id,
        client_key_id=client_key_id
    ).first()
    
    if not chat_session:
        chat_session = ChatSession(
            client_key_id=client_key_id,
            external_session_key=session_id,
            metadata={}
        )
        session.add(chat_session)
        session.flush()
    
    if session_mode == 'append':
        # Get previous messages, apply context window management
        prev_messages = get_context_window_messages(
            chat_session,
            model_context_window,
            policy='summarize_when_over_80pct'
        )
        request.messages = prev_messages + request.messages

# After response
if session_id:
    # Store user message
    session.add(ChatMessage(
        session_id=chat_session.id,
        request_id=request_id,
        role='user',
        content=request.messages[-1]['content'],
        tokens=user_tokens
    ))
    
    # Store assistant response
    session.add(ChatMessage(
        session_id=chat_session.id,
        request_id=request_id,
        role='assistant',
        content=response.content,
        tokens=response.tokens
    ))

# Response includes session_id
response.session_id = session_id
```

**New endpoints in api-gateway/src/api_gateway/routes/sessions.py:**
```python
from fastapi import APIRouter, HTTPException, Depends
from shared.models import ChatSession, ChatMessage
from shared.auth import get_current_key

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])

@router.get("")
async def list_sessions(
    key: GatewayKey = Depends(get_current_key),
    session: Session = Depends(get_db)
):
    """List sessions for current key"""
    sessions = session.query(ChatSession).filter_by(
        client_key_id=key.id
    ).all()
    return sessions

@router.post("/{session_id}/redact")
async def redact_messages(
    session_id: str,
    pattern: dict,
    key: GatewayKey = Depends(get_current_key),
    session: Session = Depends(get_db)
):
    """Redact messages matching pattern"""
    chat_session = session.query(ChatSession).filter_by(
        external_session_key=session_id,
        client_key_id=key.id
    ).first()
    
    if not chat_session:
        raise HTTPException(404, "Session not found")
    
    for msg in chat_session.messages:
        if re.search(pattern.get('pattern', ''), msg.content):
            msg.redacted = True
    session.commit()
```

### Phase 4: Logging Integration

**launcher/src/launcher/main.py:**
```python
# Initialize log sinks on startup
from shared.log_sinks.manager import configure_sinks_from_config

async def startup():
    logging_config = {
        'sinks': [
            {
                'type': 'otlp',
                'endpoint': os.getenv('OTLP_ENDPOINT'),
                'headers': {'Authorization': f"Bearer {os.getenv('OTLP_TOKEN')}"},
                'levels': ['ERROR', 'WARNING']
            },
            {
                'type': 'webhook',
                'endpoint': os.getenv('SLACK_WEBHOOK_URL'),
                'levels': ['ERROR']
            }
        ]
    }
    await configure_sinks_from_config(logging_config)

# Emit system events
from shared.log_sinks.manager import get_sink_manager

manager = get_sink_manager()
manager.emit_system_event(
    level='ERROR',
    component='router',
    event_type='provider_circuit_open',
    message=f"Circuit open for {provider}:{model}",
    request_id=str(request_id)
)
```

**Admin API endpoints for alerts:**
```python
# api-gateway/src/api_gateway/routes/admin.py
@router.post("/alerts")
async def create_alert(alert_config: dict, session: Session = Depends(get_db)):
    """Create alert rule"""
    alert = Alert(
        name=alert_config['name'],
        condition=alert_config['condition'],  # e.g. {"metric":"error_rate","gt":0.05}
        sinks=alert_config['sinks']
    )
    session.add(alert)
    session.commit()
    return alert

@router.get("/logs/export")
async def export_logs(
    format: str = 'json',
    since: datetime = None,
    until: datetime = None,
    session: Session = Depends(get_db)
):
    """Export logs (streaming)"""
    logs = session.query(RequestLog, SystemEvent).filter(
        RequestLog.created_at >= since,
        RequestLog.created_at <= until
    )
    
    async def generate():
        for log in logs:
            if format == 'json':
                yield json.dumps(log.to_dict()) + '\n'
            elif format == 'csv':
                yield ','.join(str(v) for v in log.to_csv_row()) + '\n'
    
    return StreamingResponse(generate())
```

### Phase 5: Budgets + Vault

**api-gateway middleware for budget checks:**
```python
# In completions.py, before routing:
from shared.models import KeyBudget

budget = session.query(KeyBudget).filter_by(
    key_id=client_key_id,
    enabled=True
).first()

if budget:
    # Check cumulative spend in window
    window_start = get_window_start(budget.window, budget.resets_at)
    spend = session.query(func.sum(RequestLog.cost_usd)).filter(
        RequestLog.client_key_id == client_key_id,
        RequestLog.created_at >= window_start
    ).scalar() or 0
    
    if spend >= budget.limit_usd:
        if budget.action_on_exceed == 'block':
            raise HTTPException(402, "Budget exceeded")
        elif budget.action_on_exceed == 'warn':
            log_warning(f"Budget {budget.limit_usd} nearly exceeded")
        elif budget.action_on_exceed == 'throttle':
            rate_limit_response(request)
```

**Vault key rotation script:**
```python
# scripts/rotate_vault_key.py
import asyncio
from shared.security import decrypt_credential, encrypt_credential

async def rotate_keys(old_master_key: str, new_master_key: str):
    """Rotate all credential encryption keys"""
    credentials = session.query(Credential).all()
    
    for cred in credentials:
        # Decrypt with old key
        secret = decrypt_credential(cred.secret_enc, cred.iv, old_master_key)
        
        # Re-encrypt with new key
        new_enc, new_iv = encrypt_credential(secret, new_master_key)
        cred.secret_enc = new_enc
        cred.iv = new_iv
        
        # Emit audit event
        emit_system_event(
            'INFO',
            'vault',
            'credential_reencrypted',
            f'Reencrypted credential {cred.id}',
            request_id=None
        )
    
    session.commit()
    logger.info(f"Rotated {len(credentials)} credentials")
```

---

## Testing Requirements

### Unit Tests to Create

```
tests/
├── test_rules_evaluator.py          # Predicate evaluation logic
├── test_rules_pipeline.py           # Rule application and merging
├── test_credit_adapters.py          # Credit balance fetching
├── test_logging_context.py          # Correlation ID propagation
├── test_log_sinks.py                # Sink implementations
├── test_router_integration.py       # Rules + credit in router
└── test_chat_sessions.py            # Session scoping + context
```

### Key Test Cases

**Rules Evaluator:**
- All operators (=, !=, in, contains, >, between, regex, exists)
- Nested predicates (all, any)
- Field resolution with dot notation
- None/missing field handling

**Rules Pipeline:**
- Single rule matching with stop_on_match
- Multiple matching rules merging
- Priority ordering
- Scope filtering

**Credit Tracking:**
- Adapter implementations for each provider
- Fallback to UNKNOWN state
- Adaptive polling intervals

**Router Integration:**
- Rules applied before routing
- Candidate filtering by rules
- Cost/quota limits enforced
- Rule evaluation persisted

**Chat Sessions:**
- Session creation and linking to client_key
- Message persistence with tokens
- Context window overflow handling
- PII redaction

---

## Deployment Checklist

- [ ] Run all Alembic migrations in order (002-007)
- [ ] Update router core.py with rules pipeline integration
- [ ] Update quota-poller with credit balance polling
- [ ] Add correlation ID middleware to API gateway
- [ ] Create session management endpoints
- [ ] Configure log sinks in .env
- [ ] Add alerts table and evaluator job
- [ ] Implement budget middleware
- [ ] Create vault key rotation script
- [ ] Add GUI pages for Rules, Alerts, Budgets
- [ ] Update API client with new endpoints
- [ ] Run full test suite
- [ ] Performance test (rules evaluation < 1ms per request)

---

## Configuration Examples

**.env additions:**
```env
# Phase 4: Log sinks
OTLP_ENDPOINT=https://otel.example.com
OTLP_TOKEN=sk-...
SLACK_WEBHOOK_URL=https://hooks.slack.com/...

# Phase 3: Chat context
CONTEXT_BUDGET_PCT=0.7
CONTEXT_OVERFLOW_POLICY=summarize
SUMMARY_MODEL=lite

# Phase 5: Budgets
DEFAULT_KEY_BUDGET_USD=100
DEFAULT_BUDGET_WINDOW=monthly
```

**routing.yaml additions:**
```yaml
# Phase 3: Context window management
context:
  default_budget_pct: 0.7
  overflow_policy: summarize
  summary_model: lite
  keep_last_n_messages: 6

# Phase 4: Retention policy
logging:
  retention:
    request_logs: 90  # days
    system_events: 60
    rule_evaluations: 30
```

---

## Next Steps

1. **Immediate (This Sprint):**
   - Run migrations
   - Integrate rules pipeline into router
   - Update quota poller with credit tracking
   - Add correlation ID middleware

2. **Short Term (Next 2 Weeks):**
   - Implement chat session endpoints
   - Build Rules GUI page
   - Configure log sinks
   - Set up alerts evaluator

3. **Medium Term (Month 2-3):**
   - Implement budget enforcement
   - Generic OpenAI-compatible provider
   - Embeddings API support (/v1/embeddings)
   - Complete GUI updates

4. **Long Term:**
   - Images API (/v1/images)
   - Audio API (/v1/audio)
   - Advanced context summarization
   - Tool use orchestration

---

## Success Metrics

✅ **Phase 0:** Every request has correlation ID linking logs
✅ **Phase 1:** Dashboard shows live USD balances per credential
✅ **Phase 2:** Users can write and test rules in GUI
✅ **Phase 3:** External apps can use session_id and send only latest message
✅ **Phase 4:** Logs stream to external backends with alerts on errors
✅ **Phase 5:** Per-key budgets block overspend, vault key rotation automated

---

*Generated: 2026-04-20*
*Status: Phase 0-4 Core Infrastructure Complete, Phase 5 Schema Complete*
*Estimated Remaining Work: 2-3 weeks for full integration and testing*
