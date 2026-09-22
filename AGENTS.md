# Agent instructions

You are working on **domAIn**, a multi-agent decision council backed by a hybrid RAG knowledge layer. Before writing or modifying any application code, read the architecture and product documents below. They contain the reasoning behind every significant decision — not just the conclusions.

## Required reading (in order)

1. **[ADR 0001: Record architecture decisions](docs/adr/0001-record-architecture-decisions.md)** — how ADRs work in this repo.
2. **[ADR 0002: Tech stack](docs/adr/0002-tech-stack.md)** — FastAPI, pgvector, Voyage embeddings, LangChain, RRF retrieval, chunking, hand-rolled OAuth, testing strategy, CI/CD, write-back mechanics. Living document; check the changelog for recent additions.
3. **[ADR 0003: Schemas and knowledge sources](docs/adr/0003-schemas-and-knowledge-sources.md)** — `ReviewRequest`, `PersonaOpinion`, `CouncilDecision`, verdict vocabulary, `Connection` and `KnowledgeSource` entities, four-state status model.
4. **[ADR 0004: Permissions](docs/adr/0004-permissions.md)** — nullable `user_id`/`project_id` scoping, `can_access()` function, why no Permissions table for v1.
5. **[ADR 0005: Routing and coordination](docs/adr/0005-routing-and-coordination.md)** — supervisor intent router, orchestrator-worker council subgraph, LLM chair synthesis, no user-facing routing toggle.
6. **[PRD: Phase 1 MVP](docs/business/prd-phase1-mvp.md)** — MVP scope, system topology, user flows, acceptance criteria.
7. **[Design system](docs/business/design-system/README.md)** — tokens, components, voice rules. Load `tokens.css` then `components/bundle.css`. Read component cards before building UI.

## Rules

- **Do not contradict ADRs.** If your task requires a decision that conflicts with an ADR, propose an ADR amendment (append to the relevant living document or create a new ADR) and get it reviewed before implementing.
- **`user_id` comes from auth context, never the request body.** See ADR 0003.
- **All access checks go through `can_access()`.** See ADR 0004.
- **Verdict vocabulary is `approve` / `request_changes` / `comment`.** See ADR 0003.
- **Source types are `github_repo` and `linear` only.** No file upload. See ADR 0003.
- **Source status is `pending` / `indexing` / `ready` / `error`.** Four values, no others. See ADR 0003 and design system.
- **Unified chat, no mode selector.** The Composer has no routing toggle. The supervisor classifies intent. See ADR 0005 and design system.
- **Write-back to source of truth happens via GitHub PR**, not direct writes. See ADR 0002.
- **OAuth is hand-rolled via authlib**, not a third-party OAuth platform. See ADR 0002.
- **Docs-as-code:** business docs live in `docs/business/`, ADRs in `docs/adr/`. Updates go through PR.

## Project structure (expected)

```
docs/
  adr/                          # Architecture Decision Records
  business/
    prd-phase1-mvp.md           # Phase 1 product requirements
    design-system/              # CSS tokens, component styles, markup contracts
AGENTS.md                       # This file
```

Application code will be added in subsequent passes. When it lands, follow the conventions established in the ADRs and design system above.
