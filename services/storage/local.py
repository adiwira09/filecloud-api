from io import BytesIO
from typing import BinaryIO
from pathlib import Path

from services.storage.base import StorageService

class LocalStorage(StorageService):

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(
            parents=True,
            exist_ok=True
        )

    def _get_path(self, object_key: str) -> Path:
        base = self.base_path.resolve()
        path = (base / object_key).resolve()

        if base not in path.parents and base != path:
            raise ValueError("Invalid object key: path traversal detected")
        
        return path

    def upload(
        self,
        file: BinaryIO,
        object_key: str,
        content_type: str | None = None
    ) -> None:

        file_path = self._get_path(object_key)

        file_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with open(file_path, "wb") as buffer:
            while chunk := file.read(1024 * 1024):
                buffer.write(chunk)

    def delete(self, object_key: str) -> None:
        file_path = self._get_path(object_key)

        if file_path.exists():
            file_path.unlink()

    def exists(self, object_key: str) -> bool:
        return self._get_path(object_key).exists()

    def get_file_path(self, object_key: str) -> str:
        return str(self._get_path(object_key))
    
    def get_download_url(
        self,
        object_key: str,
        expiration: int = 3600
    ) -> str:
        raise NotImplementedError("Local storage does not support generating download URL")

    def download(self, object_key: str) -> BytesIO:
        file_path = self._get_path(object_key)

        if not file_path.is_file():
            raise FileNotFoundError(f"File tidak ditemukan: {object_key}")

        with open(file_path, "rb") as file:
            return BytesIO(file.read())