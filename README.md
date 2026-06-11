# Talend Health Analyzer

Enterprise starter scaffold for a Next.js frontend and FastAPI backend.

## Structure

```text
.
|-- backend/
|   |-- .env.example
|   |-- __init__.py
|   |-- main.py
|   |-- requirements.txt
|   |-- agents/
|   |   |-- base.py
|   |   |-- zip_agent/
|   |   |-- parser_agent/
|   |   |-- security_agent/
|   |   |-- performance_agent/
|   |   |-- recommendation_agent/
|   |   `-- dashboard_agent/
|   |-- api/routes/health.py
|   |-- api/routes/uploads.py
|   |-- core/logging.py
|   |-- langgraph/
|   |   |-- state.py
|   |   `-- workflow.py
|   |-- rag/
|   |   |-- documents.py
|   |   `-- retriever.py
|   |-- rule_engine/
|   |   |-- engine.py
|   |   `-- rules.py
|   |-- shared/
|   |   |-- execution.py
|   |   |-- logger.py
|   |   |-- models.py
|   |   `-- utils.py
|   `-- schemas/
|       |-- health.py
|       `-- upload.py
|-- frontend/
|   |-- .env.example
|   |-- package.json
|   |-- tsconfig.json
|   |-- postcss.config.mjs
|   |-- eslint.config.mjs
|   |-- app/
|   |   |-- globals.css
|   |   |-- layout.tsx
|   |   |-- page.tsx
|   |   `-- dashboard/page.tsx
|   |-- components/
|   |   |-- dashboard/status-card.tsx
|   |   |-- layout/app-shell.tsx
|   |   `-- upload/zip-upload-panel.tsx
|   `-- lib/
|       |-- config.ts
|       `-- upload.ts
|-- uploads/
`-- reports/
```

## Backend setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
uvicorn backend.main:app --reload
```

If you are already inside `backend/`, go back to the project root before running Uvicorn:

```powershell
cd ..
uvicorn backend.main:app --reload
```

Alternative setup from inside `backend/`:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
cd ..
uvicorn backend.main:app --reload
```

Upload endpoint:

```text
POST http://localhost:8000/api/v1/uploads/zip
```

Mock dashboard endpoints:

```text
GET http://localhost:8000/api/v1/dashboard/analysis/status
GET http://localhost:8000/api/v1/dashboard/summary
GET http://localhost:8000/api/v1/dashboard/charts
GET http://localhost:8000/api/v1/dashboard/findings/security
GET http://localhost:8000/api/v1/dashboard/findings/performance
GET http://localhost:8000/api/v1/dashboard/recommendations
```

Agent framework:

```text
BaseAgent provides async execution, shared logging, status tracking, retry support,
standardized AgentResponse output, and exception-to-response handling.
```

Workflow orchestration:

```text
AgentWorkflow runs ZIP -> Parser -> Security + Performance in parallel ->
Recommendation -> Dashboard. Use AgentWorkflow.graph_mermaid() to render the
workflow graph visualization.
```

Workflow state management:

```text
WorkflowState is the centralized async-safe state model for agent outputs,
workflow context, shared data, and agent-to-agent handoffs. Agents receive
isolated context snapshots from WorkflowState.context_for_agent(), while API
status updates use WorkflowState.snapshot() for consistent reads.
```

RAG configuration:

```text
RagRetriever includes a built-in Talend knowledge base and supports memory,
FAISS, or Chroma retrieval through RAG_VECTOR_DB. LLM inference uses Groq
via GROQ_API_KEY and GROQ_API_BASE_URL. For RAG embeddings, the default
provider is fake (Groq does not support embedding endpoints).
```

## Frontend setup

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```
