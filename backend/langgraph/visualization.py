WORKFLOW_MERMAID = """flowchart TD
    START([Start])
    ZIP[ZIP Agent]
    PARSER[Parser Agent]
    SECURITY[Security Agent]
    PERFORMANCE[Performance Agent]
    RECOMMENDATION[Recommendation Agent]
    DASHBOARD[Dashboard Agent]
    END([End])
    FAIL[[Stop: Required Input Failed]]

    START --> ZIP
    ZIP -->|valid ZIP extracted| PARSER
    ZIP -->|failed| FAIL
    PARSER -->|inventory parsed| SECURITY
    PARSER -->|inventory parsed| PERFORMANCE
    PARSER -->|failed| FAIL
    SECURITY --> RECOMMENDATION
    PERFORMANCE --> RECOMMENDATION
    RECOMMENDATION --> DASHBOARD
    DASHBOARD --> END
"""


def workflow_mermaid() -> str:
    return WORKFLOW_MERMAID
