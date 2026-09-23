# domAIn

domAIn is a multi-agent decision system built with LangGraph. Several persona-based agents (UX/end-user, dev experience, business/product) query a shared indexed knowledge layer and collaboratively review proposals and PRs, writing their reasoning back as decisions.

The knowledge layer stores the codebase, business documentation, and Architecture Decision Records (ADRs) as docs-as-code in this repository. Roadmap context is read from Linear. The council writes updates to business docs and ADRs by opening pull requests — never directly — so merged content is always human-reviewed source of truth.

## Pass 1: Knowledge layer foundation

This pass delivers the deployable knowledge layer backend:

- FastAPI service with GitHub App installation auth and Linear OAuth (`authlib`)
- `Connection` and `KnowledgeSource` entities with CRUD
- Ingestion pipeline (chunk → Voyage `voyage-context-4` embed → pgvector + Postgres FTS)
- Shared hybrid retrieval (`vector + keyword → RRF → coverage check`)
- Permissions via `can_access()`
- Docker deployment to shared droplet (GHCR + compose) with GitHub Actions CI/CD

## Quick start

```bash
cp .env.example .env
# Fill in TOKEN_ENCRYPTION_KEY, OAuth client credentials, and VOYAGE_API_KEY

docker compose up --build
```

API docs: `http://localhost:8000/docs`

Authenticate API requests with header `X-API-Key: <BOOTSTRAP_API_KEY>`.

OAuth connect:

- GitHub: `GET /oauth/github/authorize`
- Linear: `GET /oauth/linear/authorize`

## Development

```bash
pip install -e ".[dev]"
docker compose up -d db
alembic upgrade head
uvicorn domain.main:app --reload --app-dir src
```

Run tests:

```bash
pytest
```

## Architecture docs

See `AGENTS.md` and `docs/adr/` for full architecture and product requirements.
