"""User blueprint for user profile operations."""

from flask import Blueprint, jsonify
from datetime import datetime

from src.models.auth import UserProfile
from src.services.dynamodb import DynamoDBService
from src.utils.auth import require_auth, get_current_user_id
from src.utils.errors import NotFoundError

user_bp = Blueprint("user", __name__)


@user_bp.route("/me", methods=["GET"])
@require_auth
def get_user_profile() -> tuple[dict, int]:
    """Get current user's profile."""
    user_id = get_current_user_id()
    
    # Get user from database
    db_service = DynamoDBService()
    user = db_service.get_user_by_id(user_id)
    
    if not user:
        raise NotFoundError("User not found")
    
    # Create response
    profile = UserProfile(
        user_id=user_id,
        username=user["username"],
        created=datetime.fromisoformat(user["created"]),
        ratings=user.get("ratings_count", 0)
    )
    
    return jsonify(profile.dict(by_alias=True)), 200