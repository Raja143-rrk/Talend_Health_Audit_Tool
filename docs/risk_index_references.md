# Risk Index / Health Score / Deduction-Based Scoring References

## Frontend

| File | Lines | Description |
|------|-------|-------------|
| `frontend/app/dashboard/page.tsx` | 377, 435, 451-455, 490 | Health Score KPI card rendering, health_score variable, insights summary |
| `frontend/components/dashboard/ai-chat-panel.tsx` | 24 | "Explain the health score" starter prompt |
| `frontend/components/dashboard/analysis-loader.tsx` | 14 | "Generating health score and recommendations" text |
| `frontend/components/dashboard/analytics-charts.tsx` | 148-179, 325, 353-354, 401, 406, 452 | HealthScoreGaugeChart component, health_score in InsightsSummaryPanel |
| `frontend/lib/dashboard.ts` | 11, 27-28, 39, 115, 133 | ScoreDeduction type, deduction_total, severity_deductions, health_score, health_score_gauge |

## Backend Python

### Agents
| File | Lines | Description |
|------|-------|-------------|
| `backend/agents/dashboard_agent/agent.py` | 47, 62 | dashboard.health_score references |
| `backend/agents/dashboard_agent/aggregator.py` | 11, 22, 26, 47-48, 66-69, 76, 102, 242, 275 | HealthScoringEngine import/usage, health_score/grade/risk_level/risk_index in output |
| `backend/agents/dashboard_agent/models.py` | 18, 30-33 | health_score_gauge, health_score, health_grade, risk_index, risk_level fields |
| `backend/agents/dashboard_agent/scoring.py` | 45-81, 88-105, 157, 159, 177-178, 196-279 | HealthScoringEngine class, _resolve_deductions, _resolve_grade_thresholds |

### Services
| File | Lines | Description |
|------|-------|-------------|
| `backend/services/chat_service.py` | 110, 234-235, 353, 388-389, 439-440, 447, 450, 465-466, 473-474, 488, 496, 656-657, 677, 679, 682, 687, 696, 698, 701, 723, 735-736, 748-749, 774, 821, 833-834, 843, 868, 872, 883, 887, 1026-1027, 1032, 1113-1114, 1273, 1374 | Multiple health_score, risk_index, deduction, risk_level references in chat responses |
| `backend/services/dashboard_service.py` | 95-97, 102, 125-128, 359, 391 | health_score, health_grade, risk_level, risk_index, health_score_gauge, severity_deductions in API responses |

### Schemas
| File | Lines | Description |
|------|-------|-------------|
| `backend/schemas/dashboard.py` | 28, 44-45, 52, 92-95, 123 | ScoreDeduction model, deduction_total, deductions, severity_deductions, risk_index, risk_level, health_score, health_grade, health_score_gauge |

## Backend Config
| File | Lines | Description |
|------|-------|-------------|
| `backend/config/scoring_config.json` | 8-21, 83-159, 169 | severity_deductions, grade_thresholds for health scoring (defaults and maturity levels) |
