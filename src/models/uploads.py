"""Upload-related Pydantic models."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class UploadKind(str, Enum):
    """Types of upload requests."""
    FRIEND = "friend"
    DUO = "duo"


class PresignRequest(BaseModel):
    """Presigned URL request model."""
    kind: UploadKind


class PresignResponse(BaseModel):
    """Presigned URL response model."""
    upload_url: str = Field(..., alias="uploadUrl")
    file_key: str = Field(..., alias="fileKey")
    expires_in: int = Field(..., alias="expiresIn")