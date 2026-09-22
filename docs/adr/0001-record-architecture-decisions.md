# 1. Record architecture decisions

Date: 2026-09-22

## Status

Accepted

## Context

domAIn is a multi-agent decision system whose agents query a shared knowledge layer spanning codebase, business documentation, and architectural decisions. We need a lightweight, version-controlled way to capture significant technical and structural choices so agents and humans share the same durable record of why things are the way they are.

## Decision

We will use **Architecture Decision Records (ADRs)**, as described by [Michael Nygard](http://thinkrelevance.com/blog/2008/11/15/documenting-architecture-decisions).

ADRs live in `/docs/adr/` and follow the [adr-tools](https://github.com/npryce/adr-tools) numbering convention:

- One file per decision, named `NNNN-short-title.md` (e.g. `0002-use-langgraph.md`).
- Numbers are sequential and never reused.
- Superseded ADRs are marked in their **Status** field; the replacement ADR references the one it supersedes.

Each ADR uses this structure:

1. **Title** — short noun phrase
2. **Status** — Proposed | Accepted | Deprecated | Superseded
3. **Context** — forces at play and the issue motivating the decision
4. **Decision** — the change being proposed or enacted
5. **Consequences** — what becomes easier or harder as a result

Updates to ADRs are made via pull request. Direct commits to `main` are not the source of truth for architectural decisions — only merged PRs are.

## Consequences

- Architectural rationale is searchable, diffable, and available to the knowledge layer alongside code and business docs.
- Agents and humans can cite specific ADRs when reasoning about proposals.
- A small amount of ceremony per decision (file creation, PR review) in exchange for durable, reviewable decision history.
