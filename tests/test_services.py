"""Tests for service modules."""

import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal

from src.services.dynamodb import DynamoDBService
from src.services.rekognition import RekognitionService
from src.services.s3 import S3Service
from src.services.comprehend import ComprehendService
from src.utils.auth import hash_password, verify_password, generate_jwt_token, decode_jwt_token
from src.utils.errors import InvalidGenderError, FaceVerificationError, TextModerationError


class TestDynamoDBService:
    """Test DynamoDB service."""
    
    def test_create_user(self, setup_dynamodb):
        """Test user creation."""
        service = DynamoDBService()
        user_id = service.create_user("testuser", "hashed_password")
        
        assert user_id is not None
        assert len(user_id) > 0
    
    def test_get_user_by_username(self, setup_dynamodb):
        """Test getting user by username.""" 
        service = DynamoDBService()
        user_id = service.create_user("testuser", "hashed_password")
        
        user = service.get_user_by_username("testuser")
        assert user is not None
        assert user["username"] == "testuser"
    
    def test_create_friend(self, setup_dynamodb):
        """Test friend creation."""
        service = DynamoDBService()
        friend_id = service.create_friend("John Doe", "New York", "photo.jpg", "user-123")
        
        assert friend_id is not None
        friend = service.get_friend(friend_id)
        assert friend["name"] == "John Doe"
        assert friend["city"] == "New York"


class TestAuthUtils:
    """Test authentication utilities."""
    
    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "testpassword123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert verify_password(password, hashed)
        assert not verify_password("wrongpassword", hashed)
    
    def test_jwt_tokens(self):
        """Test JWT token generation and validation."""
        user_id = "test-user-123"
        token = generate_jwt_token(user_id)
        
        assert token is not None
        assert len(token) > 0
        
        payload = decode_jwt_token(token)
        assert payload["user_id"] == user_id


class TestRekognitionService:
    """Test Rekognition service."""
    
    def test_verify_male_gender_success(self, setup_rekognition):
        """Test successful male gender verification."""
        service = RekognitionService()
        
        with patch.object(service.client, "detect_faces") as mock_detect:
            mock_detect.return_value = {
                "FaceDetails": [{
                    "Gender": {"Value": "Male", "Confidence": 96.0}
                }]
            }
            
            result = service.verify_male_gender("test/selfie.jpg")
            assert result is True
    
    def test_verify_male_gender_failure(self, setup_rekognition):
        """Test failed male gender verification."""
        service = RekognitionService()
        
        with patch.object(service.client, "detect_faces") as mock_detect:
            mock_detect.return_value = {
                "FaceDetails": [{
                    "Gender": {"Value": "Female", "Confidence": 98.0}
                }]
            }
            
            result = service.verify_male_gender("test/selfie.jpg")
            assert result is False
    
    def test_detect_face_liveness(self, setup_rekognition):
        """Test face liveness detection."""
        service = RekognitionService()
        
        with patch.object(service.client, "detect_faces") as mock_detect:
            mock_detect.return_value = {
                "FaceDetails": [{
                    "Quality": {"Brightness": 80.0, "Sharpness": 90.0}
                }]
            }
            
            result = service.detect_face_liveness("test/photo.jpg")
            assert result is True


class TestS3Service:
    """Test S3 service."""
    
    def test_generate_presigned_upload_url(self, setup_s3):
        """Test presigned URL generation."""
        service = S3Service()
        
        with patch.object(service.client, "generate_presigned_post") as mock_presign:
            mock_presign.return_value = {
                "url": "https://s3.amazonaws.com/test-bucket/upload",
                "fields": {"key": "friend/test.jpg"}
            }
            
            result = service.generate_presigned_upload_url("friend")
            
            assert "upload_url" in result
            assert "file_key" in result
            assert "expires_in" in result


class TestComprehendService:
    """Test Comprehend service."""
    
    def test_appropriate_text(self, mock_aws):
        """Test appropriate text detection."""
        service = ComprehendService()
        
        with patch.object(service.client, "detect_sentiment") as mock_sentiment, \
             patch.object(service.client, "detect_pii_entities") as mock_pii, \
             patch.object(service.client, "detect_key_phrases") as mock_phrases:
            
            mock_sentiment.return_value = {
                "Sentiment": "POSITIVE",
                "SentimentScore": {"Positive": 0.9, "Negative": 0.1}
            }
            mock_pii.return_value = {"Entities": []}
            mock_phrases.return_value = {"KeyPhrases": [{"Text": "great guy"}]}
            
            result = service.is_text_appropriate("This is a great guy!")
            assert result is True
    
    def test_inappropriate_text(self, mock_aws):
        """Test inappropriate text detection."""
        service = ComprehendService()
        
        with patch.object(service.client, "detect_sentiment") as mock_sentiment, \
             patch.object(service.client, "detect_pii_entities") as mock_pii, \
             patch.object(service.client, "detect_key_phrases") as mock_phrases:
            
            mock_sentiment.return_value = {
                "Sentiment": "NEGATIVE", 
                "SentimentScore": {"Positive": 0.1, "Negative": 0.9}
            }
            mock_pii.return_value = {"Entities": []}
            mock_phrases.return_value = {"KeyPhrases": [{"Text": "hate this guy"}]}
            
            result = service.is_text_appropriate("I hate this guy!")
            assert result is False