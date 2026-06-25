from fastapi import APIRouter, HTTPException, status

from backend.core.exceptions import AppError
from backend.schemas.dashboard import (
    AnalysisStatusResponse,
    ChartDataResponse,
    ComponentDrillDown,
    DashboardOverviewResponse,
    DashboardSummaryResponse,
    FindingsResponse,
    RecommendationsResponse,
)
from backend.services.dashboard_service import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _dashboard_error(exc: Exception, detail: str) -> HTTPException:
    if isinstance(exc, AppError):
        return HTTPException(status_code=exc.status_code, detail=exc.message)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=detail,
    )


@router.get("", response_model=DashboardOverviewResponse)
async def get_dashboard(
    analysis_id: str | None = None,
    job_name: str | None = None,
) -> DashboardOverviewResponse:
    try:
        return dashboard_service.get_dashboard_overview(analysis_id, job_name)
    except Exception as exc:
        raise _dashboard_error(exc, "Unable to load dashboard.") from exc


@router.get("/analysis/status", response_model=AnalysisStatusResponse)
async def get_analysis_status(analysis_id: str | None = None) -> AnalysisStatusResponse:
    try:
        return dashboard_service.get_analysis_status(analysis_id)
    except Exception as exc:
        raise _dashboard_error(exc, "Unable to load analysis status.") from exc


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    analysis_id: str | None = None,
    job_name: str | None = None,
) -> DashboardSummaryResponse:
    try:
        return dashboard_service.get_dashboard_summary(analysis_id, job_name)
    except Exception as exc:
        raise _dashboard_error(exc, "Unable to load dashboard summary.") from exc


@router.get("/charts", response_model=ChartDataResponse)
async def get_chart_data(analysis_id: str | None = None) -> ChartDataResponse:
    try:
        return dashboard_service.get_chart_data(analysis_id)
    except Exception as exc:
        raise _dashboard_error(exc, "Unable to load chart data.") from exc


@router.get("/findings/security", response_model=FindingsResponse)
async def get_security_findings(
    analysis_id: str | None = None,
    job_name: str | None = None,
) -> FindingsResponse:
    try:
        return dashboard_service.get_security_findings(analysis_id, job_name)
    except Exception as exc:
        raise _dashboard_error(exc, "Unable to load security findings.") from exc


@router.get("/findings/performance", response_model=FindingsResponse)
async def get_performance_findings(
    analysis_id: str | None = None,
    job_name: str | None = None,
) -> FindingsResponse:
    try:
        return dashboard_service.get_performance_findings(analysis_id, job_name)
    except Exception as exc:
        raise _dashboard_error(exc, "Unable to load performance findings.") from exc


@router.get("/recommendations", response_model=RecommendationsResponse)
async def get_recommendations(
    analysis_id: str | None = None,
    job_name: str | None = None,
) -> RecommendationsResponse:
    try:
        return dashboard_service.get_recommendations(analysis_id, job_name)
    except Exception as exc:
        raise _dashboard_error(exc, "Unable to load recommendations.") from exc


@router.get("/components/drilldown", response_model=list[ComponentDrillDown])
async def get_component_drilldown(
    analysis_id: str | None = None,
    job_name: str | None = None,
) -> list[ComponentDrillDown]:
    try:
        return dashboard_service.get_component_drilldown(analysis_id, job_name)
    except Exception as exc:
        raise _dashboard_error(exc, "Unable to load component drill-down.") from exc
