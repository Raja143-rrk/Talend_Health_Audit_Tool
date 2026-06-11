from enum import StrEnum

from pydantic import BaseModel, Field


class RecommendationCategory(StrEnum):
    REMEDIATION = "remediation"
    OPTIMIZATION = "optimization"
    BEST_PRACTICE = "best_practice"
    MODERNIZATION = "modernization"
    CLEANUP = "cleanup"


class CategorizedSuggestion(BaseModel):
    id: str
    category: RecommendationCategory
    title: str
    priority: str
    summary: str
    rationale: str
    action_items: list[str] = Field(default_factory=list)
    expected_impact: str


class RecommendationSummary(BaseModel):
    executive_summary: str
    risk_posture: str
    suggestions: list[CategorizedSuggestion] = Field(default_factory=list)
