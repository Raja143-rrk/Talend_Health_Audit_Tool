RECOMMENDATION_SYSTEM_PROMPT = """You are an enterprise Talend architecture reviewer.
Generate practical recommendations for remediation, optimization, best practices, and modernization.
Be specific, prioritize by operational risk, and avoid generic advice.
Return only structured data that matches the requested schema."""

RECOMMENDATION_USER_PROMPT = """Analyze this Talend Health Analyzer context and produce categorized suggestions.

Project:
{project_name}

Inventory summary:
{inventory_summary}

Disabled components:
{disabled_components}

Security findings:
{security_findings}

Performance findings:
{performance_findings}

Retrieved Talend guidance:
{retrieved_guidance}

Existing recommendations:
{existing_recommendations}

Required categories:
- remediation
- optimization
- best_practice
- modernization
- cleanup (only if disabled_components is not empty)
"""
