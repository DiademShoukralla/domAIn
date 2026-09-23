import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from sqlalchemy.ext.asyncio import AsyncSession

from domain.council.chair import synthesize_decision
from domain.council.personas import PERSONA_IDS, run_persona
from domain.schemas.common import ActorContext, CouncilDecision, PersonaOpinion, ReviewRequest


class CouncilState(TypedDict):
    request: ReviewRequest
    actor: ActorContext
    db: AsyncSession
    persona_opinions: Annotated[list[PersonaOpinion], operator.add]
    decision: CouncilDecision | None


class PersonaWorkerState(TypedDict):
    request: ReviewRequest
    actor: ActorContext
    db: AsyncSession
    persona: str


def dispatch_personas(state: CouncilState) -> list[Send]:
    return [
        Send(
            "persona",
            {
                "request": state["request"],
                "actor": state["actor"],
                "db": state["db"],
                "persona": persona,
            },
        )
        for persona in PERSONA_IDS
    ]


async def persona_node(state: PersonaWorkerState) -> dict[str, list[PersonaOpinion]]:
    opinion = await run_persona(
        persona=state["persona"],
        request=state["request"],
        actor=state["actor"],
        db=state["db"],
    )
    return {"persona_opinions": [opinion]}


async def chair_node(state: CouncilState) -> dict[str, CouncilDecision]:
    decision = await synthesize_decision(state["persona_opinions"])
    return {"decision": decision}


def build_council_graph():
    graph = StateGraph(CouncilState)
    graph.add_node("persona", persona_node)
    graph.add_node("chair", chair_node)
    graph.add_conditional_edges(START, dispatch_personas, ["persona"])
    graph.add_edge("persona", "chair")
    graph.add_edge("chair", END)
    return graph.compile()


council_graph = build_council_graph()
