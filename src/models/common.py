"""Common models and utilities."""

from typing import Any, Dict

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str
    message: str
    details: Dict[str, Any] = {}


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = "ok"