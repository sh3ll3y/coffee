"""Friends blueprint for friend management and rating."""

from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from typing import Optional

from src.models.friends import (
    VerifyRequest, VerifyResponse, RateRequest, RateResponse,
    SearchResponse, FriendSearchItem, FriendProfile, Rating,
    FriendPhotosResponse
)
from src.services.dynamodb import DynamoDBService
from src.services.rekognition import RekognitionService
from src.services.s3 import S3Service
from src.services.comprehend import ComprehendService
from src.utils.auth import require_auth, get_current_user_id
from src.utils.errors import NotFoundError, FaceVerificationError
from src.utils.validation import validate_s3_key, validate_comment_length, validate_pagination_cursor

friends_bp = Blueprint("friends", __name__)


@friends_bp.route("/verify", methods=["POST"])
@require_auth
def verify_friend() -> tuple[dict, int]:
    """Verify friend photos and create/link friend record."""
    try:
        # Parse request
        data = VerifyRequest(**request.get_json())
    except ValidationError as e:
        raise ValidationError(e.errors())
    
    # Validate S3 keys
    validate_s3_key(data.friend_photo_key)
    validate_s3_key(data.duo_photo_key)
    
    user_id = get_current_user_id()
    
    # Initialize services
    db_service = DynamoDBService()
    rekognition_service = RekognitionService()
    s3_service = S3Service()
    
    # Verify both photos exist in S3
    if not s3_service.check_object_exists(data.friend_photo_key):
        raise FaceVerificationError("Friend photo not found")
    
    if not s3_service.check_object_exists(data.duo_photo_key):
        raise FaceVerificationError("Duo photo not found")
    
    # Detect face liveness in both images
    if not rekognition_service.detect_face_liveness(data.friend_photo_key):
        raise FaceVerificationError("Friend photo failed liveness check")
    
    if not rekognition_service.detect_face_liveness(data.duo_photo_key):
        raise FaceVerificationError("Duo photo failed liveness check")
    
    # Compare faces to ensure friend appears in both photos
    similarity = rekognition_service.compare_faces(data.friend_photo_key, data.duo_photo_key)
    if similarity < 80.0:  # Threshold for same person
        raise FaceVerificationError("Friend not found in both photos")
    
    # Search for existing friend in collection
    existing_face_id = rekognition_service.search_faces_in_collection(data.friend_photo_key)
    
    if existing_face_id:
        # Use existing friend
        friend_id = rekognition_service.get_face_id_hash(existing_face_id)
        
        # Add new photo to existing friend
        db_service.add_friend_photo(friend_id, data.friend_photo_key, user_id)
        db_service.add_friend_photo(friend_id, data.duo_photo_key, user_id)
    else:
        # Create new friend
        friend_id = db_service.create_friend(
            data.friend_name,
            data.friend_city,
            data.friend_photo_key,
            user_id
        )
        
        # Add friend to Rekognition collection
        face_id = rekognition_service.add_face_to_collection(
            data.friend_photo_key,
            friend_id
        )
        
        # Store duo photo as well
        db_service.add_friend_photo(friend_id, data.duo_photo_key, user_id)
    
    # Return response
    response = VerifyResponse(friend_id=friend_id)
    return jsonify(response.dict(by_alias=True)), 201


@friends_bp.route("/<friend_id>/rate", methods=["POST"])
@require_auth
def rate_friend(friend_id: str) -> tuple[dict, int]:
    """Add a rating and comment for a friend."""
    try:
        # Parse request
        data = RateRequest(**request.get_json())
    except ValidationError as e:
        raise ValidationError(e.errors())
    
    # Validate comment length
    validate_comment_length(data.comment)
    
    user_id = get_current_user_id()
    
    # Initialize services
    db_service = DynamoDBService()
    comprehend_service = ComprehendService()
    
    # Verify friend exists
    friend = db_service.get_friend(friend_id)
    if not friend:
        raise NotFoundError("Friend not found")
    
    # Moderate comment text
    comprehend_service.moderate_comment(data.comment)
    
    # Create rating
    rating_id = db_service.create_rating(friend_id, user_id, data.score, data.comment)
    
    # Update friend's aggregate rating
    current_avg = float(friend.get("avg_rating", 0))
    current_count = friend.get("num_ratings", 0)
    
    new_count = current_count + 1
    new_avg = ((current_avg * current_count) + data.score) / new_count
    
    db_service.update_friend_rating(friend_id, new_avg, new_count)
    
    # Increment user's ratings count
    db_service.increment_user_ratings_count(user_id)
    
    # Return response
    response = RateResponse(rating_id=rating_id)
    return jsonify(response.dict(by_alias=True)), 201


@friends_bp.route("/search", methods=["GET"])
def search_friends() -> tuple[dict, int]:
    """Search friends by name and city with pagination."""
    # Parse query parameters
    name_prefix = request.args.get("name")
    city_prefix = request.args.get("city")
    cursor = request.args.get("cursor")
    
    # Validate cursor
    validate_pagination_cursor(cursor)
    
    # Initialize service
    db_service = DynamoDBService()
    
    # Search friends
    friends, next_cursor = db_service.search_friends(
        name_prefix=name_prefix,
        city_prefix=city_prefix,
        cursor=cursor,
        limit=20
    )
    
    # Convert to response format
    items = []
    for friend in friends:
        # Get first photo as thumbnail
        photos, _ = db_service.get_friend_photos(
            friend["PK"].replace("FRIEND#", ""),
            limit=1
        )
        thumbnail_key = photos[0] if photos else ""
        
        item = FriendSearchItem(
            friend_id=friend["PK"].replace("FRIEND#", ""),
            name=friend["name"],
            city=friend["city"],
            avg_rating=float(friend["avg_rating"]),
            num_ratings=friend["num_ratings"],
            thumbnail_key=thumbnail_key
        )
        items.append(item)
    
    # Return response
    response = SearchResponse(items=items, next_cursor=next_cursor)
    return jsonify(response.dict(by_alias=True)), 200


@friends_bp.route("/<friend_id>", methods=["GET"])
def get_friend_profile(friend_id: str) -> tuple[dict, int]:
    """Get complete friend profile with ratings."""
    # Initialize service
    db_service = DynamoDBService()
    
    # Get friend metadata
    friend = db_service.get_friend(friend_id)
    if not friend:
        raise NotFoundError("Friend not found")
    
    # Get friend photos
    photos, _ = db_service.get_friend_photos(friend_id, limit=50)
    
    # Get friend ratings
    rating_records = db_service.get_friend_ratings(friend_id)
    
    ratings = []
    for record in rating_records:
        rating = Rating(
            user_id=record["user_id"],
            score=record["score"],
            comment=record["comment"],
            created=record["created"]
        )
        ratings.append(rating)
    
    # Create response
    profile = FriendProfile(
        friend_id=friend_id,
        name=friend["name"],
        city=friend["city"],
        photos=photos,
        avg_rating=float(friend["avg_rating"]),
        num_ratings=friend["num_ratings"],
        ratings=ratings
    )
    
    return jsonify(profile.dict(by_alias=True)), 200


@friends_bp.route("/<friend_id>/photos", methods=["GET"])
def get_friend_photos(friend_id: str) -> tuple[dict, int]:
    """Get paginated photos for a friend."""
    # Parse query parameters
    cursor = request.args.get("cursor")
    
    # Validate cursor
    validate_pagination_cursor(cursor)
    
    # Initialize service
    db_service = DynamoDBService()
    
    # Verify friend exists
    friend = db_service.get_friend(friend_id)
    if not friend:
        raise NotFoundError("Friend not found")
    
    # Get photos with pagination
    photos, next_cursor = db_service.get_friend_photos(friend_id, cursor, limit=20)
    
    # Return response
    response = FriendPhotosResponse(items=photos, next_cursor=next_cursor)
    return jsonify(response.dict(by_alias=True)), 200