from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from domain.schemas.common import Citation, CouncilDecision
from domain.schemas.writeback import WriteBackProposalOut


class ChatIntent(StrEnum):
    GREETING = "greeting"
    SIMPLE_RETRIEVAL = "simple_retrieval"
    STRATEGIC_SESSION = "strategic_session"
    LINEAR_READ = "linear_read"
    LINEAR_WRITE = "linear_write"


class ResponseKind(StrEnum):
    DIRECT_ANSWER = "direct_answer"
    COUNCIL_RESULT = "council_result"
    STUB_NOT_IMPLEMENTED = "stub_not_implemented"


class ChatRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessageIn(BaseModel):
    session_id: UUID
    content: str = Field(min_length=1)


class ChatMessageOut(BaseModel):
    id: UUID
    session_id: UUID
    role: ChatRole
    content: str
    classified_intent: ChatIntent | None = None
    response_kind: ResponseKind | None = None
    citations: list[Citation] = Field(default_factory=list)
    council_decision: CouncilDecision | None = None
    write_back_proposal: WriteBackProposalOut | None = None
    created_at: datetime


class RoutedChatResponse(BaseModel):
    session_id: UUID
    content: str
    classified_intent: ChatIntent
    response_kind: ResponseKind
    citations: list[Citation] = Field(default_factory=list)
    council_decision: CouncilDecision | None = None


class ChatResponse(RoutedChatResponse):
    id: UUID


class ChatStatusUpdate(BaseModel):
    session_id: UUID
    scope: Literal["supervisor", "persona"]
    persona: str | None = None
    status: str


class ChatHistoryResponse(BaseModel):
    session_id: UUID
    messages: list[ChatMessageOut]
