from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from domain.db.models import Provider


class ConnectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    provider: Provider
    external_account_id: str
    external_account_name: str
    created_at: datetime
    updated_at: datetime


class ConnectionListResponse(BaseModel):
    connections: list[ConnectionRead]
