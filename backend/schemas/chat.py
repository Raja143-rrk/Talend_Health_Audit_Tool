from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class DashboardChatRequest(BaseModel):
    analysis_id: str
    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list)


class DashboardChatAction(BaseModel):
    type: Literal["navigate", "filter", "open_component"]
    label: str
    target: str
    filters: dict[str, Any] = Field(default_factory=dict)


class DashboardChatSource(BaseModel):
    title: str
    source: str
    snippet: str


class DashboardChatResponse(BaseModel):
    analysis_id: str
    answer: str
    actions: list[DashboardChatAction] = Field(default_factory=list)
    sources: list[DashboardChatSource] = Field(default_factory=list)
    matched_counts: dict[str, int] = Field(default_factory=dict)
