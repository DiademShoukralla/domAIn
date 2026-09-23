import operator
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Send

from domain.council.chair import synthesize_decision
from domain.council.personas import PERSONA_IDS, run_persona
from domain.db.session import async_session_factory
from domain.schemas.common import ActorContext, CouncilDecision, PersonaOpinion, ReviewRequest


class CouncilState(TypedDict):
    request: ReviewRequest
    actor: ActorContext
    persona_opinions: Annotated[list[PersonaOpinion], operator.add]
    decision: CouncilDecision | None


class PersonaWorkerState(TypedDict):
    request: ReviewRequest
    actor: ActorContext
    persona: str


def dispatch_personas(state: CouncilState) -> list[Send]:
    return [
        Send(
            "persona",
            {
                "request": state["request"],
                "actor": state["actor"],
                "persona": persona,
            },
        )
        for persona in PERSONA_IDS
    ]


async def persona_node(state: PersonaWorkerState) -> dict[str, list[PersonaOpinion]]:
    async with async_session_factory() as db:
        opinion = await run_persona(
            persona=state["persona"],
            request=state["request"],
            actor=state["actor"],
            db=db,
        )
    return {"persona_opinions": [opinion]}


async def chair_node(state: CouncilState) -> dict[str, CouncilDecision]:
    decision = await synthesize_decision(state["persona_opinions"])
    return {"decision": decision}


def build_council_graph() -> CompiledStateGraph[CouncilState, Any, CouncilState, CouncilState]:
    graph = StateGraph(CouncilState)
    graph.add_node("persona", persona_node)
    graph.add_node("chair", chair_node)
    graph.add_conditional_edges(START, dispatch_personas, ["persona"])
    graph.add_edge("persona", "chair")
    graph.add_edge("chair", END)
    return graph.compile()


council_graph: CompiledStateGraph[CouncilState, Any, CouncilState, CouncilState] = (
    build_council_graph()
)
