# 3. Schemas and synthesis pattern

Date: 2026-09-22

## Status

Accepted

## Context

domAIn's council receives a review request, fans out to three persona agents, and returns a structured decision. Every boundary between the API, agents, and client must speak the same types. We also need a coordination pattern that produces nuanced synthesis from disagreeing personas without over-engineering dynamic routing for v1.

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
| `user_id` | **Auth context only** | Extracted from the authenticated session or API key. Never accepted in the request body. |

**Rationale:** `user_id` in the body would be a security footgun (caller could impersonate another user). Auth middleware resolves identity once; all downstream nodes receive it via graph state, not user input.

#### `PersonaOpinion`

```python
class PersonaOpinion(BaseModel):
    persona: str          # e.g. "ux", "dev_experience", "business"
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

**Rationale:** These three values mirror **GitHub's PR review states** (`APPROVE`, `REQUEST_CHANGES`, `COMMENT`). Since the council's write-back path opens GitHub PRs, aligning verdict vocabulary means a `CouncilDecision` maps directly to a GitHub review action without translation logic. Using GitHub-native terms also makes the output intuitive for developers who are the primary v1 users.

**Rejected alternatives:**

- Custom scales (`pass` / `fail` / `needs_discussion`) — requires mapping layer to GitHub and loses semantic precision.
- Numeric scores — meaningless for PR review write-back and encourage false precision.

### Synthesis and coordination pattern

#### Orchestrator-worker (fixed fan-out)

```
ReviewRequest
      │
      ▼
  Orchestrator ──┬──► UX Persona        ──► PersonaOpinion
                 ├──► Dev Experience   ──► PersonaOpinion
                 └──► Business/Product ──► PersonaOpinion
                              │
                              ▼
                     Chair (synthesis) ──► CouncilDecision
```

- The orchestrator dispatches the same `ReviewRequest` to **exactly three persona nodes** in parallel.
- This is a fixed fan-out, **not a supervisor pattern**. No node decides which other nodes to invoke or skip.
- Each persona independently queries the knowledge layer and returns a `PersonaOpinion`.

**Rationale:**

- v1 always needs all three perspectives. Dynamic routing (skip a persona, re-run one) adds graph complexity with no v1 use case.
- Fixed fan-out is trivially parallelizable and easy to test (three independent LLM calls + one synthesis call).
- LangGraph's `Send` API or a simple fan-out node handles this without a supervisor agent.

#### LLM-based synthesis (chair)

The chair node receives all three `PersonaOpinion` objects and uses an **LLM call** to produce `overall_verdict` and `synthesis`.

**Rationale:**

- The point of three personas is **nuanced disagreement** — a UX persona may `request_changes` while the business persona `approves`. A deterministic rule (e.g. `MIN(verdict_severity)`) would collapse that nuance into a single label and discard the reasoning that makes the council valuable.
- The chair prompt instructs the LLM to weigh each opinion, identify consensus and conflict, and produce a reasoned overall verdict with a narrative synthesis.
- The chair also queries the knowledge layer if it needs additional context to resolve a disagreement.

**Rejected alternative:**

- Rule-based aggregation (`worst verdict wins`, majority vote) — fast but produces shallow output that ignores reasoning quality and citation strength.

#### Supervisor migration path

The current orchestrator-worker pattern does **not** require a supervisor. A supervisor becomes warranted only when:

- Personas gain **tool-calling** ability (e.g. a persona can request a re-index or query a specific file) — this is compatible with orchestrator-worker; tools are local to each persona node.
- **Genuine dynamic routing** is needed: skipping a persona for out-of-scope reviews, re-running a persona after the chair identifies a gap, or adding ad-hoc specialist personas. This would migrate to a LangGraph supervisor/subgraph pattern.

No v1 work should anticipate or pre-build supervisor infrastructure. The fixed fan-out graph is the correct v1 shape.

## Consequences

- Shared Pydantic models enforce contract consistency from API through to LangGraph state.
- `user_id` never in the request body eliminates an entire class of authorization bugs.
- GitHub-aligned verdicts make write-back a thin mapping layer.
- Fixed fan-out keeps the graph simple, testable, and parallelizable.
- LLM synthesis costs one additional LLM call per review but produces meaningfully better output than rule-based aggregation.
- Supervisor migration is a graph refactor, not a schema change — `PersonaOpinion` and `CouncilDecision` survive unchanged.
