from io import BytesIO
from typing import BinaryIO
from datetime import timedelta

from google.cloud import storage

from services.storage.base import StorageService

class GCSStorageService(StorageService):
    def __init__(
            self,
            bucket_name: str,
    ):
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

    def upload(
            self,
            file: BinaryIO,
            object_key: str,
            content_type: str | None = None
    ) -> None:
        blob = self.bucket.blob(object_key)
        blob.upload_from_file(file, content_type=content_type)

    def delete(self, object_key: str) -> None:
        blob = self.bucket.blob(object_key)

        if blob.exists():
            blob.delete()

    def exists(self, object_key: str) -> bool:
        blob = self.bucket.blob(object_key)
        return blob.exists()

    def get_download_url(
            self, 
            object_key: str, 
            expiration: int = 3600,
            download: bool = False,
            filename: str | None = None
    ) -> str:

        blob = self.bucket.blob(object_key)
        response_disposition = None

        if download and filename:
            response_disposition = f'attachment; filename="{filename}"'

        url = blob.generate_signed_url(version='v4', expiration=timedelta(seconds=expiration), method='GET', response_disposition=response_disposition)
        return url

    def get_upload_url(
            self, 
            object_key: str, 
            expiration: int = 3600, 
            content_type: str | None = None
    ) -> str:
        blob = self.bucket.blob(object_key)
        url = blob.generate_signed_url(
            version='v4', 
            expiration=timedelta(seconds=expiration), 
            method='PUT', 
            content_type=content_type
        )
        return url
    
    def download(self, object_key: str) -> BytesIO:
        blob = self.bucket.blob(object_key)

        if not blob.exists():
            raise FileNotFoundError(f"File with object key '{object_key}' not found in GCS bucket")

        file_stream = BytesIO()
        blob.download_to_file(file_stream)
        file_stream.seek(0)

        return file_stream