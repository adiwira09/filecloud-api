from abc import ABC, abstractmethod
from typing import BinaryIO

class StorageService(ABC):
    @abstractmethod
    def upload(self, file: BinaryIO, object_key: str, content_type: str | None = None) -> None:
        pass

    @abstractmethod
    def delete(self, object_key: str) -> None:
        pass

    @abstractmethod
    def exists(self, object_key: str) -> bool:
        pass

    @abstractmethod
    def get_download_url(self, object_key: str, expiration: int = 3600) -> str:
        pass

    @abstractmethod
    def get_upload_url(self, object_key: str, expiration: int = 3600, content_type: str | None = None) -> str:
        pass

    @abstractmethod
    def download(self, object_key: str) -> BinaryIO:
        pass