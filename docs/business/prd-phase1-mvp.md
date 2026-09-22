# PRD: domAIn Phase 1 MVP

Date: 2026-09-22
Status: Draft

## Overview

domAIn is a multi-agent decision council that reviews proposals, PRs, and questions against an indexed knowledge layer. Phase 1 delivers the core loop: attach knowledge sources, chat in two modes (simple RAG and strategic council), and receive structured recommendations.

## MVP scope

### In scope (v1)

| Capability | Description |
|------------|-------------|
| Single user, single project | One authenticated user, one active project. Multi-tenant and multi-project are future work. |
| Knowledge source management | Attach, delete, and refresh knowledge sources (git repos, file uploads). Sources are indexed into pgvector + full-text search. |
| Simple RAG chat | User asks a question; system retrieves relevant chunks and returns a direct answer. No persona agents, no council — just retrieval + generation. |
| Strategic chat (council) | User submits a review request; three persona agents (UX, dev experience, business/product) independently query the knowledge layer and return opinions; a chair synthesizes a `CouncilDecision`. |
| Structured output | Council responses include per-persona verdicts, reasoning, citations, and an overall synthesis. |
| API key auth | Authenticate via API key; `user_id` resolved from key, never from request body. |

### Out of scope (v1)

- Multi-user / multi-project / RBAC
- Write-back to GitHub PRs or Linear (manual for v1; automated write-back is Phase 1.5+)
- Eval pipeline (Phase 2)
- Fleet visualizer
- Flutter mobile apps (web only for v1)
- Reasoning traces / chain-of-thought exposure in simple RAG mode
- Supervisor pattern / dynamic persona routing

## System topology

```
┌─────────────────────────────────────────────────────────┐
│                    Flutter Web (v1)                      │
│              Chat UI · Source management                 │
└────────────────────────┬────────────────────────────────┘
                         │ HTTPS / WebSocket
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Backend                        │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Auth     │  │ Source CRUD  │  │ Chat endpoints   │  │
│  │ (API key)│  │ + indexing   │  │ (RAG + council)  │  │
│  └──────────┘  └──────────────┘  └────────┬─────────┘  │
│                                           │              │
│  ┌────────────────────────────────────────▼──────────┐  │
│  │              LangGraph Council Graph               │  │
│  │  Orchestrator → [UX, DevExp, Business] → Chair    │  │
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

External (read-only in v1):
  · Voyage AI API (embeddings)
  · Anthropic API (LLM via LangChain)
  · Linear API (roadmap context, future write-back)
  · GitHub API (future write-back)
```

### Key components

| Component | Technology | Role |
|-----------|-----------|------|
| Backend API | FastAPI | REST + WebSocket endpoints, auth, source management |
| Vector + text store | Postgres + pgvector | Chunk storage, vector similarity, full-text search |
| Embeddings | Voyage `voyage-context-4` | Contextual chunk embeddings |
| LLM | Claude via LangChain `init_chat_model` | Persona reasoning, chair synthesis, simple RAG answers |
| Agent orchestration | LangGraph | Council graph (orchestrator → personas → chair) |
| Frontend | Flutter Web | Chat UI, knowledge source management |

## User flows

### Flow 1: Attach a knowledge source

```
User → Sources page → "Add source"
  → Select type (git repo URL or file upload)
  → Backend validates access (can_access)
  → Backend indexes: chunk → embed (Voyage) → store (pgvector + FTS)
  → Source appears in list with status "ready"
```

**Acceptance criteria:**

- User can attach a git repo by URL or upload files.
- Indexing completes and source status shows "ready".
- User can delete a source (removes chunks from the store).
- User can refresh a source (re-index from origin).

### Flow 2: Simple RAG chat

```
User → Chat page → Select "Simple" mode
  → Type a question
  → Backend: embed query → hybrid retrieval (vector + FTS → RRF) → LLM answer with citations
  → Response streams to chat UI
```

**Acceptance criteria:**

- Answer is grounded in indexed knowledge sources.
- Citations link to source documents/chunks.
- No persona agents invoked; single LLM call after retrieval.
- Response streams via WebSocket.

### Flow 3: Strategic chat (council review)

```
User → Chat page → Select "Council" mode
  → Submit a review request (query + optional project scope)
  → Backend: orchestrator fans out to 3 persona agents in parallel
      Each persona: hybrid retrieval → LLM reasoning → PersonaOpinion
  → Chair: receives 3 opinions → LLM synthesis → CouncilDecision
  → Structured response returned:
      · Per-persona: verdict (approve/request_changes/comment), reasoning, citations
      · Overall: verdict + synthesis narrative
```

**Acceptance criteria:**

- All three personas return opinions before synthesis begins.
- Each opinion includes a verdict, reasoning, and citations.
- Overall verdict and synthesis reconcile persona disagreements.
- Response is structured JSON (rendered in chat UI).

## Non-functional requirements

| Requirement | Target |
|-------------|--------|
| Deployment | Containerized, Cloud Run |
| Auth | API key (v1); OAuth deferred |
| Latency (simple chat) | < 10s for typical queries |
| Latency (council) | < 30s (3 parallel persona calls + synthesis) |
| Data isolation | `can_access()` enforced on all reads |

## Related documents

- [ADR 0002: Tech stack](../adr/0002-tech-stack.md)
- [ADR 0003: Schemas and synthesis](../adr/0003-schemas-and-synthesis.md)
- [ADR 0004: Permissions](../adr/0004-permissions.md)
