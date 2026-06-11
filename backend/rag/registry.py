import json
import os
import re
from pathlib import Path
from typing import Any

from backend.rag.knowledge_base import RAG_DIR

RAG_DIR = Path(__file__).resolve().parent
CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
SEVERITY_OVERRIDES_FILE = CONFIG_DIR / "severity_overrides.json"


def _parse_rag_field(value: str) -> str:
    return value.strip().replace("\n", " ").replace("\r", "")


def _parse_rag_document(content: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    field_pattern = re.compile(r"^\*\*(\w+):\*\*\s*(.*)", re.MULTILINE)
    header_pattern = re.compile(r"^##\s+(\S+):\s*(.*)", re.MULTILINE)
    sections = re.split(r"\n---\n|\n#\s", "\n" + content)
    for section in sections:
        header_match = header_pattern.search(section)
        fields: dict[str, str] = {}
        if header_match:
            rule_id = header_match.group(1).strip()
            fields["rule_id"] = rule_id
            title = header_match.group(2).strip()
            if title:
                fields["title"] = title
        field_matches = field_pattern.findall(section)
        for key, raw_value in field_matches:
            fields[key] = _parse_rag_field(raw_value)
        if "rule_id" in fields and len(fields) > 1:
            entries.append(fields)
    return entries


def _load_all_rag_entries() -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    category_dirs = [
        "security",
        "performance",
        "maintainability",
        "architecture",
        "limitations",
    ]
    for category in category_dirs:
        category_path = RAG_DIR / category
        if not category_path.is_dir():
            continue
        for md_file in sorted(category_path.glob("*.md")):
            content = md_file.read_text(encoding="utf-8")
            entries.extend(_parse_rag_document(content))
    return entries


def _build_registry(
    entries: list[dict[str, str]],
) -> dict[str, dict[str, str]]:
    registry: dict[str, dict[str, str]] = {}
    for entry in entries:
        rule_id = entry.get("rule_id", "")
        if rule_id:
            registry[rule_id] = entry
    return registry


_ALL_ENTRIES = _load_all_rag_entries()
RAG_RULE_REGISTRY: dict[str, dict[str, str]] = _build_registry(_ALL_ENTRIES)


CLASSIFICATION_CONFIG_FILE = CONFIG_DIR / "classification_config.json"


def _load_classification_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or CLASSIFICATION_CONFIG_FILE
    if config_path.is_file():
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    return {}


_CLASSIFICATION_CONFIG = _load_classification_config()

SEVERITY_KEYWORDS: list[tuple[str, str]] = [
    (item["keyword"], item["severity"])
    for item in _CLASSIFICATION_CONFIG.get("severity_keywords", [])
]

CATEGORY_MAP: dict[str, str] = dict(
    _CLASSIFICATION_CONFIG.get("category_map", {})
)

SEVERITY_DEFAULT = _CLASSIFICATION_CONFIG.get("severity_default", "informational")
CATEGORY_DEFAULT = _CLASSIFICATION_CONFIG.get("category_default", "unknown")


def _load_severity_overrides() -> dict[str, dict[str, str]]:
    try:
        if SEVERITY_OVERRIDES_FILE.is_file():
            with open(SEVERITY_OVERRIDES_FILE, encoding="utf-8") as f:
                data = json.load(f)
            overrides = data.get("overrides", {})
            if isinstance(overrides, dict):
                return overrides
        return {}
    except Exception:
        return {}


CLIENT_SEVERITY_OVERRIDES = _load_severity_overrides()


def apply_client_overrides(rule_id: str, classification: str, client_id: str | None = None) -> str:
    if client_id and client_id in CLIENT_SEVERITY_OVERRIDES:
        client_overrides = CLIENT_SEVERITY_OVERRIDES[client_id]
        if rule_id in client_overrides:
            return client_overrides[rule_id]
    return classification


def lookup_rule(rule_id: str) -> dict[str, str] | None:
    return RAG_RULE_REGISTRY.get(rule_id)


def get_registered_rule_ids() -> set[str]:
    return set(RAG_RULE_REGISTRY.keys())


def extract_severity(classification: str) -> str:
    if not classification:
        return SEVERITY_DEFAULT
    classification_upper = classification.upper()
    for keyword, severity in SEVERITY_KEYWORDS:
        if keyword.upper() in classification_upper:
            return severity
    return SEVERITY_DEFAULT


def resolve_severity(rule_id: str, client_id: str | None = None) -> str:
    entry = lookup_rule(rule_id)
    if not entry:
        return SEVERITY_DEFAULT
    classification = entry.get("classification") or ""
    classification = apply_client_overrides(rule_id, classification, client_id)
    return extract_severity(classification)


def resolve_category(rule_id: str) -> str:
    entry = lookup_rule(rule_id)
    if not entry:
        return CATEGORY_DEFAULT
    raw = (entry.get("category") or "").lower().strip()
    return CATEGORY_MAP.get(raw, raw)


def resolve_rag_fields(rule_id: str, client_id: str | None = None) -> dict[str, str]:
    entry = lookup_rule(rule_id)
    if not entry:
        return {
            "severity": SEVERITY_DEFAULT,
            "category": CATEGORY_DEFAULT,
            "impact": "",
            "source": "",
            "remediation": "",
        }
    classification = entry.get("classification") or ""
    classification = apply_client_overrides(rule_id, classification, client_id)
    raw_category = (entry.get("category") or "").lower().strip()
    return {
        "severity": extract_severity(classification),
        "category": CATEGORY_MAP.get(raw_category, raw_category),
        "impact": entry.get("impact") or "",
        "source": entry.get("source") or "",
        "remediation": entry.get("remediation") or "",
    }
