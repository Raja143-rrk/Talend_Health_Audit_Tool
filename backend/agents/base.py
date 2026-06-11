from abc import ABC, abstractmethod
from datetime import datetime

from backend.shared.execution import RetryConfig, run_with_retries
from backend.shared.logger import get_agent_logger
from backend.shared.models import AgentContext, AgentResponse, AgentStatus
from backend.shared.utils import utc_now


class BaseAgent(ABC):
    name: str = "base-agent"
    description: str = "Base agent contract for Talend Health Analyzer."
    retry_config: RetryConfig = RetryConfig()

    def __init__(self) -> None:
        self.logger = get_agent_logger(self.name)
        self.status = AgentStatus.PENDING
        self.last_response: AgentResponse | None = None

    async def run(self, context: AgentContext) -> AgentResponse:
        started_at = utc_now()
        self.status = AgentStatus.RUNNING
        self.logger.info("Starting %s for analysis %s", self.name, context.analysis_id)

        try:
            result, attempts = await run_with_retries(
                operation=lambda: self.execute(context, started_at),
                retry_config=self.retry_config,
                on_retry=self._handle_retry,
            )
            result.attempts = attempts
            if result.completed_at:
                result.duration_ms = int(
                    (result.completed_at - result.started_at).total_seconds() * 1000
                )
            self.status = result.status
            self.last_response = result
            self.logger.info("Completed %s for analysis %s", self.name, context.analysis_id)
            return result
        except Exception as exc:
            attempts = self.retry_config.max_attempts
            self.status = AgentStatus.FAILED
            self.logger.exception("Agent %s failed", self.name)
            response = AgentResponse.failed(
                agent_name=self.name,
                started_at=started_at,
                error=exc,
                attempts=attempts,
            )
            self.last_response = response
            return response

    def _handle_retry(self, attempt: int, exc: Exception) -> None:
        self.status = AgentStatus.RETRYING
        self.logger.warning(
            "Retrying %s after attempt %s failed: %s",
            self.name,
            attempt,
            exc,
        )

    @abstractmethod
    async def execute(self, context: AgentContext, started_at: datetime) -> AgentResponse:
        raise NotImplementedError
