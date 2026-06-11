from fastapi import APIRouter, HTTPException, status

from backend.core.exceptions import AppError
from backend.schemas.chat import DashboardChatRequest, DashboardChatResponse
from backend.services.chat_service import dashboard_chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


def _chat_error(exc: Exception, detail: str) -> HTTPException:
    if isinstance(exc, AppError):
        return HTTPException(status_code=exc.status_code, detail=exc.message)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=detail,
    )


@router.post("/dashboard", response_model=DashboardChatResponse)
async def dashboard_chat(request: DashboardChatRequest) -> DashboardChatResponse:
    try:
        return await dashboard_chat_service.chat(request)
    except Exception as exc:
        raise _chat_error(exc, "Unable to process dashboard chat request.") from exc
