"""Authentication blueprint."""

from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from src.models.auth import RegisterRequest, LoginRequest, TokenResponse
from src.services.dynamodb import DynamoDBService
from src.services.rekognition import RekognitionService
from src.utils.auth import hash_password, verify_password, generate_jwt_token
from src.utils.errors import ConflictError, AuthenticationError, InvalidGenderError
from src.utils.validation import validate_s3_key

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register() -> tuple[dict, int]:
    """Register a new user with men-only verification."""
    try:
        # Parse request
        data = RegisterRequest(**request.get_json())
    except ValidationError as e:
        raise ValidationError(e.errors())
    
    # Validate selfie S3 key
    validate_s3_key(data.selfie_key)
    
    # Initialize services
    db_service = DynamoDBService()
    rekognition_service = RekognitionService()
    
    # Check if username already exists
    if db_service.username_exists(data.username):
        raise ConflictError("Username already exists", "USERNAME_EXISTS")
    
    # Verify gender using Rekognition
    if not rekognition_service.verify_male_gender(data.selfie_key):
        raise InvalidGenderError()
    
    # Hash password and create user
    password_hash = hash_password(data.password)
    user_id = db_service.create_user(data.username, password_hash)
    
    # Generate JWT token
    token = generate_jwt_token(user_id)
    
    # Return response
    response = TokenResponse(token=token, user_id=user_id)
    return jsonify(response.dict(by_alias=True)), 201


@auth_bp.route("/login", methods=["POST"])
def login() -> tuple[dict, int]:
    """Login a user and return JWT token."""
    try:
        # Parse request
        data = LoginRequest(**request.get_json())
    except ValidationError as e:
        raise ValidationError(e.errors())
    
    # Initialize service
    db_service = DynamoDBService()
    
    # Get user by username
    user = db_service.get_user_by_username(data.username)
    if not user:
        raise AuthenticationError()
    
    # Verify password
    if not verify_password(data.password, user["password_hash"]):
        raise AuthenticationError()
    
    # Extract user ID from PK
    user_id = user["PK"].replace("USER#", "")
    
    # Generate JWT token
    token = generate_jwt_token(user_id)
    
    # Return response
    response = TokenResponse(token=token, user_id=user_id)
    return jsonify(response.dict(by_alias=True)), 200