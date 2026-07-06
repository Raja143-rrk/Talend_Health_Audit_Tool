import time
from pathlib import Path

from dotenv import load_dotenv

for env_path in (Path(__file__).resolve().parent.parent / ".env", Path.cwd() / ".env"):
    if env_path.is_file():
        load_dotenv(env_path, override=True)
        break

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes.analysis import router as analysis_router
from backend.api.routes.chat import router as chat_router
from backend.api.routes.dashboard import router as dashboard_router
from backend.api.routes.health import router as health_router
from backend.api.routes.tasks import router as tasks_router
from backend.api.routes.execution_logs import router as execution_logs_router
from backend.api.routes.uploads import router as uploads_router
from backend.core.exceptions import register_exception_handlers
from backend.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

app = FastAPI(title="Talend Health Analyzer API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def timing_middleware(request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    response.headers["X-Process-Time"] = str(elapsed_ms)
    logger.info(
        "%s %s %s %dms",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


register_exception_handlers(app)


@app.get("/", tags=["sample"])
async def read_root() -> dict[str, str]:
    return {"message": "Talend Health Analyzer FastAPI service is running"}


app.include_router(health_router, prefix="/api/v1")
app.include_router(uploads_router, prefix="/api/v1")
app.include_router(analysis_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(execution_logs_router, prefix="/api/v1")
