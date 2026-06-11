from pydantic import BaseModel, Field


class RagDocument(BaseModel):
    id: str
    source: str
    content: str
    metadata: dict[str, str] = Field(default_factory=dict)


class RagSearchResult(BaseModel):
    document: RagDocument
    score: float | None = None
    rank: int


class RetrievalContext(BaseModel):
    query: str
    results: list[RagSearchResult] = Field(default_factory=list)
    context_text: str
    backend: str = "memory"
