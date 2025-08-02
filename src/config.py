"""Configuration management for the Coffee backend."""

import os
from typing import Optional

from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # AWS Configuration
    aws_region: str = "us-east-1"
    aws_profile: Optional[str] = None
    
    # DynamoDB
    dynamodb_table_name: str = "coffee-table"
    
    # S3
    s3_bucket_name: str = "coffee-uploads"
    s3_presigned_url_expiry: int = 900  # 15 minutes
    
    # Rekognition
    rekognition_collection_id: str = "coffee-faces"
    face_match_threshold: float = 90.0
    gender_confidence_threshold: float = 95.0
    
    # JWT
    jwt_secret_key: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24
    
    # Flask
    flask_env: str = "production"
    flask_debug: bool = False
    
    # Text Moderation
    comprehend_endpoint_name: Optional[str] = None
    max_comment_length: int = 250
    
    # File Upload Limits
    max_file_size_mb: int = 5
    allowed_image_types: list[str] = ["image/jpeg", "image/png"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()