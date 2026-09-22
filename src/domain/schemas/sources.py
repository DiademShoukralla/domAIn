from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from domain.db.models import SourceStatus, SourceType


class KnowledgeSourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    source_type: SourceType
    external_ref: str = Field(min_length=1, max_length=512)
    connection_id: UUID
    project_id: UUID | None = None


class KnowledgeSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID | None
    project_id: UUID | None
    source_type: SourceType
    external_ref: str
    connection_id: UUID
    name: str
    status: SourceStatus
    status_message: str | None
    last_indexed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class KnowledgeSourceListResponse(BaseModel):
    sources: list[KnowledgeSourceRead]
