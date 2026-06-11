from pydantic import BaseModel


class UploadResponse(BaseModel):
    filename: str
    original_filename: str
    size_bytes: int
    path: str
