"""Friend-related Pydantic models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, validator


class VerifyRequest(BaseModel):
    """Friend photo verification request model."""
    friend_photo_key: str = Field(..., alias="friendPhotoKey")
    duo_photo_key: str = Field(..., alias="duoPhotoKey")
    friend_name: str = Field(..., alias="friendName", min_length=1, max_length=100)
    friend_city: str = Field(..., alias="friendCity", min_length=1, max_length=100)


class VerifyResponse(BaseModel):
    """Friend verification response model."""
    friend_id: str = Field(..., alias="friendId")


class RateRequest(BaseModel):
    """Friend rating request model."""
    score: int = Field(..., ge=1, le=10)
    comment: str = Field(..., max_length=250)


class RateResponse(BaseModel):
    """Friend rating response model."""
    rating_id: str = Field(..., alias="ratingId")


class FriendSearchItem(BaseModel):
    """Friend search result item."""
    friend_id: str = Field(..., alias="friendId")
    name: str
    city: str
    avg_rating: float = Field(..., alias="avgRating")
    num_ratings: int = Field(..., alias="numRatings")
    thumbnail_key: str = Field(..., alias="thumbnailKey")


class SearchResponse(BaseModel):
    """Friend search response model."""
    items: list[FriendSearchItem]
    next_cursor: Optional[str] = Field(None, alias="nextCursor")


class Rating(BaseModel):
    """Individual rating model."""
    user_id: str = Field(..., alias="userId")
    score: int
    comment: str
    created: datetime


class FriendProfile(BaseModel):
    """Complete friend profile model."""
    friend_id: str = Field(..., alias="friendId")
    name: str
    city: str
    photos: list[str]
    avg_rating: float = Field(..., alias="avgRating")
    num_ratings: int = Field(..., alias="numRatings")
    ratings: list[Rating]


class FriendPhotosResponse(BaseModel):
    """Friend photos pagination response."""
    items: list[str]
    next_cursor: Optional[str] = Field(None, alias="nextCursor")