# MEMANTO Session-Based Architecture

**Status**: Design Specification
**Date**: December 2025
**Author**: Dr. Majid Fekri, CTO Moorcheh.ai

---

## Overview

MEMANTO v2 introduces a **session-based authentication model** that eliminates the tenant_id concept and provides a secure, stateful interaction model for AI agents.

## Core Principles

1. **Moorcheh API Key = Identity**: The Moorcheh API key uniquely identifies the user/organization
2. **Agent = Memory Namespace**: Each agent has one persistent namespace
3. **Session = Time-Bounded Access**: Sessions provide temporary, scoped access to specific agents
4. **CLI-First UX**: Users interact via CLI, not raw HTTP calls
5. **Zero Configuration for Agents**: Real AI agents just call `memanto remember "content"`

---

## Architecture Components

### 1. Authentication Flow

```
┌─────────────────────────────────────────────────────────────┐
│ User provides Moorcheh API Key                              │
│ (stored in ~/.memanto/config.yaml, encrypted)                 │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ User creates MEMANTO agent                                    │
│ POST /api/v2/agents                                         │
│ Auth: Bearer {moorcheh_api_key}                             │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ MEMANTO creates namespace: memanto_agent_{agent_id}             │
│ (Isolated by Moorcheh API key at Moorcheh backend)         │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ User activates agent (starts session)                       │
│ POST /api/v2/agents/{agent_id}/activate                    │
│ Auth: Bearer {moorcheh_api_key}                             │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ MEMANTO issues session token (JWT)                            │
│ - Includes: agent_id, namespace, moorcheh_api_key (enc)    │
│ - Expires: 6 hours (configurable)                          │
│ - Signed: HMAC-SHA256                                      │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Agent operations use session token                          │
│ POST /api/v2/agents/{agent_id}/remember                    │
│ Auth: Bearer {session_token}                                │
└─────────────────────────────────────────────────────────────┘
```

### 2. Namespace Model

**Format**: `memanto_agent_{agent_id}`

**Isolation**: Moorcheh backend enforces isolation by API key

```
User A (API Key: key_abc123)
├── memanto_agent_customer-support    (accessible)
├── memanto_agent_sales-bot           (accessible)
└── memanto_agent_research-assistant  (accessible)

User B (API Key: key_xyz789)
├── memanto_agent_customer-support    (different namespace, isolated)
└── memanto_agent_project-manager     (accessible)
```

**Key insight**: Same `agent_id` under different API keys = different namespaces (isolated by Moorcheh)

### 3. Session Token Structure

**JWT Payload**:
```json
{
  "agent_id": "customer-support",
  "namespace": "memanto_agent_customer-support",
  "moorcheh_api_key_hash": "sha256...",
  "session_id": "sess_abc123xyz",
  "started_at": "2025-12-28T16:00:00Z",
  "expires_at": "2025-12-28T20:00:00Z",
  "iat": 1735401600,
  "exp": 1735416000
}
```

**Security**:
- Moorcheh API key NOT included in plaintext (hash only)
- Token signed with MEMANTO secret key
- Short expiration (6 hours default, configurable)
- Scoped to specific agent (cannot access other agents)

### 4. Session Storage

**File-based storage** (v1): `~/.memanto/sessions/`

```
~/.memanto/
├── config.yaml                      # Main configuration
└── sessions/
    ├── customer-support.json        # Session state
    ├── sales-bot.json
    └── active                       # Symlink to active session
```

**Session file structure** (`customer-support.json`):
```json
{
  "agent_id": "customer-support",
  "session_id": "sess_abc123xyz",
  "session_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "namespace": "memanto_agent_customer-support",
  "started_at": "2025-12-28T16:00:00Z",
  "expires_at": "2025-12-28T20:00:00Z",
  "pattern": "support",
  "status": "active"
}
```

**Future**: Moorcheh.ai backend is capable of handling millions of input memories as well as calls to the backend llms for intelligent and smart tasks

---

## API Endpoints

### Agent Lifecycle

#### Create Agent
```http
POST /api/v2/agents
Authorization: Bearer {moorcheh_api_key}
Content-Type: application/json

{
  "agent_id": "customer-support",
  "pattern": "support",
  "description": "Customer support AI agent",
  "metadata": {
    "real_agent_type": "claude-3.5-sonnet",
    "owner": "user@company.com"
  }
}

Response:
{
  "agent_id": "customer-support",
  "namespace": "memanto_agent_customer-support",
  "pattern": "support",
  "created_at": "2025-12-28T16:00:00Z",
  "status": "created"
}
```

#### List Agents
```http
GET /api/v2/agents
Authorization: Bearer {moorcheh_api_key}

Response:
{
  "agents": [
    {
      "agent_id": "customer-support",
      "namespace": "memanto_agent_customer-support",
      "pattern": "support",
      "created_at": "2025-12-27T10:00:00Z",
      "last_session": "2025-12-28T15:30:00Z",
      "memory_count": 1547,
      "session_count": 23,
      "status": "inactive"
    }
  ]
}
```

### 3. Use the Session

All memory operations now require the `X-Session-Token` header and use the `/api/v2/` path prefix.

```bash
# Store memory in agent's session
curl -X POST "http://localhost:8000/api/v2/agents/my-agent/remember?content=..." \
  -H "X-Session-Token: eyJhbGciOiJIUzI1..."

# Ask a question
curl -X POST "http://localhost:8000/api/v2/agents/my-agent/answer?question=..." \
  -H "X-Session-Token: eyJhbGciOiJIUzI1..."
```

#### Activate Agent (Start Session)
```http
POST /api/v2/agents/{agent_id}/activate
Authorization: Bearer {moorcheh_api_key}

Response:
{
  "session_id": "sess_abc123xyz",
  "session_token": "eyJhbGc...",
  "agent_id": "customer-support",
  "namespace": "memanto_agent_customer-support",
  "started_at": "2025-12-28T16:00:00Z",
  "expires_at": "2025-12-28T20:00:00Z"
}
```

#### Deactivate Agent (End Session)
```http
POST /api/v2/agents/{agent_id}/deactivate
Authorization: Bearer {session_token}

Response:
{
  "session_id": "sess_abc123xyz",
  "agent_id": "customer-support",
  "ended_at": "2025-12-28T18:30:00Z",
  "duration_hours": 2.5,
  "memories_created": 67,
  "summary_memory_id": "mem_summary_xyz"
}
```

### Memory Operations (Session-Scoped)

#### Remember
```http
POST /api/v2/agents/{agent_id}/remember
Authorization: Bearer {session_token}

Parameters:
  memory_type: str
  title: str
  content: str
  confidence: float = 0.8
  tags: str = None  (comma-separated)
  source: str = "agent"

Response:
{
  "memory_id": "mem_abc123",
  "agent_id": "customer-support",
  "session_id": "sess_abc123xyz",
  "namespace": "memanto_agent_customer-support",
  "status": "queued"
}
```

#### Recall
```http
GET /api/v2/agents/{agent_id}/recall
Authorization: Bearer {session_token}

Parameters:
  query: str
  limit: int = 10
  created_after: str = None (ISO 8601)
  created_before: str = None (ISO 8601)
  memory_types: str = None (comma-separated)

Response:
{
  "agent_id": "customer-support",
  "session_id": "sess_abc123xyz",
  "query": "customer preferences",
  "memories": [...]
}
```

#### Answer (RAG)
```http
POST /api/v2/agents/{agent_id}/answer
Authorization: Bearer {session_token}

Parameters:
  question: str

Response:
{
  "agent_id": "customer-support",
  "session_id": "sess_abc123xyz",
  "question": "What are customer communication preferences?",
  "answer": "Based on stored memories...",
  "sources": [...]
}
```

---

## Security Model

### 1. API Key Protection

```python
# NEVER store API key in session token plaintext
# NEVER log API key
# NEVER expose API key in responses

# Store API key:
# - Encrypted in config file
# - In memory during CLI session
# - Hash in session token for validation
```

### 2. Session Validation

```python
def validate_session(session_token: str) -> Session:
    """
    Validate session token

    Checks:
    1. Token signature valid (HMAC)
    2. Token not expired
    3. Agent still exists
    4. API key hash matches
    """
    payload = jwt.decode(session_token, SECRET_KEY)

    if datetime.now() > payload['exp']:
        raise SessionExpiredError()

    if not agent_exists(payload['agent_id']):
        raise AgentNotFoundError()

    return Session(**payload)
```

### 3. Agent Isolation

```python
@router.post("/{agent_id}/remember")
async def remember(
    agent_id: str,
    session: Session = Depends(get_current_session)
):
    # Enforce: session token MUST match agent_id
    if session.agent_id != agent_id:
        raise ForbiddenError(
            f"Session is for {session.agent_id}, "
            f"cannot access {agent_id}"
        )

    # Proceed with memory storage
    ...
```

---

## Migration from tenant_id Model

### Current (v1) - DEPRECATED
```python
# ❌ OLD: tenant_id in query params (spoofable)
POST /api/v2/agents/{agent_id}/remember?tenant_id=any-value
```

### New (v2) - RECOMMENDED
```python
# ✅ NEW: Session token with scoped access
1. **Activate session**: `POST /api/v2/agents/{agent_id}/activate`
2. **Authorize**: Use `X-Session-Token` for subsequent operations
3. **Automatic isolation**: All memory operations (`remember`, `recall`, `answer`) are automatically scoped to the active agent.
4. **CLI Convenience**: In the CLI, `memanto agent create` automatically performs activation for you.
```

### Namespace Migration

```python
# OLD namespace format:
memanto_{tenant_id}_agent_{agent_id}
memanto_acme-corp_agent_customer-support

# NEW namespace format:
memanto_agent_{agent_id}
memanto_agent_customer-support
```

---

## Configuration

### User Configuration (~/.memanto/config.yaml)

```yaml
memanto:
  version: "2.0"

  server:
    url: "http://localhost:8000"
    port: 8000

  moorcheh:
    api_key_encrypted: "enc_gAAAAABh..."  # Fernet encrypted

  session:
    default_duration_hours: 6
    auto_extend: true
    extend_threshold_minutes: 30  # Extend if < 30 min remaining
    auto_renew_enabled: true
    auto_renew_interval_hours: 6  # Fresh session every 6 hours

  cli:
    interactive_mode: true
    smart_parse: true
    auto_title: true
```

---

## Benefits Summary

| Aspect | Old (tenant_id) | New (Session-based) |
|--------|-----------------|---------------------|
| **Auth** | Query param (spoofable) | JWT token (signed) |
| **Identity** | Manual tenant_id | Automatic from API key |
| **Rotation** | Breaks on key rotation | Handled by Moorcheh |
| **Isolation** | Manual namespace | Moorcheh backend |
| **Agent Access** | Any agent accessible | Scoped to session |
| **UX** | Raw HTTP calls | CLI with guidance |
| **Security** | Low (param injection) | High (signed tokens) |

### API Endpoints and Authorization

| Endpoint | Header Required | Description |
|----------|-----------------|-------------|
| `POST /api/v2/agents` | `Authorization` | Create a new agent namespace |
| `POST /api/v2/agents/{id}/activate` | `Authorization` | Start session, get token |
| `POST /api/v2/agents/{id}/remember` | `X-Session-Token` | Store memory in session |
| `GET /api/v2/agents/{id}/recall` | `X-Session-Token` | Search session memories |
| `POST /api/v2/agents/{id}/answer` | `X-Session-Token` | Ask question over session memories |
| `POST /api/v2/session/extend` | `X-Session-Token` | Extend expiration time |

---

## Future Enhancements

1. **Multi-agent sessions**: Support activating multiple agents simultaneously
2. **Session persistence**: Redis backend for production
3. **Session transfer**: Transfer session between devices
4. **Audit logging**: Track all session operations
5. **Rate limiting**: Per-session rate limits
6. **Session analytics**: Usage metrics per session

---

**Conclusion**: The session-based architecture provides **secure**, **stateful**, and **user-friendly** access to MEMANTO memory services while maintaining perfect isolation through Moorcheh's multi-tenant backend.

**Questions?** Contact Dr. Majid Fekri, CTO Moorcheh.ai
