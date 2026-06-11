import re
from dataclasses import dataclass
from re import Pattern


@dataclass(frozen=True)
class SecurityRule:
    id: str
    title: str
    pattern: Pattern[str]
    description: str


def compile_rule(
    rule_id: str,
    title: str,
    pattern: str,
    description: str,
) -> SecurityRule:
    return SecurityRule(
        id=rule_id,
        title=title,
        pattern=re.compile(pattern, re.IGNORECASE),
        description=description,
    )


DEFAULT_SECURITY_RULES = [
    compile_rule(
        rule_id="SEC-PASSWORD-001",
        title="Hardcoded password detected",
        pattern=r"\b(pass(word)?|pwd)\b[^A-Za-z0-9]{0,8}(value=|=|:)\s*[\"']?([^\"'\s;&<>]{4,})",
        description="Static password-like values were found in Talend metadata.",
    ),
    compile_rule(
        rule_id="SEC-USERNAME-001",
        title="Hardcoded username detected",
        pattern=r"\b(user(name)?|uid)\b[^A-Za-z0-9]{0,8}(value=|=|:)\s*[\"']?([^\"'\s;&<>]{3,})",
        description="Static username-like values were found in Talend metadata.",
    ),
    compile_rule(
        rule_id="SEC-APIKEY-001",
        title="API key detected",
        pattern=r"\b(api[_-]?key|access[_-]?key)\b[^A-Za-z0-9]{0,8}(value=|=|:)\s*[\"']?([A-Za-z0-9_\-]{16,})",
        description="A static API key-like value was found.",
    ),
    compile_rule(
        rule_id="SEC-TOKEN-001",
        title="Token detected",
        pattern=r"\b(token|bearer|secret)\b[^A-Za-z0-9]{0,8}(value=|=|:)\s*[\"']?([A-Za-z0-9_\-.]{16,})",
        description="A static token-like value was found.",
    ),
    compile_rule(
        rule_id="SEC-JDBC-001",
        title="JDBC URL detected",
        pattern=r"jdbc:[A-Za-z0-9:_/@.\-?=&;]+",
        description="A JDBC connection URL was found in Talend metadata.",
    ),
]
