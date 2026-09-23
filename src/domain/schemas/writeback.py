from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class WriteBackProposalStatus(StrEnum):
    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    EXECUTED = "executed"


class WriteBackPlan(BaseModel):
    needs_doc_update: bool
    doc_target: Literal["existing", "new"] | None = None
    existing_doc_path: str | None = None
    new_doc_slug: str | None = None
    needs_roadmap_item: bool


class WriteBackFeedbackEntry(BaseModel):
    feedback: str
    created_at: datetime


class WriteBackProposalRefine(BaseModel):
    feedback: str = Field(min_length=1)


class WriteBackProposalOut(BaseModel):
    id: UUID
    chat_message_id: UUID
    user_id: UUID
    project_id: UUID | None = None
    plan: WriteBackPlan
    feedback_history: list[WriteBackFeedbackEntry] = Field(default_factory=list)
    status: WriteBackProposalStatus
    created_at: datetime
    updated_at: datetime
    executed_at: datetime | None = None
