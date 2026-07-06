import asyncio
import uuid
import zipfile
from pathlib import Path

from fastapi import UploadFile

from backend.core.exceptions import BadRequestError, AppError
from backend.core.logging import get_logger

logger = get_logger(__name__)

EXECUTION_LOGS_DIR = Path(__file__).resolve().parents[2] / "uploads" / "execution_logs"

ALLOWED_EXTENSIONS = {".zip", ".log", ".csv"}
ALLOWED_CONTENT_TYPES = {
    "application/zip",
    "application/x-zip-compressed",
    "text/plain",
    "text/csv",
    "application/csv",
    "text/x-log",
    "application/octet-stream",
    "",
}
MAX_UPLOAD_SIZE_MB = 200
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024


class UploadHandler:

    async def receive(self, project_id: str, file: UploadFile) -> Path:
        self._validate(file)
        project_dir = EXECUTION_LOGS_DIR / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        saved_name = self._build_safe_filename(file.filename)
        destination = project_dir / saved_name
        try:
            await asyncio.to_thread(self._copy, file, destination)
            ext = Path(file.filename or "").suffix.lower()
            if ext == ".zip" and not zipfile.is_zipfile(destination):
                destination.unlink(missing_ok=True)
                raise BadRequestError("Uploaded file is not a valid ZIP archive.")
        except AppError:
            raise
        except Exception as exc:
            destination.unlink(missing_ok=True)
            logger.exception("Execution log upload failed")
            raise AppError("Unable to save uploaded file.") from exc
        finally:
            await file.close()
        logger.info("Saved execution log %s for project %s", saved_name, project_id)
        return destination

    def extract_zip(self, zip_path: Path, extract_dir: Path | None = None) -> list[Path]:
        if extract_dir is None:
            extract_dir = zip_path.parent / f"{zip_path.stem}_extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)
        extracted: list[Path] = []
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.namelist():
                member_path = Path(member)
                ext = member_path.suffix.lower()
                if ext not in ALLOWED_EXTENSIONS and ext != ".zip":
                    continue
                target = extract_dir / member_path.name
                with zf.open(member) as source, open(target, "wb") as dest:
                    dest.write(source.read())
                extracted.append(target)
        logger.info("Extracted %s file(s) from %s", len(extracted), zip_path.name)
        return extracted

    def _validate(self, file: UploadFile) -> None:
        if not file.filename:
            raise BadRequestError("File must have a name.")
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise BadRequestError(
                f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
            )
        if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
            raise BadRequestError(f"File content type '{file.content_type}' is not supported.")

    def _copy(self, file: UploadFile, destination: Path) -> None:
        with destination.open("wb") as output_file:
            total = 0
            while True:
                chunk = file.file.read(8192)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_UPLOAD_SIZE_BYTES:
                    raise BadRequestError(
                        f"Upload exceeds maximum allowed size of {MAX_UPLOAD_SIZE_MB} MB."
                    )
                output_file.write(chunk)

    def _build_safe_filename(self, filename: str | None) -> str:
        original_name = Path(filename or "execution-log.zip").name
        stem = Path(original_name).stem or "execution-log"
        normalized_stem = "".join(
            character if character.isalnum() or character in {"-", "_"} else "-"
            for character in stem
        ).strip("-")
        ext = Path(original_name).suffix.lower()
        return f"{normalized_stem or 'execution-log'}-{uuid.uuid4().hex}{ext}"


upload_handler = UploadHandler()
