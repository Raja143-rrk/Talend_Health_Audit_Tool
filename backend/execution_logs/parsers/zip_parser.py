from pathlib import Path

from backend.core.logging import get_logger
from backend.execution_logs.models import ExecutionLogEntry
from backend.execution_logs.parsers.base import BaseParser

logger = get_logger(__name__)


class ZipParser(BaseParser):
    """Parses a ZIP by delegating to sub-parsers for each contained file."""

    def __init__(self, extract_dir: Path | None = None) -> None:
        self._extract_dir = extract_dir

    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == ".zip"

    def parse(self, file_path: Path) -> list[ExecutionLogEntry]:
        from backend.execution_logs.parsers.factory import ParserFactory
        from backend.execution_logs.upload_handler import upload_handler

        extract_dir = self._extract_dir or file_path.parent / f"{file_path.stem}_extracted"
        extracted = upload_handler.extract_zip(file_path, extract_dir)
        if not extracted:
            logger.info("No parseable files found inside %s", file_path.name)
            return []

        all_entries: list[ExecutionLogEntry] = []
        for extracted_file in extracted:
            parser = ParserFactory.get_parser(extracted_file)
            if parser is None or isinstance(parser, ZipParser):
                logger.debug("No parser or nested zip for %s, skipping", extracted_file.name)
                continue
            try:
                entries = parser.parse(extracted_file)
                all_entries.extend(entries)
            except Exception as exc:
                logger.warning("Failed to parse %s: %s", extracted_file.name, exc)

        logger.info("Parsed %s execution record(s) from ZIP %s", len(all_entries), file_path.name)
        return all_entries
