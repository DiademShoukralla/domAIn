from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from domain.llm.factory import get_supervisor_model
from domain.schemas.chat import ChatIntent

CLASSIFIER_SYSTEM_PROMPT = """You are the domAIn chat intent classifier. Classify each user message into exactly one intent:

- greeting: small talk, hellos, thanks, or other conversational openers with no knowledge lookup
- simple_retrieval: factual questions answerable from indexed knowledge (docs, ADRs, codebase, roadmap context)
- strategic_session: review-worthy or strategic decisions needing multi-perspective council debate
- linear_read: requests to read, fetch, or display Linear issues, tickets, or roadmap items
- linear_write: requests to update, create, comment on, or change Linear issues or roadmap items

Return only the intent label. When unsure between simple_retrieval and strategic_session, prefer simple_retrieval for factual lookups and strategic_session for proposals, reviews, tradeoffs, or "should we" decisions."""


class IntentClassification(BaseModel):
    intent: ChatIntent = Field(description="The classified routing intent for the user message.")


async def classify_intent(message: str) -> ChatIntent:
    model = get_supervisor_model().with_structured_output(IntentClassification)
    result = await model.ainvoke(
        [
            SystemMessage(content=CLASSIFIER_SYSTEM_PROMPT),
            HumanMessage(content=message),
        ]
    )
    if isinstance(result, IntentClassification):
        return result.intent
    return IntentClassification.model_validate(result).intent
