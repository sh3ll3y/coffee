"""Input validation utilities."""

import mimetypes
from typing import Optional

from src.config import settings
from src.utils.errors import ValidationError


def validate_file_size(file_size: int) -> None:
    """Validate file size is within limits."""
    max_size = settings.max_file_size_mb * 1024 * 1024  # Convert to bytes
    if file_size > max_size:
        raise ValidationError(f"File size exceeds {settings.max_file_size_mb}MB limit")


def validate_file_type(filename: str) -> None:
    """Validate file type is allowed."""
    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type not in settings.allowed_image_types:
        allowed = ", ".join(settings.allowed_image_types)
        raise ValidationError(f"File type not allowed. Allowed types: {allowed}")


def validate_s3_key(s3_key: str) -> None:
    """Validate S3 key format and safety."""
    if not s3_key or not isinstance(s3_key, str):
        raise ValidationError("Invalid S3 key")
    
    # Check for path traversal attempts
    if ".." in s3_key or s3_key.startswith("/"):
        raise ValidationError("Invalid S3 key format")
    
    # Check minimum length
    if len(s3_key) < 10:
        raise ValidationError("S3 key too short")


def validate_comment_length(comment: str) -> None:
    """Validate comment length."""
    if len(comment) > settings.max_comment_length:
        raise ValidationError(
            f"Comment exceeds {settings.max_comment_length} character limit"
        )


def validate_pagination_cursor(cursor: Optional[str]) -> None:
    """Validate pagination cursor format."""
    if cursor is None:
        return
    
    if not isinstance(cursor, str) or len(cursor) == 0:
        raise ValidationError("Invalid cursor format")
    
    # Basic base64 validation
    try:
        import base64
        base64.b64decode(cursor)
    except Exception:
        raise ValidationError("Invalid cursor encoding")