from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile, status

from backend.schemas.execution_logs import (
    ExecutionLogHistoryItem,
    ExecutionLogUploadDetail,
    ExecutionLogUploadResponse,
    ExecutionRecordResponse,
    ProjectInfo,
    ProjectUploadSummary,
)
from backend.services.execution_log_service import execution_log_service

router = APIRouter(prefix="/execution-logs", tags=["execution-logs"])


@router.get("/projects", response_model=list[ProjectInfo])
async def list_projects() -> list[ProjectInfo]:
    return execution_log_service.get_projects()


@router.post(
    "/upload",
    response_model=ExecutionLogUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_execution_log(
    project_id: Annotated[str, Form()],
    project_name: Annotated[str, Form()],
    file: Annotated[UploadFile, File(alias="file")],
) -> ExecutionLogUploadResponse:
    return await execution_log_service.upload_log(project_id, project_name, file)


@router.get("/history", response_model=list[ExecutionLogHistoryItem])
async def get_upload_history() -> list[ExecutionLogHistoryItem]:
    return execution_log_service.get_upload_history()


@router.get(
    "/projects/{project_id}/summary",
    response_model=ProjectUploadSummary | None,
    responses={404: {"description": "No upload found for project"}},
)
async def get_project_upload_summary(project_id: str) -> ProjectUploadSummary | None:
    summary = execution_log_service.get_project_summary(project_id)
    if summary is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"No upload found for project: {project_id}")
    return summary


@router.get(
    "/{upload_id}",
    response_model=ExecutionLogUploadDetail,
    responses={404: {"description": "Upload not found"}},
)
async def get_upload_detail(upload_id: str) -> ExecutionLogUploadDetail:
    detail = execution_log_service.get_upload_detail(upload_id)
    if detail is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"Upload not found: {upload_id}")
    return detail


@router.get(
    "/projects/{project_id}/records",
    response_model=list[ExecutionRecordResponse],
)
async def get_execution_records(project_id: str) -> list[ExecutionRecordResponse]:
    return execution_log_service.get_execution_records(project_id)
