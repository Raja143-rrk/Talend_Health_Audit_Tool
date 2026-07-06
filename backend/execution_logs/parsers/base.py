from abc import ABC, abstractmethod
from pathlib import Path

from backend.execution_logs.models import ExecutionLogEntry


class BaseParser(ABC):

    @abstractmethod
    def supports(self, file_path: Path) -> bool:
        ...

    @abstractmethod
    def parse(self, file_path: Path) -> list[ExecutionLogEntry]:
        ...
