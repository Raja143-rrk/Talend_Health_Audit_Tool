# Severity Classification Migration Report

## Overview
Replaced the legacy 5-level severity model (Critical/High/Medium/Low/Info) with a new 5-level model (Critical Risk/Risk/Warning/Advisory/Informational). Classifications now come exclusively from RAG documents — no hardcoded severity values remain in agent or rule code.

## Changes Summary

### 1. Backend Enum (`backend/shared/models.py`)
- Removed: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO`
- Added: `CRITICAL_RISK`, `RISK`, `WARNING`, `ADVISORY`, `INFORMATIONAL`

### 2. RAG Registry (`backend/rag/registry.py`)
- Updated `SEVERITY_KEYWORDS`: maps ["critical risk"→"critical_risk", "risk"→"risk", "warning"→"warning", "advisory"→"advisory", "informational"→"informational"]
- Default severity changed from "info" → "informational"
- Added `apply_client_overrides()` — reads `backend/config/severity_overrides.json` for client-specific classification overrides
- `resolve_severity()` and `resolve_rag_fields()` now accept optional `client_id` parameter

### 3. RAG Markdown Documents (4 files updated)
| File | Changes |
|------|---------|
| `backend/rag/security/findings.md` | Remapped all 7 RULE-SEC-* classifications; added RULE-SEC-008 (Hardcoded Username → Warning) |
| `backend/rag/performance/findings.md` | Remapped all 9 RULE-PERF-* classifications (HIGH→Risk, MEDIUM→Warning, LOW→Advisory) |
| `backend/rag/maintainability/findings.md` | Remapped all 10 RULE-COMP-* classifications |
| `backend/rag/architecture/findings.md` | Remapped all 11 RULE-ARCH-* classifications |

### 4. Rule Engine (`backend/rule_engine/`)
- `engine.py`: `SEVERITY_ORDER` updated to new 5-level order; `_resolve_severity()` uses RAG first
- `models.py`: `RuleDefinition.severity` made optional (`None` default); `to_finding()` falls back to `INFORMATIONAL`
- `rules/security.py`, `rules/performance.py`, `rules/components.py`, `rules/architecture.py`: All `severity=FindingSeverity.*` lines removed; `FindingSeverity` import removed

### 5. Agents
| File | Changes |
|------|---------|
| `agents/security_agent/scanner.py` | SCANNER_TO_RAG_RULE_MAP: SEC-USERNAME-001 → RULE-SEC-008 (Warning); recommendations use new severity strings |
| `agents/security_agent/rules.py` | Unchanged (no severity fields) |
| `agents/performance_agent/analyzer.py` | Priority mapping updated: critical_risk→P1, risk→P2, warning/advisory/informational→P3 |
| `agents/performance_agent/rules.py` | Unchanged (no severity fields) |

### 6. Dashboard & Scoring
| File | Changes |
|------|---------|
| `agents/dashboard_agent/aggregator.py` | `_severity_summary()` keys changed; KPI severity label changed to "critical_risk" |
| `agents/dashboard_agent/scoring.py` | `severity_deductions` keys changed; default fallback changed to "informational" |
| `services/dashboard_service.py` | `_issue_chart_points()` buckets changed; `_risk_timeline()` fields updated |

### 7. Frontend (`frontend/components/dashboard/`)
| File | Changes |
|------|---------|
| `analysis-tabs.tsx` | `Severity` type, `severityOrder`, `severityClasses`, `normalizeSeverity()`, `severityFilter`, filter options all updated |
| `analytics-charts.tsx` | `severityColors`, severity data keys updated |

### 8. Client Overrides Config (`backend/config/severity_overrides.json`)
New file supporting:
```json
{
  "overrides": {
    "client_acme": {
      "RULE-SEC-001": "Warning - Relaxed severity for internal tools",
      "RULE-SEC-008": "Informational"
    }
  }
}
```
Usage: `resolve_severity("RULE-SEC-001", client_id="client_acme")` returns "warning"

## Default Classification Mapping

### Security
| Rule | Classification | Scanner Source |
|------|---------------|----------------|
| RULE-SEC-001 | Risk | Hardcoded passwords |
| RULE-SEC-002 | Risk | Inline JDBC URLs |
| RULE-SEC-003 | Risk | High volume of security findings |
| RULE-SEC-004 | Risk | Missing/unencrypted context variables |
| RULE-SEC-005 | Critical Risk | API keys, tokens, secrets |
| RULE-SEC-006 | Warning | Insecure DB connections |
| RULE-SEC-007 | Warning | Cross-environment context exposure |
| RULE-SEC-008 | Warning | Hardcoded usernames |

### Performance
| Rule | Classification |
|------|---------------|
| RULE-PERF-001 | Risk (memory bottleneck) |
| RULE-PERF-002 | Warning (excessive tMap) |
| RULE-PERF-003 | Warning (small commit) |
| RULE-PERF-004 | Warning (missing pushdown) |
| RULE-PERF-005 | Risk (large unoptimized lookup) |
| RULE-PERF-006 | Advisory (missing parallelization) |
| RULE-PERF-007 | Advisory (excessive memory) |
| RULE-PERF-008 | Advisory (redundant components) |
| RULE-PERF-009 | Warning (monolithic subjob) |

### Maintainability
| Rule | Classification |
|------|---------------|
| RULE-COMP-001 | Advisory (disabled component) |
| RULE-COMP-002 | Warning (large job) |
| RULE-COMP-003 | Informational (naming convention) |
| RULE-COMP-004 | Advisory (missing documentation) |
| RULE-COMP-005 | Warning (error handling) |
| RULE-COMP-006 | Warning (duplicate config) |
| RULE-COMP-007 | Warning (missing reuse) |
| RULE-COMP-008 | Warning (missing metadata) |
| RULE-COMP-009 | Warning (missing context) |
| RULE-COMP-010 | Advisory (unused items) |

### Architecture
| Rule | Classification |
|------|---------------|
| RULE-ARCH-001 | Risk (missing contexts) |
| RULE-ARCH-002 | Warning (high system spread) |
| RULE-ARCH-003 | Risk (missing error handling) |
| RULE-ARCH-004 | Warning (no CI/CD) |
| RULE-ARCH-005 | Risk (missing logging framework) |
| RULE-ARCH-006 | Warning (missing governed metadata) |
| RULE-ARCH-007 | Warning (monolithic job design) |
| RULE-ARCH-008 | Advisory (poor reusability) |
| RULE-ARCH-009 | Warning (missing error framework) |
| RULE-ARCH-010 | Warning (missing monitoring) |
| RULE-ARCH-011 | Warning (missing exception framework) |

## Verification
- All 153 RAG registry entries correctly parsed
- Engine severity order: Informational → Advisory → Warning → Risk → Critical Risk
- Full analysis pipeline: 11 Risk (passwords), 11 Warning (usernames), 10 Warning (performance) — zero legacy severity values
