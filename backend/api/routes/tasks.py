from fastapi import APIRouter

from backend.schemas.analysis import AnalysisTaskStatusResponse
from backend.services.analysis_service import analysis_service

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}/status", response_model=AnalysisTaskStatusResponse)
async def get_task_status(task_id: str) -> AnalysisTaskStatusResponse:
    return AnalysisTaskStatusResponse(**analysis_service.get_task_status_payload(task_id))
