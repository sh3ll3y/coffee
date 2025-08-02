"""Amazon S3 service for file uploads and presigned URLs."""

import uuid
from typing import Dict, Any

import boto3
from botocore.exceptions import ClientError

from src.config import settings
from src.utils.errors import CoffeeException


class S3Service:
    """Service for Amazon S3 operations."""
    
    def __init__(self) -> None:
        """Initialize S3 service."""
        self.client = boto3.client("s3", region_name=settings.aws_region)
        self.bucket_name = settings.s3_bucket_name
    
    def generate_presigned_upload_url(self, upload_kind: str) -> Dict[str, Any]:
        """Generate a presigned URL for file upload."""
        # Generate unique file key
        file_key = f"{upload_kind}/{uuid.uuid4()}.jpg"
        
        try:
            # Generate presigned POST URL
            response = self.client.generate_presigned_post(
                Bucket=self.bucket_name,
                Key=file_key,
                Fields={"Content-Type": "image/jpeg"},
                Conditions=[
                    {"Content-Type": "image/jpeg"},
                    ["content-length-range", 0, settings.max_file_size_mb * 1024 * 1024]
                ],
                ExpiresIn=settings.s3_presigned_url_expiry
            )
            
            return {
                "upload_url": response["url"],
                "file_key": file_key,
                "expires_in": settings.s3_presigned_url_expiry,
                "fields": response["fields"]
            }
            
        except ClientError as e:
            raise CoffeeException(f"Failed to generate presigned URL: {e}")
    
    def generate_presigned_download_url(self, s3_key: str) -> str:
        """Generate a presigned URL for file download."""
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": s3_key},
                ExpiresIn=3600  # 1 hour
            )
            return url
        except ClientError as e:
            raise CoffeeException(f"Failed to generate download URL: {e}")
    
    def check_object_exists(self, s3_key: str) -> bool:
        """Check if an object exists in S3."""
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise CoffeeException(f"Failed to check object existence: {e}")
    
    def get_object_size(self, s3_key: str) -> int:
        """Get the size of an S3 object in bytes."""
        try:
            response = self.client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return response["ContentLength"]
        except ClientError as e:
            raise CoffeeException(f"Failed to get object size: {e}")