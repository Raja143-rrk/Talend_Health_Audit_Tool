from datetime import datetime, timezone

from fastapi import APIRouter

from backend.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="Talend Health Analyzer API",
        environment="development",
        timestamp=datetime.now(timezone.utc),
    )
