from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Verdict(StrEnum):
    APPROVE = "approve"
    REQUEST_CHANGES = "request_changes"
    COMMENT = "comment"


class Citation(BaseModel):
    document_id: str
    chunk_index: int
    knowledge_source_id: UUID
    excerpt: str


class ReviewRequest(BaseModel):
    query: str
    project_id: UUID | None = None


class PersonaOpinion(BaseModel):
    persona: str
    verdict: Verdict
    reasoning: str
    citations: list[Citation]


class CouncilDecision(BaseModel):
    persona_opinions: list[PersonaOpinion]
    overall_verdict: Verdict
    synthesis: str


class ActorContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_id: UUID
    project_id: UUID | None = None
