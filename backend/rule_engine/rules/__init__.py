from backend.rule_engine.rules.architecture import ARCHITECTURE_RULES
from backend.rule_engine.rules.components import COMPONENT_RULES
from backend.rule_engine.rules.performance import PERFORMANCE_RULES
from backend.rule_engine.rules.security import SECURITY_RULES

DEFAULT_RULES = [
    *SECURITY_RULES,
    *PERFORMANCE_RULES,
    *COMPONENT_RULES,
    *ARCHITECTURE_RULES,
]

__all__ = [
    "ARCHITECTURE_RULES",
    "COMPONENT_RULES",
    "DEFAULT_RULES",
    "PERFORMANCE_RULES",
    "SECURITY_RULES",
]
