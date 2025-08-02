"""Authentication-related Pydantic models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """User registration request model."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)
    selfie_key: str = Field(..., alias="selfieKey")


class LoginRequest(BaseModel):
    """User login request model."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """JWT token response model."""
    token: str
    user_id: str = Field(..., alias="userId")


class UserProfile(BaseModel):
    """User profile model."""
    user_id: str = Field(..., alias="userId")
    username: str
    created: datetime
    ratings: int