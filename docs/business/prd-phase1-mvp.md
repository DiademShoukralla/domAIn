# PRD: domAIn Phase 1 MVP

Date: 2026-09-22
Status: Draft

## Overview

domAIn is a multi-agent decision council that reviews proposals, PRs, and questions against an indexed knowledge layer. Phase 1 delivers the core loop: OAuth-connect external knowledge sources (GitHub repos, Linear), ask questions in a single unified chat (no mode selector), and receive either a direct retrieval answer or a structured council recommendation.

## MVP scope

### In scope (v1)

| Capability | Description |
|------------|-------------|
| Single user, single project | One authenticated user, one active project. Multi-tenant and multi-project are future work. |
| OAuth connections | Connect GitHub and Linear accounts via hand-rolled OAuth (authlib). Tokens stored on `Connection` entity. |
| Knowledge source management | Attach GitHub repos and Linear teams as knowledge sources. Sources indexed into pgvector + full-text search. Four status states: `pending`, `indexing`, `ready`, `error`. |
| Unified chat | One Composer, no routing toggle. Supervisor classifies intent and routes to greeting, simple retrieval, or council review automatically. |
| Simple retrieval | User asks a factual question; supervisor routes to `simple_retrieval`; system returns a direct answer with citations. |
| Strategic session (council) | User submits a review-worthy question; supervisor routes to `strategic_session`; three personas debate; chair synthesizes a `CouncilDecision`. |
| Structured output | Council responses include per-persona verdicts (`approve` / `request_changes` / `comment`), reasoning, citations, and an overall synthesis. |
| Write-back (manual trigger) | Council can propose doc updates via GitHub PR and roadmap updates via Linear API. |

### Out of scope (v1)

- Multi-user / multi-project / RBAC beyond nullable scoping columns
- File upload as a knowledge source
- User-facing chat mode selector (Simple / Council toggle)
- `linear_read` and `linear_write` intent handlers (stubbed; return "not yet available")
- Automated write-back without user confirmation
- Eval pipeline for persona/council output quality (Phase 2)
- Fleet visualizer
- Separate staging environment

## System topology

```
┌─────────────────────────────────────────────────────────┐
│                    Web Frontend                          │
│     Unified chat · Source rail · OAuth connect           │
└────────────────────────┬────────────────────────────────┘
                         │ HTTPS / WebSocket
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Backend                        │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ OAuth    │  │ Source CRUD  │  │ Chat endpoint    │  │
│  │ (authlib)│  │ + indexing   │  │ (unified)        │  │
│  └──────────┘  └──────────────┘  └────────┬─────────┘  │
│                                           │              │
│  ┌────────────────────────────────────────▼──────────┐  │
│  │              LangGraph Agent Graph                 │  │
│  │  Supervisor ──┬── greeting                         │  │
│  │               ├── simple_retrieval (RAG)           │  │
│  │               ├── strategic_session ──┐            │  │
│  │               ├── linear_read [stub]  │            │  │
│  │               └── linear_write [stub] │            │  │
│  │                                         ▼            │  │
│  │               Orchestrator → [UX, DevExp, Biz]      │  │
│  │                         → Chair → CouncilDecision  │  │
│  └───────────────────────────────────────────────────┘  │
│                         │                                │
│  ┌──────────────────────▼──────────────────────────┐   │
│  │           Hybrid Retrieval Pipeline              │   │
│  │   pgvector (Voyage embeddings) + FTS → RRF      │   │
│  └──────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   Postgres           │
              │   (pgvector + FTS)   │
              └─────────────────────┘

External:
  · Voyage AI API (embeddings)
  · Anthropic API (LLM via LangChain)
  · GitHub API (repo indexing, PR write-back) — via user OAuth
  · Linear API (roadmap indexing, issue write-back) — via user OAuth
```

### Key components

| Component | Technology | Role |
|-----------|-----------|------|
| Backend API | FastAPI | REST + WebSocket endpoints, OAuth, source management |
| Auth | authlib + GitHub/Linear OAuth Apps | User identity and provider tokens |
| Vector + text store | Postgres + pgvector | Chunk storage, vector similarity, full-text search |
| Embeddings | Voyage `voyage-context-4` | Contextual chunk embeddings |
| LLM | Claude via LangChain `init_chat_model` | Supervisor routing, persona reasoning, chair synthesis, RAG answers |
| Agent orchestration | LangGraph | Supervisor graph + nested council subgraph |
| Frontend | Web (design system in `docs/business/design-system/`) | Unified chat, source rail, OAuth connect flows |

## User flows

### Flow 1: Connect a provider and attach a knowledge source

```
User → Settings / Sources rail → "Connect GitHub" (or Linear)
  → OAuth redirect → callback → Connection stored
  → "Add source" → select provider → pick repo (or Linear team)
  → Backend creates KnowledgeSource (status: pending)
  → Indexing pipeline: pending → indexing → ready (or error)
  → Source appears in rail with status chip
```

**Acceptance criteria:**

- User can OAuth-connect GitHub and Linear independently.
- User can attach a GitHub repo by selecting from connected account.
- User can attach a Linear team/project as a knowledge source.
- Source status progresses through `pending` → `indexing` → `ready`.
- Failed indexing shows `error` status with actionable message.
- User can delete a source (removes chunks from the store).
- User can refresh a source (re-index from origin).
- No file upload option is presented.

### Flow 2: Unified chat — simple retrieval

```
User → Chat → types "What ADRs cover the permissions model?"
  → Backend: supervisor classifies → simple_retrieval
  → embed query → hybrid retrieval (vector + FTS → RRF) → LLM answer with citations
  → Response streams to chat UI
```

**Acceptance criteria:**

- No mode selector visible in the Composer.
- Answer is grounded in indexed knowledge sources.
- Citations link to source documents/chunks.
- Single LLM call after retrieval (no persona agents).
- Response streams via WebSocket.

### Flow 3: Unified chat — strategic council review

```
User → Chat → types "Review this proposal: migrate chunking to semantic splitting"
  → Backend: supervisor classifies → strategic_session
  → Orchestrator fans out to 3 persona agents in parallel
      Each persona: hybrid retrieval → LLM reasoning → PersonaOpinion
  → Chair: receives 3 opinions → LLM synthesis → CouncilDecision
  → Structured response returned:
      · Per-persona: verdict (approve/request_changes/comment), reasoning, citations
      · Overall: verdict + synthesis narrative
```

**Acceptance criteria:**

- No mode selector visible in the Composer.
- All three personas return opinions before synthesis begins.
- Each opinion includes a verdict, reasoning, and citations.
- Overall verdict and synthesis reconcile persona disagreements.
- Persona messages and chair block render per design system markup contracts.

### Flow 4: Write-back (manual trigger)

```
User → receives CouncilDecision → clicks "Propose doc update" (or similar)
  → Backend opens GitHub PR with proposed ADR/doc changes
  → OR updates Linear issue with roadmap note
  → User reviews PR in GitHub / change in Linear
```

**Acceptance criteria:**

- Write-back uses the user's OAuth Connection token.
- GitHub write-back opens a PR; does not commit directly to main.
- Linear write-back updates an issue or adds a comment.

## Non-functional requirements

| Requirement | Target |
|-------------|--------|
| Deployment | Containerized, Cloud Run |
| Auth | OAuth (GitHub + Linear); session from OAuth identity |
| CI/CD | GitHub Actions: PR lint/type-check/test; merge → build/deploy |
| Latency (simple retrieval) | < 10s for typical queries |
| Latency (council) | < 30s (3 parallel persona calls + synthesis) |
| Data isolation | `can_access()` enforced on all reads |
| Design system | Composer has no routing toggle; source status uses 4 states |

## Related documents

- [ADR 0002: Tech stack](../adr/0002-tech-stack.md)
- [ADR 0003: Schemas and knowledge sources](../adr/0003-schemas-and-knowledge-sources.md)
- [ADR 0004: Permissions](../adr/0004-permissions.md)
- [ADR 0005: Routing and coordination](../adr/0005-routing-and-coordination.md)
- [Design system](design-system/README.md)
