# Agent instructions

You are working on **domAIn**, a multi-agent decision council backed by a hybrid RAG knowledge layer. Before writing or modifying any application code, read the architecture and product documents below. They contain the reasoning behind every significant decision — not just the conclusions.

## Required reading (in order)

1. **[ADR 0001: Record architecture decisions](docs/adr/0001-record-architecture-decisions.md)** — how ADRs work in this repo.
2. **[ADR 0002: Tech stack](docs/adr/0002-tech-stack.md)** — FastAPI, pgvector, Voyage embeddings, LangChain, RRF retrieval, chunking, write-back mechanics. This is a living document; check the changelog for recent additions.
3. **[ADR 0003: Schemas and synthesis](docs/adr/0003-schemas-and-synthesis.md)** — `ReviewRequest`, `PersonaOpinion`, `CouncilDecision`, verdict vocabulary, orchestrator-worker pattern, LLM-based chair synthesis.
4. **[ADR 0004: Permissions](docs/adr/0004-permissions.md)** — nullable `user_id`/`project_id` scoping, `can_access()` function, why no Permissions table for v1.
5. **[PRD: Phase 1 MVP](docs/business/prd-phase1-mvp.md)** — MVP scope, system topology, user flows, acceptance criteria.

## Rules

- **Do not contradict ADRs.** If your task requires a decision that conflicts with an ADR, propose an ADR amendment (append to the relevant living document or create a new ADR) and get it reviewed before implementing.
- **`user_id` comes from auth context, never the request body.** See ADR 0003.
- **All access checks go through `can_access()`.** See ADR 0004.
- **Verdict vocabulary is `approve` / `request_changes` / `comment`.** See ADR 0003.
- **Write-back to source of truth happens via GitHub PR**, not direct writes. See ADR 0002.
- **Docs-as-code:** business docs live in `docs/business/`, ADRs in `docs/adr/`. Updates go through PR.

## Project structure (expected)

```
docs/
  adr/           # Architecture Decision Records
  business/      # PRD, requirements, product context
AGENTS.md        # This file
```

Application code will be added in subsequent passes. When it lands, follow the conventions established in the ADRs above.
