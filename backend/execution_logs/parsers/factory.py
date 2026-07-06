from pathlib import Path

from backend.execution_logs.parsers.base import BaseParser
from backend.execution_logs.parsers.csv_parser import CsvParser
from backend.execution_logs.parsers.log_parser import LogParser


class ParserFactory:
    _parsers: list[type[BaseParser]] = []

    @classmethod
    def _ensure_loaded(cls) -> None:
        if cls._parsers:
            return
        from backend.execution_logs.parsers.zip_parser import ZipParser

        cls._parsers = [
            ZipParser,
            CsvParser,
            LogParser,
        ]

    @classmethod
    def get_parser(cls, file_path: Path) -> BaseParser | None:
        cls._ensure_loaded()
        for parser_cls in cls._parsers:
            instance = parser_cls()
            if instance.supports(file_path):
                return instance
        return None

    @classmethod
    def register(cls, parser_cls: type[BaseParser]) -> None:
        cls._ensure_loaded()
        cls._parsers.insert(0, parser_cls)
