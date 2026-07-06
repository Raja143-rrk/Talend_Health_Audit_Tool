from abc import ABC, abstractmethod

from backend.execution_logs.models import ExecutionLogUploadRecord


class BaseStorage(ABC):

    @abstractmethod
    def save(self, record: ExecutionLogUploadRecord) -> None:
        ...

    @abstractmethod
    def get(self, record_id: str) -> ExecutionLogUploadRecord | None:
        ...

    @abstractmethod
    def list_all(self) -> list[ExecutionLogUploadRecord]:
        ...

    @abstractmethod
    def delete(self, record_id: str) -> bool:
        ...
