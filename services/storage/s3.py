from typing import BinaryIO
from io import BytesIO

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from services.storage.base import StorageService

class S3StorageService(StorageService):
    def __init__(
            self,
            endpoint_url: str,
            region_name: str,
            access_key: str,
            secret_key: str,
            bucket_name: str, 
    ):
        self.bucket_name = bucket_name
        self.client = boto3.client(
            's3', 
            endpoint_url=endpoint_url, 
            region_name=region_name, 
            aws_access_key_id=access_key, 
            aws_secret_access_key=secret_key,
            config=Config(signature_version='s3v4')
        )

    def upload(
            self, 
            file: BinaryIO,
            object_key: str,
            content_type: str | None = None
    ) -> None:
        
        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type

        self.client.upload_fileobj(file, self.bucket_name, object_key, ExtraArgs=extra_args)

    def delete(self, object_key: str) -> None:
        self.client.delete_object(Bucket=self.bucket_name, Key=object_key)

    def exists(self, object_key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=object_key)
            return True
        except ClientError as e:
            error_code = e.response.get(
                "Error", {}
            ).get("Code")

            if error_code in ("404", "NoSuchKey"):
                return False

            raise

    def get_download_url(
            self, 
            object_key: str, 
            expiration: int = 3600, 
            download: bool = False,
            filename: str | None = None
    ) -> str:

        params = {
            "Bucket": self.bucket_name,
            "Key": object_key
        }

        if download and filename:
            params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'
            
        try:
            response = self.client.generate_presigned_url(
                'get_object',
                Params=params,
                ExpiresIn=expiration
            )
        except ClientError as e:
            raise Exception(f"Error generating download URL: {e}")
        
        return response

    def get_upload_url(
        self,
        object_key: str,
        expiration: int = 3600,
        content_type: str | None = None
    ) -> str:
        params = {
            "Bucket": self.bucket_name,
            "Key": object_key
        }

        try:
            response = self.client.generate_presigned_url(
                'put_object',
                Params=params,
                ExpiresIn=expiration
            )
        except ClientError as e:
            raise Exception(f"Error generating upload URL: {e}")
        
        return response
    
    def download(self, object_key: str) -> BytesIO:
        response = self.client.get_object(
            Bucket=self.bucket_name,
            Key=object_key
        )

        return BytesIO(response["Body"].read())