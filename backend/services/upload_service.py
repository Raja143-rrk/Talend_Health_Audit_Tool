import asyncio
import uuid
import zipfile
from pathlib import Path

from fastapi import UploadFile

from backend.core.exceptions import BadRequestError, AppError
from backend.core.logging import get_logger
from backend.schemas.upload import UploadResponse

logger = get_logger(__name__)
UPLOADS_DIR = Path(__file__).resolve().parents[2] / "uploads"

MAX_UPLOAD_SIZE_MB = 500
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

ZIP_CONTENT_TYPES = {
    "application/zip",
    "application/x-zip-compressed",
    "multipart/x-zip",
}


class UploadService:
    async def save_zip(self, file: UploadFile) -> UploadResponse:
        self._validate_zip_metadata(file)

        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        saved_name = self._build_safe_filename(file.filename)
        destination = UPLOADS_DIR / saved_name

        try:
            await asyncio.to_thread(self._copy_upload_file, file, destination)

            if not zipfile.is_zipfile(destination):
                destination.unlink(missing_ok=True)
                raise BadRequestError("Uploaded file is not a valid ZIP archive.")
        except AppError:
            raise
        except Exception as exc:
            destination.unlink(missing_ok=True)
            logger.exception("ZIP upload failed")
            raise AppError("Unable to save uploaded ZIP file.") from exc
        finally:
            await file.close()

        logger.info("Saved ZIP upload %s as %s", file.filename, destination)
        return UploadResponse(
            filename=saved_name,
            original_filename=file.filename or "talend-upload.zip",
            size_bytes=destination.stat().st_size,
            path=str(destination),
        )

    async def save_zips(self, files: list[UploadFile]) -> list[UploadResponse]:
        responses: list[UploadResponse] = []
        for file in files:
            response = await self.save_zip(file)
            responses.append(response)
        return responses

    def _copy_upload_file(self, file: UploadFile, destination: Path) -> None:
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

    def _validate_zip_metadata(self, file: UploadFile) -> None:
        if not file.filename or not file.filename.lower().endswith(".zip"):
            raise BadRequestError("Only .zip files are supported.")

        if file.content_type and file.content_type not in ZIP_CONTENT_TYPES:
            raise BadRequestError("Uploaded file must be a ZIP archive.")

    def _build_safe_filename(self, filename: str | None) -> str:
        original_name = Path(filename or "talend-upload.zip").name
        stem = Path(original_name).stem or "talend-upload"
        normalized_stem = "".join(
            character if character.isalnum() or character in {"-", "_"} else "-"
            for character in stem
        ).strip("-")
        return f"{normalized_stem or 'talend-upload'}-{uuid.uuid4().hex}.zip"


upload_service = UploadService()
