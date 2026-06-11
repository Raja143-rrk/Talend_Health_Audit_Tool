from fastapi import APIRouter

from backend.schemas.analysis import AnalysisDashboardResponse, AnalysisStatusResponse
from backend.services.analysis_service import analysis_service

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/{analysis_id}/status", response_model=AnalysisStatusResponse)
async def get_analysis_status(analysis_id: str) -> AnalysisStatusResponse:
    return AnalysisStatusResponse(**analysis_service.get_status_payload(analysis_id))


@router.get("/{analysis_id}/dashboard", response_model=AnalysisDashboardResponse)
async def get_analysis_dashboard(analysis_id: str) -> AnalysisDashboardResponse:
    return AnalysisDashboardResponse(**analysis_service.get_dashboard_payload(analysis_id))
