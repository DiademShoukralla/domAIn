# 2. Tech stack

Date: 2026-09-22

## Status

Accepted

> **Living document.** Future tech-stack changes are appended to this ADR as dated sections rather than creating new ADR files. This keeps the full evolution of the stack in one place and avoids proliferating single-topic ADRs for incremental choices.

## Context

domAIn Phase 1 is a containerized backend (deployed on Cloud Run) that exposes a unified chat API, indexes knowledge sources into a hybrid vector + full-text store, and runs a LangGraph-based decision council. We need a coherent, minimal stack that supports async I/O, OAuth-connected external sources, structured agent output, relational scoping (user/project), and retrieval quality at MVP scale — without coupling to sibling projects or over-provisioning infrastructure.

## Decision

### Backend framework: FastAPI

Use **FastAPI** as the backend framework.

**Rationale:**

- Native async support fits WebSocket streaming for chat and concurrent retrieval calls.
- Pydantic integration gives first-class request/response validation and aligns with the structured schemas the council produces (`PersonaOpinion`, `CouncilDecision`).
- Mature ecosystem for Postgres, auth middleware, and OpenAPI documentation.
- Lightweight enough for a single-service MVP; no need for a heavier framework.

### Vector store: pgvector + Postgres full-text search

Use **pgvector** for vector similarity search and **Postgres built-in full-text search** (tsvector/tsquery) for keyword retrieval, both in the same Postgres instance.

**Rationale:**

- MVP scale does not justify a dedicated vector database (Pinecone, Weaviate, etc.). Operational complexity and cost outweigh benefits at this stage.
- Relational joins between chunks, knowledge sources, connections, users, and projects are first-class — scoping retrieval by `user_id` / `project_id` is a `WHERE` clause, not a separate filter layer.
- Hybrid search (vector + keyword) in one database simplifies deployment (one connection pool, one backup strategy).
- pgvector performance is sufficient for single-user / single-project v1 workloads.

**Rejected alternatives:**

- Dedicated vector DBs — added infra, no relational joins, overkill for v1.
- SQLite + local embeddings — no production path to Cloud Run + managed Postgres.

### Embedding model: Voyage `voyage-context-4`

Use **Voyage AI's `voyage-context-4`** for contextual chunk embeddings at index and query time.

**Rationale:**

- Contextual embeddings (embedding a chunk in the context of its parent document) improve retrieval quality over naive chunk-only embeddings, especially for code and structured docs.
- Anthropic recommends Voyage as their embeddings partner; keeping the embedding provider aligned with the LLM provider reduces integration friction.
- Voyage offers a **free tier** sufficient for MVP development and early usage.
- A code-specific model (e.g. `voyage-code-3`) remains available if retrieval quality on code chunks proves insufficient — swap is a config change, not an architecture change.

### Why EBS's local `all-MiniLM-L6-v2` was NOT reused

The sibling project EBS (Enterprise Brain Stack) uses a locally hosted `all-MiniLM-L6-v2` sentence-transformer for embeddings. We evaluated reusing that approach in domAIn and rejected it:

| Factor | EBS local MiniLM | Voyage `voyage-context-4` |
|--------|------------------|---------------------------|
| Cost | "Free" (local compute) | Free tier covers MVP |
| Quality | General-purpose, no document context | Contextual embeddings, higher retrieval quality |
| Ops | Model download, GPU/CPU sizing, container image bloat | API call, no local model management |
| Coupling | Shared code/dependency with EBS | Independent, no cross-repo coupling |

The original cost-saving rationale for local MiniLM **does not hold** once Voyage's free tier is accounted for. The quality tradeoff (non-contextual, smaller model) is not worth saving an API dependency that is free at MVP scale. domAIn reimplements the retrieval *approach* (RRF fusion, coverage check) from EBS but does not share embedding infrastructure.

### LLM abstraction: `init_chat_model` from LangChain

Use **`init_chat_model`** from LangChain as the single LLM abstraction point.

**Rationale:**

- One config value (`model_provider`, `model_name`) swaps the underlying LLM (Claude via Anthropic today, OpenAI or others tomorrow).
- LangChain is already a dependency for LangGraph; `init_chat_model` is the recommended unified entry point.
- Avoids scattering provider-specific client initialization across the supervisor, persona nodes, and the synthesis chair.

**Current default:** `anthropic:claude-sonnet-5`.

### Retrieval fusion: RRF + coverage check

Use **Reciprocal Rank Fusion (RRF)** to merge vector and full-text search result sets, followed by a **coverage check** that verifies retrieved chunks collectively cover the query intent.

**Rationale:**

- RRF is rank-based, not score-based, so it transfers cleanly across different retrieval backends (vector scores vs. ts_rank scores are not directly comparable).
- The same fusion approach is used in EBS's knowledge layer, reimplemented fresh in this repo — no shared/coupled code, but proven pattern.
- Coverage check catches cases where top-ranked chunks are individually relevant but collectively miss part of the query (e.g. a question spanning two doc sections).

**Implementation sketch:**

1. Run vector search and full-text search in parallel.
2. Merge with RRF: `score(d) = Σ 1 / (k + rank_i(d))` where `k` is a constant (typically 60).
3. Coverage check: prompt the LLM (or a lightweight classifier) to assess whether the top-N fused results adequately cover the query. If not, expand retrieval (increase N, relax filters) and re-fuse.

### Chunking strategy

Use a **simple default chunking strategy** for v1:

- Split on paragraph/section boundaries where possible (markdown headers, blank lines).
- Target chunk size: ~512 tokens with ~50-token overlap.
- Store chunk metadata: source document ID, chunk index, parent heading hierarchy.

**Rationale:**

- Fancy chunking (semantic splitting, code-aware AST parsing) adds complexity without proven benefit at MVP scale where knowledge sources are relatively small (ADRs, business docs, modest codebases).
- Simple chunking is easy to debug and replace. If retrieval quality is poor on code files, code-aware chunking becomes a dated appendix to this section.

### OAuth: hand-rolled, not a third-party platform

Use **hand-rolled OAuth** for external provider connections — a GitHub OAuth App and a Linear OAuth App, implemented with **authlib**.

**Rationale:**

- Phase 1 connects exactly two static providers (GitHub for repo indexing and doc write-back; Linear for roadmap read/write). A third-party OAuth platform (Nango, Composio) adds another service, another failure mode, and another bill for infrastructure that two static OAuth flows do not justify.
- authlib is a mature Python library that handles the OAuth 2.0 dance (authorization URL, callback, token exchange, refresh) without a hosted intermediary.
- Tokens are stored on the `Connection` entity (see ADR 0003) and refreshed by the backend; the frontend never sees refresh tokens.

**Rejected alternatives:**

- **Nango** — excellent for many SaaS integrations, but adds a hosted sync layer and operational dependency for two providers.
- **Composio** — similar tradeoff; tool/action abstractions are useful at scale but overkill when we need raw GitHub and Linear API access anyway.

**Scopes (initial):**

| Provider | Scopes | Purpose |
|----------|--------|---------|
| GitHub | `repo`, `read:user` | Index repo contents; open PRs for doc write-back |
| Linear | `read`, `write` | Read roadmap issues; update roadmap items on write-back |

Manual click-through verification of the OAuth flow is required after deploy (see Testing strategy below).

### Write-back mechanics

The council and agents write knowledge-layer updates through external systems, never directly to the database:

| Target | Mechanism | Credentials |
|--------|-----------|-------------|
| ADRs, PRD, business docs | **GitHub Pull Request** against this repo | User's GitHub `Connection` OAuth token |
| Roadmap items | **Linear issue/comment update** | User's Linear `Connection` OAuth token |

Only merged PR content becomes current knowledge-layer truth. Linear updates are informational (roadmap status, links) and do not flow back into the indexed knowledge layer automatically.

### Testing strategy

| Layer | What | How |
|-------|------|-----|
| Unit tests | Pure logic: RRF merge, coverage check, `can_access()` | pytest, no I/O |
| Integration tests | I/O boundaries: ingestion pipeline, write-back handlers | Test Postgres + pgvector instance; mocked GitHub/Linear API clients |
| Router eval | Intent classifier accuracy | Small labeled dataset (~50–100 examples) for supervisor routing labels |
| Persona/council output | **Not tested in Phase 1** | Qualitative eval is Phase 2's pipeline; asserting persona phrasing in CI is brittle and low signal |
| OAuth flow | End-to-end provider connection | Manual click-through verification after deploy to Cloud Run |

**Rationale:** Unit tests protect algorithms that must be deterministic. Integration tests protect the boundaries where bugs cause data loss or auth leaks. The router eval is cheap and high signal because misrouting sends a greeting to three persona LLM calls. Persona output quality is explicitly deferred to Phase 2.

### CI/CD

Use **GitHub Actions**.

| Trigger | Steps |
|---------|-------|
| Pull request | Lint, type-check, unit tests, integration tests |
| Merge to `main` | Build container image, push to registry, deploy to Cloud Run |

No separate staging environment for v1. PR CI is the quality gate; `main` is production.

## Consequences

- Single Postgres instance handles relational data, vectors, and full-text — simple deployment, one backup.
- Voyage API dependency is acceptable at MVP scale (free tier); monitor usage as sources grow.
- RRF fusion is backend-agnostic — if we ever migrate off pgvector, the fusion layer survives unchanged.
- Simple chunking may need upgrading for large codebases; the living-document format makes that a low-friction appendix.
- Hand-rolled OAuth means we own token refresh and provider API changes, but avoid a third-party dependency for two providers.
- Write-back via PR enforces human review on all source-of-truth changes, consistent with the project's docs-as-code philosophy.
- No staging environment means deploy discipline matters; PR CI must be trustworthy.

## Authentication model

Date: 2026-09-23

### API key auth for HTTP routes

Pass 1 shipped API-key authentication without a formal ADR. HTTP requests authenticate via an `X-API-Key` header. `AuthMiddleware` (Starlette `BaseHTTPMiddleware`) validates the key on every protected HTTP route by calling `validate_api_key()`, which SHA-256-hashes the presented key, looks up the matching `api_keys` row, and resolves an `ActorContext` (`user_id`, optional `project_id`). Missing or invalid keys return `401`.

Public paths bypass auth and receive a default `ActorContext` using `default_user_id`: `/health`, `/ready`, OpenAPI docs, and all `/oauth/*` routes.

A bootstrap API key is inserted on application startup from `BOOTSTRAP_API_KEY` when no matching hash exists in the database.

### WebSocket exception

`BaseHTTPMiddleware` does **not** run for WebSocket connections. The unified chat WebSocket endpoint (`/chat/ws`) therefore performs **manual** API-key validation on connect (query parameter `api_key`), reusing the same `validate_api_key()` function and `ActorContext` resolution as HTTP routes. Connections without a valid key are rejected before `accept()`.

**Rationale:** Reusing `validate_api_key()` keeps one identity model across HTTP and WebSocket. Manual WS validation is required because middleware cannot protect the upgrade handshake.

## Changelog

| Date | Change |
|------|--------|
| 2026-09-22 | Initial decisions: FastAPI, pgvector, Voyage, LangChain, RRF, simple chunking, hand-rolled OAuth, write-back via GitHub PR + Linear, testing strategy, CI/CD. |
| 2026-09-23 | Authentication model: API-key HTTP auth (`AuthMiddleware`, `validate_api_key`, `ActorContext`) and WebSocket manual validation exception. |
