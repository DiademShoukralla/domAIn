# 3. Schemas and knowledge sources

Date: 2026-09-22

## Status

Accepted

## Context

domAIn's API, agents, and client must speak the same types at every boundary. Knowledge sources are not self-contained blobs — they reference external systems (GitHub repos, Linear teams) that require per-user OAuth credentials. We need schemas for review I/O and a data model that ties indexed content back to the connection that fetched it.

## Decision

### Core schemas

All schemas are Pydantic models shared between the FastAPI layer and LangGraph nodes.

#### `ReviewRequest`

```python
class ReviewRequest(BaseModel):
    query: str
    project_id: Optional[UUID] = None
```

| Field | Source | Notes |
|-------|--------|-------|
| `query` | Request body | The question, proposal, or PR diff to review. |
| `project_id` | Request body (optional) | Scopes retrieval to a project. Omit for user-global context. |
| `user_id` | **Auth context only** | Extracted from the authenticated session. Never accepted in the request body. |

**Rationale:** `user_id` in the body would be a security footgun (caller could impersonate another user). Auth middleware resolves identity once; all downstream nodes receive it via graph state, not user input.

#### `PersonaOpinion`

```python
class PersonaOpinion(BaseModel):
    persona: str          # "ux" | "dev_experience" | "business"
    verdict: Verdict
    reasoning: str
    citations: list[Citation]
```

Each persona produces one `PersonaOpinion` per review. Citations reference knowledge-layer chunks (document ID + chunk index) so the client can link back to source material.

#### `CouncilDecision`

```python
class CouncilDecision(BaseModel):
    persona_opinions: list[PersonaOpinion]  # always 3 in v1
    overall_verdict: Verdict
    synthesis: str
```

The chair's output. `synthesis` is a narrative reconciling the three persona opinions, not a mechanical aggregation.

#### `Verdict` vocabulary

```python
class Verdict(str, Enum):
    APPROVE = "approve"
    REQUEST_CHANGES = "request_changes"
    COMMENT = "comment"
```

**Rationale:** These three values mirror **GitHub's PR review states** (`APPROVE`, `REQUEST_CHANGES`, `COMMENT`). Since the council's write-back path opens GitHub PRs, aligning verdict vocabulary means a `CouncilDecision` maps directly to a GitHub review action without translation logic.

**Rejected alternatives:**

- Custom scales (`pass` / `fail` / `needs_discussion`) — requires mapping layer to GitHub and loses semantic precision.
- Numeric scores — meaningless for PR review write-back and encourage false precision.

### Knowledge source and connection model

External knowledge lives in GitHub repos and Linear — not in uploaded files. Each fetch location needs credentials.

#### `Connection`

Stores OAuth credentials per provider per user.

```python
class Connection(Base):
    id: UUID
    user_id: UUID                    # owner; required
    provider: str                    # "github" | "linear"
    access_token: str                # encrypted at rest
    refresh_token: Optional[str]     # encrypted at rest
    token_expires_at: Optional[datetime]
    external_account_id: str         # GitHub user id or Linear user id
    external_account_name: str       # display name / login
    created_at: datetime
    updated_at: datetime
```

One user may have one `Connection` per provider. Re-authorizing updates the existing row.

#### `KnowledgeSource`

```python
class KnowledgeSource(Base):
    id: UUID
    user_id: Optional[UUID]          # owner; see ADR 0004 scoping
    project_id: Optional[UUID]       # scope; see ADR 0004
    source_type: SourceType
    external_ref: str                # repo full name or Linear team id
    connection_id: UUID              # FK → Connection
    name: str                        # display name
    status: SourceStatus
    status_message: Optional[str]    # error detail or progress note
    last_indexed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

class SourceType(str, Enum):
    GITHUB_REPO = "github_repo"
    LINEAR = "linear"

class SourceStatus(str, Enum):
    PENDING = "pending"
    INDEXING = "indexing"
    READY = "ready"
    ERROR = "error"
```

| Field | Purpose |
|-------|---------|
| `external_ref` | Identifies *what* to fetch: `"DiademShoukralla/domAIn"` for GitHub, `"team-uuid"` for Linear |
| `connection_id` | Identifies *whose credentials* to use for fetching |
| `status` | Four-state lifecycle visible in the UI (see design system `SourceListItem`) |

**Rationale:**

- Separating `Connection` (credentials) from `KnowledgeSource` (fetch location) lets a user connect GitHub once and attach multiple repos, and reconnect without re-creating sources.
- `external_ref` + `connection_id` replaces ambiguous URL strings — the backend resolves fetch mechanics from `source_type`.
- Four status values give the UI enough signal to show progress without over-modeling partial index states.

**Rejected alternatives:**

- File upload as a source type — out of scope for v1; all knowledge comes from connected external systems.
- Embedding OAuth tokens directly on `KnowledgeSource` — duplicates credentials when one connection backs multiple sources.

### Status lifecycle

```
pending → indexing → ready
                  ↘ error
```

| Status | Meaning |
|--------|---------|
| `pending` | Source created; indexing not yet started |
| `indexing` | Chunk → embed → store pipeline running |
| `ready` | Indexed and available for retrieval |
| `error` | Indexing failed; `status_message` explains why |

Re-indexing transitions `ready → indexing → ready` (or `error`).

## Consequences

- Shared Pydantic models enforce contract consistency from API through to LangGraph state.
- `user_id` never in the request body eliminates an entire class of authorization bugs.
- GitHub-aligned verdicts make write-back a thin mapping layer.
- Connection/KnowledgeSource split keeps credential management centralized.
- Four status values align with the design system; the UI must not invent additional states.
- No file upload simplifies ingestion to two well-defined fetch adapters (GitHub API, Linear API).
