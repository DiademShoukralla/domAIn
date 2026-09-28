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

Install [uv](https://docs.astral.sh/uv/), then sync dependencies from the lockfile:

```bash
uv sync --extra dev
pre-commit install
docker compose up -d db
uv run alembic upgrade head
uv run uvicorn domain.main:app --reload --app-dir src
```

### Dependencies

- `pyproject.toml` declares version ranges; `uv.lock` pins exact versions for CI, Docker, and local dev.
- **Add a dependency:** edit `pyproject.toml`, then `uv lock` and commit both files.
- **Upgrade one package deliberately:** `uv lock --upgrade-package <name>` (then run tests and commit `uv.lock`).
- CI runs `uv lock --check` and installs with `uv sync --frozen`, so a stale lockfile fails the build.

`pre-commit install` is a required one-time setup step. It installs a git hook that runs ruff (lint + format) and mypy on each commit, blocking commits that introduce lint or type errors.

Run tests:

```bash
uv run pytest
```

## Production env on the droplet

Production secrets live in `.env.production`, generated from `.env.production.example` via `deploy/generate-env.sh`. Deploy runs `deploy/generate-env.sh --check` before sourcing the env file; if template keys are missing, deploy aborts with instructions to run `--missing`.

### Adding a new env var

1. Add the variable (with a comment) to both `.env.production.example` and `.env.example`.
2. Merge the change to `main`.
3. On the droplet: `cd ~/domAIn && git pull && bash deploy/generate-env.sh --missing`.
4. Deploy (GitHub Actions or manual `deploy/deploy.sh`).

## Architecture docs

See `AGENTS.md` and `docs/adr/` for full architecture and product requirements.
