from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from domain.db.models import Provider, SourceType


class AvailableSourceItem(BaseModel):
    source_type: SourceType
    external_ref: str = Field(min_length=1, max_length=512)
    name: str = Field(min_length=1, max_length=255)
    private: bool | None = None
    updated_at: datetime | None = None
    key: str | None = None
    already_added: bool = False
    source_id: UUID | None = None


class AvailableSourcesResponse(BaseModel):
    provider: Provider
    items: list[AvailableSourceItem]
