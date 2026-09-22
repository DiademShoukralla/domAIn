from uuid import UUID

from pydantic import BaseModel, Field


class RetrievalRequest(BaseModel):
    query: str = Field(min_length=1)
    project_id: UUID | None = None
    top_k: int | None = Field(default=None, ge=1, le=50)


class RetrievedChunk(BaseModel):
    chunk_id: UUID
    knowledge_source_id: UUID
    document_id: str
    chunk_index: int
    content: str
    heading_hierarchy: list[str]
    rrf_score: float
    vector_rank: int | None = None
    keyword_rank: int | None = None


class RetrievalResponse(BaseModel):
    query: str
    chunks: list[RetrievedChunk]
    coverage_sufficient: bool
    coverage_score: float
    expanded: bool = False
