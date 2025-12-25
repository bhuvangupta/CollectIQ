from typing import Optional, BinaryIO
from minio import Minio
from minio.error import S3Error
import io
import uuid
from datetime import timedelta

from app.core.config import settings


class FileService:
    """Service for file storage using MinIO."""

    def __init__(self):
        self.client = Minio(
            f"{settings.minio_host}:{settings.minio_port}",
            access_key=settings.minio_root_user,
            secret_key=settings.minio_root_password,
            secure=settings.minio_secure
        )
        self.bucket = settings.minio_bucket
        self._ensure_bucket()

    def _ensure_bucket(self):
        """Ensure the bucket exists."""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except S3Error as e:
            print(f"Error ensuring bucket: {e}")

    def upload_file(
        self,
        file_data: BinaryIO,
        file_name: str,
        content_type: str = "application/octet-stream",
        folder: str = ""
    ) -> str:
        """Upload a file and return its path."""
        # Generate unique file name
        ext = file_name.split(".")[-1] if "." in file_name else ""
        unique_name = f"{uuid.uuid4()}.{ext}" if ext else str(uuid.uuid4())
        object_name = f"{folder}/{unique_name}" if folder else unique_name

        # Get file size
        file_data.seek(0, 2)
        file_size = file_data.tell()
        file_data.seek(0)

        try:
            self.client.put_object(
                self.bucket,
                object_name,
                file_data,
                file_size,
                content_type=content_type
            )
            return object_name
        except S3Error as e:
            raise Exception(f"Failed to upload file: {e}")

    def upload_bytes(
        self,
        data: bytes,
        file_name: str,
        content_type: str = "application/octet-stream",
        folder: str = ""
    ) -> str:
        """Upload bytes and return the path."""
        file_data = io.BytesIO(data)
        return self.upload_file(file_data, file_name, content_type, folder)

    def download_file(self, object_name: str) -> bytes:
        """Download a file and return its contents."""
        try:
            response = self.client.get_object(self.bucket, object_name)
            return response.read()
        except S3Error as e:
            raise Exception(f"Failed to download file: {e}")
        finally:
            response.close()
            response.release_conn()

    def get_presigned_url(
        self,
        object_name: str,
        expires: timedelta = timedelta(hours=1)
    ) -> str:
        """Get a presigned URL for file access."""
        try:
            return self.client.presigned_get_object(
                self.bucket,
                object_name,
                expires=expires
            )
        except S3Error as e:
            raise Exception(f"Failed to generate presigned URL: {e}")

    def delete_file(self, object_name: str) -> bool:
        """Delete a file."""
        try:
            self.client.remove_object(self.bucket, object_name)
            return True
        except S3Error as e:
            print(f"Failed to delete file: {e}")
            return False

    def file_exists(self, object_name: str) -> bool:
        """Check if a file exists."""
        try:
            self.client.stat_object(self.bucket, object_name)
            return True
        except S3Error:
            return False


# Singleton instance
file_service = FileService()
