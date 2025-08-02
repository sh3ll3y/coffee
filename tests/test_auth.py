"""Tests for authentication endpoints."""

import pytest
from unittest.mock import patch, MagicMock

from src.services.dynamodb import DynamoDBService
from src.utils.auth import hash_password


class TestAuthEndpoints:
    """Test authentication endpoints."""
    
    def test_register_success(self, client, setup_dynamodb, setup_s3, setup_rekognition):
        """Test successful user registration."""
        with patch("src.services.rekognition.RekognitionService.verify_male_gender") as mock_verify:
            mock_verify.return_value = True
            
            response = client.post("/auth/register", json={
                "username": "newuser",
                "password": "password123",
                "selfieKey": "test/selfie.jpg"
            })
            
            assert response.status_code == 201
            data = response.get_json()
            assert "token" in data
            assert "userId" in data
    
    def test_register_username_exists(self, client, setup_dynamodb):
        """Test registration with existing username."""
        # Create existing user
        db_service = DynamoDBService()
        db_service.create_user("existinguser", hash_password("password"))
        
        with patch("src.services.rekognition.RekognitionService.verify_male_gender") as mock_verify:
            mock_verify.return_value = True
            
            response = client.post("/auth/register", json={
                "username": "existinguser",
                "password": "password123", 
                "selfieKey": "test/selfie.jpg"
            })
            
            assert response.status_code == 409
            data = response.get_json()
            assert data["error"] == "USERNAME_EXISTS"
    
    def test_register_invalid_gender(self, client, setup_dynamodb, setup_s3, setup_rekognition):
        """Test registration with invalid gender."""
        with patch("src.services.rekognition.RekognitionService.verify_male_gender") as mock_verify:
            mock_verify.return_value = False
            
            response = client.post("/auth/register", json={
                "username": "newuser",
                "password": "password123",
                "selfieKey": "test/selfie.jpg"
            })
            
            assert response.status_code == 400
            data = response.get_json()
            assert data["error"] == "INVALID_GENDER"
    
    def test_register_validation_error(self, client, setup_dynamodb):
        """Test registration with invalid input."""
        response = client.post("/auth/register", json={
            "username": "ab",  # Too short
            "password": "123",  # Too short
            "selfieKey": "test/selfie.jpg"
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert data["error"] == "VALIDATION_ERROR"
    
    def test_login_success(self, client, setup_dynamodb):
        """Test successful login."""
        # Create test user
        db_service = DynamoDBService()
        db_service.create_user("testuser", hash_password("password123"))
        
        response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "password123"
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert "token" in data
        assert "userId" in data
    
    def test_login_invalid_username(self, client, setup_dynamodb):
        """Test login with invalid username."""
        response = client.post("/auth/login", json={
            "username": "nonexistent",
            "password": "password123"
        })
        
        assert response.status_code == 401
        data = response.get_json()
        assert data["error"] == "BAD_CREDENTIALS"
    
    def test_login_invalid_password(self, client, setup_dynamodb):
        """Test login with invalid password."""
        # Create test user
        db_service = DynamoDBService()
        db_service.create_user("testuser", hash_password("password123"))
        
        response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
        data = response.get_json()
        assert data["error"] == "BAD_CREDENTIALS"