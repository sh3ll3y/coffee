"""Authentication utilities for JWT and password handling."""

import uuid
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, Optional

import bcrypt
import jwt
from flask import request, g

from src.config import settings
from src.services.dynamodb import DynamoDBService
from src.utils.errors import AuthenticationError, AuthorizationError


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


def generate_jwt_token(user_id: str) -> str:
    """Generate a JWT token for a user."""
    payload = {
        "user_id": user_id,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=settings.jwt_expiry_hours),
        "jti": str(uuid.uuid4()),  # JWT ID for token uniqueness
    }
    
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token")


def get_current_user_id() -> str:
    """Get the current authenticated user ID from Flask's g object."""
    if not hasattr(g, "user_id"):
        raise AuthorizationError("No authenticated user")
    return g.user_id


def require_auth(f: Callable) -> Callable:
    """Decorator to require JWT authentication."""
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise AuthenticationError("No authorization header")
        
        # Extract Bearer token
        try:
            scheme, token = auth_header.split(" ", 1)
            if scheme.lower() != "bearer":
                raise AuthenticationError("Invalid authorization scheme")
        except ValueError:
            raise AuthenticationError("Invalid authorization header format")
        
        # Decode and validate token
        payload = decode_jwt_token(token)
        user_id = payload.get("user_id")
        
        if not user_id:
            raise AuthenticationError("Invalid token payload")
        
        # Verify user still exists
        db_service = DynamoDBService()
        user = db_service.get_user_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found")
        
        # Store user ID in Flask's g object
        g.user_id = user_id
        
        return f(*args, **kwargs)
    
    return decorated_function