import shutil
import zipfile
from pathlib import Path

from backend.shared.utils import ensure_directory

PROJECT_ROOT = Path(__file__).resolve().parents[3]
WORKSPACES_DIR = PROJECT_ROOT / "reports" / "workspaces"


class ZipExtractionError(Exception):
    pass


class ZipValidationError(ZipExtractionError):
    pass


class CorruptedZipMemberError(ZipExtractionError):
    def __init__(self, member_name: str) -> None:
        super().__init__(f"Corrupted ZIP member detected: {member_name}")
        self.member_name = member_name


class UnsafeZipMemberError(ZipExtractionError):
    def __init__(self, member_name: str) -> None:
        super().__init__(f"Unsafe ZIP member path detected: {member_name}")
        self.member_name = member_name


class ZipExtractor:
    def __init__(self, workspace_root: Path = WORKSPACES_DIR) -> None:
        self.workspace_root = workspace_root

    def extract(self, analysis_id: str, upload_path: str | None) -> dict:
        zip_path = self._validate_zip_path(upload_path)
        workspace_path = self._create_workspace(analysis_id)

        try:
            with zipfile.ZipFile(zip_path) as archive:
                corrupted_member = archive.testzip()
                if corrupted_member:
                    raise CorruptedZipMemberError(corrupted_member)

                members = archive.infolist()
                self._validate_member_paths(workspace_path, members)
                archive.extractall(workspace_path)
        except ZipExtractionError:
            shutil.rmtree(workspace_path, ignore_errors=True)
            raise
        except zipfile.BadZipFile as exc:
            shutil.rmtree(workspace_path, ignore_errors=True)
            raise ZipValidationError("Uploaded file is not a readable ZIP archive.") from exc
        except Exception:
            shutil.rmtree(workspace_path, ignore_errors=True)
            raise

        extracted_files = [
            str(path)
            for path in workspace_path.rglob("*")
            if path.is_file()
        ]

        return {
            "zip_path": str(zip_path),
            "workspace_path": str(workspace_path),
            "extracted_paths": extracted_files,
            "file_count": len(extracted_files),
        }

    def _validate_zip_path(self, upload_path: str | None) -> Path:
        if not upload_path:
            raise ZipValidationError("No ZIP upload path was provided.")

        zip_path = Path(upload_path)
        if not zip_path.exists() or not zip_path.is_file():
            raise ZipValidationError(f"ZIP file does not exist: {zip_path}")

        if zip_path.suffix.lower() != ".zip":
            raise ZipValidationError("Upload path must point to a .zip file.")

        if not zipfile.is_zipfile(zip_path):
            raise ZipValidationError("Uploaded file is not a valid ZIP archive.")

        return zip_path

    def _create_workspace(self, analysis_id: str) -> Path:
        safe_analysis_id = "".join(
            character if character.isalnum() or character in {"-", "_"} else "-"
            for character in analysis_id
        ).strip("-")
        workspace_path = self.workspace_root / (safe_analysis_id or "analysis")

        if workspace_path.exists():
            shutil.rmtree(workspace_path)

        return ensure_directory(workspace_path)

    def _validate_member_paths(
        self,
        workspace_path: Path,
        members: list[zipfile.ZipInfo],
    ) -> None:
        workspace_root = workspace_path.resolve()

        for member in members:
            target_path = (workspace_path / member.filename).resolve()
            if workspace_root != target_path and workspace_root not in target_path.parents:
                raise UnsafeZipMemberError(member.filename)
