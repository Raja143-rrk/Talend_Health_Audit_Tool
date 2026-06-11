# Scoring Configuration Migration Report

## Overview

Migrated scoring framework from hardcoded values to file-based configuration, enabling enterprise governance compliance, client-specific overrides, category-specific weights, and configurable maturity levels.

---

## Changes Made

### 1. New File: `backend/config/scoring_config.json`

**Path:** `backend/config/scoring_config.json`

Contains all scoring policy in a single, documented JSON file:

| Section | Description |
|---------|-------------|
| `defaults.starting_score` | Baseline score (100) |
| `defaults.minimum_score` | Floor (0) |
| `defaults.maximum_score` | Ceiling (100) |
| `defaults.severity_deductions` | Points deducted per severity level |
| `defaults.grade_thresholds` | Score→Grade mapping |
| `defaults.categories` | Scoring categories with domain/category aliases |
| `category_weights` | Per-category deduction overrides (same as defaults initially) |
| `maturity_levels` | Four named scoring models: `standard`, `strict`, `lenient`, `security_focused` |
| `client_overrides` | Per-client overrides for deductions, thresholds, and maturity level |

### 2. New File: `backend/config/classification_config.json`

**Path:** `backend/config/classification_config.json`

Contains classification keyword mappings previously hardcoded in `registry.py`:

| Section | Description |
|---------|-------------|
| `severity_keywords` | Ordered list of keyword→severity pairs for parsing classification text |
| `category_map` | Maps raw RAG category strings to internal category keys |
| `severity_default` | Fallback severity when no keyword matches |
| `category_default` | Fallback category when RAG entry has no category |

### 3. Modified: `backend/rag/registry.py`

**Lines 73-97** — Removed hardcoded `SEVERITY_KEYWORDS`, `CATEGORY_MAP`, and defaults. Now loaded from `classification_config.json`:

```python
SEVERITY_KEYWORDS: list[tuple[str, str]] = [
    (item["keyword"], item["severity"])
    for item in _CLASSIFICATION_CONFIG.get("severity_keywords", [])
]
CATEGORY_MAP: dict[str, str] = dict(_CLASSIFICATION_CONFIG.get("category_map", {}))
SEVERITY_DEFAULT = _CLASSIFICATION_CONFIG.get("severity_default", "informational")
CATEGORY_DEFAULT = _CLASSIFICATION_CONFIG.get("category_default", "unknown")
```

**Imports:** Added `from typing import Any`.

### 4. Modified: `backend/agents/dashboard_agent/scoring.py`

Complete rewrite of configuration loading:

- **`DEFAULT_SCORING_CONFIG`** is now built by `build_scoring_config()` which reads from `scoring_config.json`
- **`HealthScoringEngine.__init__`** accepts optional `client_id` and `maturity` parameters for per-client/per-maturity scoring
- **`_deduction_for_finding()`** now accepts `category_key` and resolves category-specific deductions via `_resolve_category_deductions()`
- **`build_scoring_config()`** resolves config with this priority chain:
  1. Client overrides from `scoring_config.json` `client_overrides` section
  2. Maturity level from `maturity_levels[]` matching the resolved maturity name
  3. Category-specific weights from `category_weights[]`
  4. Default values from `defaults{}`
- **`ScoringConfig`** now includes `maturity` and `client_id` fields for traceability
- **`ScoringPolicy` response** now includes `maturity` and `client_id`

New helper functions:
- `_resolve_client_maturity()` — reads maturity level from client overrides
- `_resolve_deductions()` — resolves deductions with category-specific + client + maturity merging
- `_resolve_grade_thresholds()` — resolves thresholds with client + maturity merging
- `_resolve_starting/minimum/maximum_score()` — resolves with client override support

### 5. Modified: `backend/agents/security_agent/scanner.py`

- **Line 84:** Fixed `FindingSeverity.INFO` → `FindingSeverity.INFORMATIONAL` (bug fix)
- **Lines 129-171:** Replaced hardcoded recommendation severity strings with `resolve_severity(rag_rule_id)` calls:
  - `severity="critical_risk"` → `resolve_severity("RULE-SEC-001")`
  - `severity="risk"` → `resolve_severity("RULE-SEC-002")`
  - `severity="warning"` → `resolve_severity("RULE-SEC-008")`
- **Line 2:** Added `resolve_severity` to imports

### 6. Modified: `backend/agents/performance_agent/analyzer.py`

- **Line 51:** Fixed `FindingSeverity.INFO` → `FindingSeverity.INFORMATIONAL` (bug fix)

### 7. Modified: `backend/shared/models.py`

- **Line 62:** Changed `AgentRecommendation.severity` default from `"info"` → `"informational"`

### 8. Modified: `backend/agents/dashboard_agent/aggregator.py`

- **Lines 56-57:** Changed KPI display severity from `"info"` → `"informational"`

### 9. Modified: `backend/services/dashboard_service.py`

- **Line 341, 411, 432:** Changed fallback severity from `"info"` → `"informational"`

### 10. Modified: `backend/agents/recommendation_agent/generator.py`

- **Line 201:** Changed severity check from `== "critical"` → `in {"critical_risk", "risk"}`

---

## Configuration Resolution Priority

When computing a score, the framework resolves each config value in this order (higher number wins):

| Priority | Source | Scope |
|----------|--------|-------|
| 1 (low) | `defaults{}` in scoring_config.json | Global |
| 2 | `category_weights[category_key]{}` | Per-category |
| 3 | `maturity_levels[].severity_deductions{}` | Per-maturity |
| 4 | `maturity_levels[].category_weights[].{}` | Per-category per-maturity |
| 5 (high) | `client_overrides[client_id].{}` | Per-client |

---

## Maturity Levels Available

| Name | Description | Deductions |
|------|-------------|------------|
| `standard` | Balanced model (default) | 10/5/2/1/0 |
| `strict` | For regulated industries | 15/8/4/1/0 |
| `lenient` | For internal/early-stage | 5/3/1/0/0 |
| `security_focused` | Strict security, standard rest | Security: 15/8/4/1/0, Others: 10/5/2/1/0 |

---

## Backward Compatibility

- **API unchanged:** `HealthScoringEngine()` with no arguments still works — loads defaults from file
- **DashboardAggregator** unchanged interface — still receives `scoring_engine` optionally
- All existing callers continue to work without modification

---

## Verification

- `grep` confirms **zero hardcoded deduction values** in `scoring.py`
- `grep` confirms **zero old severity strings** (`"critical"`, `"high"`, `"medium"`, `"low"`, `"info"`) used as severity values in `backend/`
- `grep` confirms **zero instances** of `FindingSeverity.INFO`, `FindingSeverity.CRITICAL`, `FindingSeverity.HIGH`, `FindingSeverity.MEDIUM`, `FindingSeverity.LOW`
- All recommendation severities now flow through `resolve_severity()` RAG resolution
