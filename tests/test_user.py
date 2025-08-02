"""Tests for user endpoints."""

import pytest

from src.services.dynamodb import DynamoDBService
from src.utils.auth import hash_password


class TestUserEndpoints:
    """Test user endpoints."""
    
    def test_get_profile_success(self, client, auth_token, setup_dynamodb):
        """Test successful user profile retrieval."""
        response = client.get("/me", 
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert "userId" in data
        assert "username" in data
        assert "created" in data
        assert "ratings" in data
        assert data["username"] == "testuser"
    
    def test_get_profile_unauthorized(self, client, setup_dynamodb):
        """Test user profile without authentication."""
        response = client.get("/me")
        
        assert response.status_code == 401
        data = response.get_json()
        assert data["error"] == "BAD_CREDENTIALS"
    
    def test_get_profile_invalid_token(self, client, setup_dynamodb):
        """Test user profile with invalid token."""
        response = client.get("/me",
            headers={"Authorization": "Bearer invalid-token"}
        )
        
        assert response.status_code == 401
        data = response.get_json()
        assert data["error"] == "BAD_CREDENTIALS"