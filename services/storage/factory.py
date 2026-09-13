from core.config import (
    STORAGE_PROVIDER,
    LOCAL_STORAGE_PATH,
    S3_ENDPOINT_URL,
    S3_REGION_NAME,
    S3_ACCESS_KEY,
    S3_SECRET_KEY,
    S3_BUCKET_NAME,
    GCS_BUCKET_NAME
)

from services.storage.base import StorageService
from services.storage.local import LocalStorage
from services.storage.s3 import S3StorageService
from services.storage.gcs import GCSStorageService

def get_storage_service() -> StorageService:
    provider = STORAGE_PROVIDER.lower()

    if provider == "local":
        return LocalStorage(base_path=LOCAL_STORAGE_PATH)

    if provider == "s3":
        return S3StorageService(
            endpoint_url=S3_ENDPOINT_URL,
            region_name=S3_REGION_NAME,
            access_key=S3_ACCESS_KEY,
            secret_key=S3_SECRET_KEY,
            bucket_name=S3_BUCKET_NAME
        )
    
    if provider == "gcs":
        return GCSStorageService(
            bucket_name=GCS_BUCKET_NAME
        )

    raise ValueError(f"Unsupported storage provider: {provider}")