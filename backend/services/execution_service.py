import asyncio

from fastapi import UploadFile

from backend.core.exceptions import AppError
from backend.core.logging import get_logger
from backend.schemas.analysis import AnalysisCreateResponse, AnalysisExecutionResponse
from backend.services.analysis_service import AnalysisRecord, analysis_service
from backend.services.upload_service import upload_service

logger = get_logger(__name__)


class ExecutionService:
    """Coordinates the production ZIP-to-dashboard execution flow."""

    async def queue_zip_analysis(
        self,
        file: UploadFile,
    ) -> AnalysisCreateResponse:
        upload, record = await self._create_analysis_from_upload(file)
        asyncio.create_task(analysis_service.run_analysis(record.analysis_id))

        logger.info(
            "Queued end-to-end analysis task %s for analysis %s",
            record.task_id,
            record.analysis_id,
        )
        return AnalysisCreateResponse(
            task_id=record.task_id,
            analysis_id=record.analysis_id,
            status=record.status.value,
            message="Analysis queued. Poll the status URL until the dashboard is ready.",
            upload=upload.model_dump(),
            task_status_url=self._task_status_url(record),
            status_url=self._status_url(record),
            dashboard_url=self._dashboard_url(record),
        )

    async def execute_zip_analysis(self, file: UploadFile) -> AnalysisExecutionResponse:
        upload, record = await self._create_analysis_from_upload(file)

        logger.info(
            "Starting synchronous end-to-end analysis task %s for analysis %s",
            record.task_id,
            record.analysis_id,
        )
        try:
            await analysis_service.run_analysis(record.analysis_id)
            execution_payload = analysis_service.get_execution_payload(record.analysis_id)
            workflow = execution_payload.get("workflow", {})
            dashboard = execution_payload.get("dashboard")
            status = str(execution_payload.get("status") or record.status.value)
        except AppError:
            raise
        except Exception as exc:
            logger.exception(
                "End-to-end analysis failed for analysis %s",
                record.analysis_id,
            )
            raise AppError("Unable to complete analysis workflow.") from exc

        return AnalysisExecutionResponse(
            task_id=record.task_id,
            analysis_id=record.analysis_id,
            status=status,
            message=self._completion_message(status),
            upload=upload.model_dump(),
            dashboard=dashboard,
            workflow=workflow,
            task_status_url=self._task_status_url(record),
            status_url=self._status_url(record),
            dashboard_url=self._dashboard_url(record),
        )

    async def _create_analysis_from_upload(self, file: UploadFile):
        upload = await upload_service.save_zip(file)
        record = analysis_service.create_analysis(
            upload_path=upload.path,
            original_filename=upload.original_filename,
        )
        logger.info(
            "Created analysis %s for uploaded ZIP %s",
            record.analysis_id,
            upload.original_filename,
        )
        return upload, record

    def _task_status_url(self, record: AnalysisRecord) -> str:
        return f"/api/v1/tasks/{record.task_id}/status"

    def _status_url(self, record: AnalysisRecord) -> str:
        return f"/api/v1/analysis/{record.analysis_id}/status"

    def _dashboard_url(self, record: AnalysisRecord) -> str:
        return f"/api/v1/analysis/{record.analysis_id}/dashboard"

    def _completion_message(self, status: str) -> str:
        if status == "completed":
            return "Analysis completed and dashboard is ready."
        if status == "partial":
            return "Analysis completed with partial results; dashboard is available."
        if status == "failed":
            return "Analysis failed before dashboard generation."
        return "Analysis finished."


execution_service = ExecutionService()
