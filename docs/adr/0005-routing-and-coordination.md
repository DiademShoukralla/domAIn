# 5. Routing and coordination pattern

Date: 2026-09-22

## Status

Accepted

## Context

domAIn exposes one unified chat surface — no mode selector in the Composer. The backend must classify user intent and route to the appropriate handler: a direct retrieval answer, a full council review, a greeting, or (stubbed) Linear read/write actions. Within the council path, three fixed personas debate and a chair synthesizes. These are two distinct coordination patterns at different graph levels.

## Decision

### Two-level coordination

domAIn uses **two separate coordination patterns** in a nested graph:

1. **Supervisor** (top-level) — classifies intent and routes to the correct subgraph or handler.
2. **Orchestrator-worker** (nested, council subgraph) — fans out to three fixed personas, then the chair synthesizes.

The supervisor and chair are **separate nodes** with different model tiers and different evaluability. Conflating them would make it impossible to test routing independently from synthesis quality.

### Supervisor (top-level intent router)

The supervisor is the entry node for every chat message. It classifies the user's message into one of five intents and routes accordingly:

| Intent | Handler | Phase 1 status |
|--------|---------|----------------|
| `greeting` | Short conversational reply | Implemented |
| `simple_retrieval` | Hybrid retrieval → single LLM answer with citations | Implemented |
| `strategic_session` | Council subgraph (orchestrator-worker) | Implemented |
| `linear_read` | Fetch/display Linear issue data | Stub |
| `linear_write` | Update Linear issue via write-back | Stub |

```
User message
     │
     ▼
 Supervisor (classify intent)
     │
     ├── greeting ──────────► Conversational reply
     ├── simple_retrieval ──► RAG answer
     ├── strategic_session ─► Council subgraph ──► CouncilDecision
     ├── linear_read ───────► [stub] Not implemented
     └── linear_write ──────► [stub] Not implemented
```

**Rationale:**

- One chat surface means the user never selects a "mode." Intent classification is the only routing mechanism — confirmed in the design system: the Composer has **no routing toggle**.
- Stubs for `linear_read` and `linear_write` reserve graph slots without blocking Phase 1 delivery. The supervisor returns a "not yet available" response for stub intents.
- The supervisor uses a lightweight/fast model tier because classification is a simpler task than persona reasoning or chair synthesis.

**Rejected alternatives:**

- User-facing mode selector (Simple / Council toggle) — adds UI complexity and forces the user to predict which backend path they need. The redesign explicitly removed this.
- Single graph with conditional persona skipping — conflates routing with council coordination; harder to test and evolve independently.

### Orchestrator-worker (council subgraph)

When the supervisor routes to `strategic_session`, the council subgraph runs:

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
- This is a fixed fan-out, not dynamic routing. No node decides which other nodes to invoke or skip.
- Each persona independently queries the knowledge layer and returns a `PersonaOpinion`.

**Rationale:**

- v1 always needs all three perspectives for strategic reviews. Dynamic routing (skip a persona, re-run one) adds graph complexity with no v1 use case.
- Fixed fan-out is trivially parallelizable and easy to test (three independent LLM calls + one synthesis call).
- LangGraph's `Send` API or a simple fan-out node handles this without a supervisor agent inside the subgraph.

### LLM-based synthesis (chair)

The chair node receives all three `PersonaOpinion` objects and uses an **LLM call** to produce `overall_verdict` and `synthesis`.

**Rationale:**

- The point of three personas is **nuanced disagreement** — a UX persona may `request_changes` while the business persona `approves`. A deterministic rule (e.g. `MIN(verdict_severity)`) would collapse that nuance into a single label and discard the reasoning that makes the council valuable.
- The chair prompt instructs the LLM to weigh each opinion, identify consensus and conflict, and produce a reasoned overall verdict with a narrative synthesis.
- The chair uses a higher-capability model tier than the supervisor because synthesis requires weighing conflicting evidence.

**Rejected alternative:**

- Rule-based aggregation (`worst verdict wins`, majority vote) — fast but produces shallow output that ignores reasoning quality and citation strength.

### Supervisor vs. chair: why they are separate

| | Supervisor | Chair |
|---|-----------|-------|
| **Job** | Classify intent, route | Synthesize three opinions |
| **Input** | Raw user message | Three `PersonaOpinion` objects |
| **Output** | Route label | `CouncilDecision` |
| **Model tier** | Fast/lightweight | Capable/thorough |
| **Eval** | Labeled intent classifier eval (~50–100 examples) | Phase 2 qualitative eval |
| **Failure mode** | Wrong route (greeting sent to council) | Shallow or wrong synthesis |

Merging them would couple routing accuracy to synthesis quality in testing and make it impossible to swap model tiers independently.

### Routing is never user-facing

The design system enforces this: the Composer component has **no routing toggle, no mode selector, no "Simple vs. Council" switch.** The user types a message; the supervisor decides the path. Implementation must not add UI controls that bypass or override supervisor routing.

## Chat request/response data contract

Date: 2026-09-23

Pass 2 formalizes the wire contract for the unified chat surface. The supervisor architecture above is unchanged; this section specifies the Pydantic shapes the frontend consumes.

### WebSocket transport

- **Endpoint:** `GET /chat/ws?api_key=<key>` (API key validated manually on connect; see ADR 0002 authentication model).
- **Client → server frame:** `ChatMessageIn` — `{ "session_id": "<uuid>", "content": "<text>" }`.
- **Server → client frame:** `ChatResponse` — see below.
- **History:** `GET /chat/sessions/{session_id}/messages` returns persisted `ChatMessageOut` rows for the authenticated actor.

Messages persist in `chat_messages` (session id, role, content, classified intent, response kind, citations JSON, timestamps) even though the UI presents chat as ephemeral.

### Intent labels (supervisor output)

| Value | Meaning |
|-------|---------|
| `greeting` | Small talk; no retrieval |
| `simple_retrieval` | Factual question answered from the knowledge layer |
| `strategic_session` | Hand off to the council subgraph |
| `linear_read` | Linear fetch intent (stub in Pass 2) |
| `linear_write` | Linear update intent (stub in Pass 2) |

Classifier model: **`claude-haiku-4-5`** (supervisor only; council chair uses a stronger model per the table above).

### Response kind (frontend voice mapping)

| `response_kind` | Handler paths | Design-system voice |
|-----------------|---------------|---------------------|
| `direct_answer` | `greeting`, `simple_retrieval` | `dom-msg--direct` |
| `council_pending_handoff` | `strategic_session` | `dom-msg--pending` |
| `stub_not_implemented` | `linear_read`, `linear_write` | plain text (no variant class) |

`ChatResponse` fields:

```python
class ChatResponse(BaseModel):
    session_id: UUID
    content: str
    classified_intent: ChatIntent
    response_kind: ResponseKind
    citations: list[Citation]  # populated for simple_retrieval
```

`simple_retrieval` responses include `Citation` objects (`document_id`, `chunk_index`, `knowledge_source_id`, `excerpt`) so the UI can render `CodeCitation` blocks.

## Council result wire contract (Pass 3a)

Date: 2026-09-23

Pass 3a replaces the Pass 2 council stub with a completed orchestrator-worker graph. The `strategic_session` path now returns a full `CouncilDecision` instead of a pending handoff.

### `ResponseKind` changes

| Before (Pass 2) | After (Pass 3a) |
|-----------------|-----------------|
| `council_pending_handoff` | **removed** |
| — | `council_result` |

### Updated response-kind → design-system voice mapping

| `response_kind` | Handler paths | Design-system voice |
|-----------------|---------------|---------------------|
| `direct_answer` | `greeting`, `simple_retrieval` | `dom-msg--direct` |
| `council_result` | `strategic_session` (completed council) | `dom-chair-block` (synthesis in `content`; structured `PersonaMessage` + `ChairBlock` from `council_decision`) |
| `stub_not_implemented` | `linear_read`, `linear_write` | plain text (no variant class) |

### `ChatResponse` schema extension

```python
class ChatResponse(BaseModel):
    session_id: UUID
    content: str                              # chair synthesis narrative
    classified_intent: ChatIntent
    response_kind: ResponseKind
    citations: list[Citation] = []            # populated for simple_retrieval
    council_decision: CouncilDecision | None = None  # populated for council_result
```

A completed council response sets `response_kind=council_result` and populates `council_decision` with three `PersonaOpinion` objects plus `overall_verdict` and `synthesis`. The top-level `content` field carries the chair synthesis for clients that render a single message bubble; structured UI renders per-persona opinions and the chair block from `council_decision`.

**Note:** Live status updates during council execution (persona-by-persona progress) are Pass 3b; Pass 3a returns only the final completed frame.

## Consequences

- Unified chat UX with no mode selector simplifies the frontend and matches user mental models ("I ask domAIn a question").
- Two-level coordination keeps routing testable independently from council quality.
- Stub intents reserve graph structure for Phase 1.5 without blocking MVP.
- LLM synthesis costs one additional LLM call per council review but produces meaningfully better output than rule-based aggregation.
- Supervisor and chair model tiers can be tuned independently as usage data arrives.
- The router eval dataset is a Phase 1 deliverable; persona output eval is explicitly Phase 2.
- Chat wire contract (`ChatMessageIn`, `ChatResponse`, `response_kind` voice mapping) is documented in the dated sections above.
- Pass 3a council results expose structured `CouncilDecision` on the wire; frontend renders `PersonaMessage` and `ChairBlock` per design system.
