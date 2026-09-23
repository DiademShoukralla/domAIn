from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from domain.llm.factory import get_council_chair_model
from domain.schemas.common import CouncilDecision, PersonaOpinion, Verdict

CHAIR_SYSTEM_PROMPT = """You are the chair of a decision council. You receive three persona opinions
(UX/end-user, developer experience, business/product) on a strategic question.

Synthesize them into one overall recommendation. Write the synthesis in third person or imperative
voice — never first person. Weigh areas of agreement and disagreement. Choose an overall verdict
(approve, request_changes, or comment) that reflects a reasoned judgment, not a mechanical rule."""


class ChairOutput(BaseModel):
    overall_verdict: Verdict
    synthesis: str


def _format_opinions(opinions: list[PersonaOpinion]) -> str:
    sections: list[str] = []
    for opinion in opinions:
        sections.append(
            f"Persona: {opinion.persona}\n"
            f"Verdict: {opinion.verdict.value}\n"
            f"Reasoning: {opinion.reasoning}"
        )
    return "\n\n".join(sections)


async def synthesize_decision(persona_opinions: list[PersonaOpinion]) -> CouncilDecision:
    model = get_council_chair_model().with_structured_output(ChairOutput)
    output = await model.ainvoke(
        [
            SystemMessage(content=CHAIR_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    "Persona opinions:\n\n"
                    f"{_format_opinions(persona_opinions)}\n\n"
                    "Provide the overall verdict and synthesis:"
                )
            ),
        ]
    )
    if not isinstance(output, ChairOutput):
        output = ChairOutput.model_validate(output)

    return CouncilDecision(
        persona_opinions=persona_opinions,
        overall_verdict=output.overall_verdict,
        synthesis=output.synthesis,
    )
