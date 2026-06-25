from typing import Annotated

from fastapi import APIRouter, File, UploadFile, status

from backend.schemas.analysis import AnalysisCreateResponse, AnalysisExecutionResponse
from backend.schemas.upload import UploadResponse
from backend.services.execution_service import execution_service
from backend.services.upload_service import upload_service

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/zip", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_zip(file: Annotated[UploadFile, File(alias="file")]) -> UploadResponse:
    return await upload_service.save_zip(file)


@router.post(
    "/zip/analyze",
    response_model=AnalysisCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_zip_and_analyze(
    files: Annotated[list[UploadFile], File(alias="file")],
) -> AnalysisCreateResponse:
    return await execution_service.queue_zip_analysis(files)


@router.post(
    "/zip/execute",
    response_model=AnalysisExecutionResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_zip_and_execute(
    files: Annotated[list[UploadFile], File(alias="file")],
) -> AnalysisExecutionResponse:
    return await execution_service.execute_zip_analysis(files)
