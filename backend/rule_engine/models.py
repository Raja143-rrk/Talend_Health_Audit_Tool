from collections.abc import Callable
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from backend.rag.registry import lookup_rule, resolve_rag_fields
from backend.shared.models import AgentFinding, FindingSeverity


class RuleScope(StrEnum):
    INVENTORY = "inventory"
    JOB = "job"
    COMPONENT = "component"


class RuleCategory(StrEnum):
    SECURITY = "security"
    PERFORMANCE = "performance"
    COMPONENT = "component"
    ARCHITECTURE = "architecture"


RulePredicate = Callable[[dict[str, Any], dict[str, Any]], bool]


class RuleThreshold(BaseModel):
    field: str
    operator: str
    value: int | float


class RuleDefinition(BaseModel):
    id: str
    title: str
    category: RuleCategory
    scope: RuleScope
    severity: FindingSeverity | None = None
    description: str
    remediation: str
    enabled: bool = True
    thresholds: list[RuleThreshold] = Field(default_factory=list)
    predicate: RulePredicate = Field(exclude=True)

    class Config:
        arbitrary_types_allowed = True

    def to_finding(
        self,
        target: dict[str, Any],
        evidence: dict[str, Any] | None = None,
    ) -> AgentFinding:
        target_name = (
            target.get("name")
            or target.get("component_name")
            or target.get("project_name")
            or "inventory"
        )
        rag_fields = resolve_rag_fields(self.id)
        try:
            rag_severity = FindingSeverity(rag_fields["severity"])
        except ValueError:
            rag_severity = self.severity or FindingSeverity.INFORMATIONAL
        rag_category = rag_fields["category"] if rag_fields["category"] != "unknown" else self.category.value
        return AgentFinding(
            id=f"{self.id}-{self._safe_id(str(target_name))}",
            title=self.title,
            job_name=str(target.get("job_name") or target.get("job") or "unknown"),
            component_name=str(target.get("name") or target.get("component") or target.get("component_name") or "unknown"),
            component_type=str(target.get("component_type") or target.get("component_name") or "unknown"),
            category=rag_category,
            severity=rag_severity,
            rule_triggered=self.id,
            description=self.description,
            impact=rag_fields["impact"],
            recommendation=self.remediation,
            source=rag_fields["source"],
            evidence={
                "rule_id": self.id,
                "scope": self.scope.value,
                "target": target_name,
                "thresholds": [threshold.model_dump() for threshold in self.thresholds],
                "remediation": rag_fields["remediation"],
                **(evidence or {}),
            },
        )

    def _safe_id(self, value: str) -> str:
        return "".join(character if character.isalnum() else "-" for character in value).strip("-")


Rule = RuleDefinition
