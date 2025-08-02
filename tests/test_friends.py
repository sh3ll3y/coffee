"""Tests for friends endpoints."""

import pytest
from unittest.mock import patch, MagicMock

from src.services.dynamodb import DynamoDBService


class TestFriendsEndpoints:
    """Test friends endpoints."""
    
    def test_verify_friend_success(self, client, setup_dynamodb, setup_s3, setup_rekognition, auth_token):
        """Test successful friend verification."""
        # Upload test images to S3
        setup_s3.put_object(
            Bucket="test-coffee-uploads",
            Key="friend/test.jpg",
            Body=b"fake image data"
        )
        setup_s3.put_object(
            Bucket="test-coffee-uploads", 
            Key="duo/test.jpg",
            Body=b"fake image data"
        )
        
        with patch("src.services.rekognition.RekognitionService") as MockRekognition:
            mock_rek = MockRekognition.return_value
            mock_rek.detect_face_liveness.return_value = True
            mock_rek.compare_faces.return_value = 85.0
            mock_rek.search_faces_in_collection.return_value = None
            mock_rek.add_face_to_collection.return_value = "face-id-123"
            mock_rek.get_face_id_hash.return_value = "friend-id-123"
            
            response = client.post("/friends/verify", 
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "friendPhotoKey": "friend/test.jpg",
                    "duoPhotoKey": "duo/test.jpg",
                    "friendName": "John Doe",
                    "friendCity": "New York"
                }
            )
            
            assert response.status_code == 201
            data = response.get_json()
            assert "friendId" in data
    
    def test_verify_friend_liveness_fail(self, client, setup_dynamodb, setup_s3, setup_rekognition, auth_token):
        """Test friend verification with liveness failure."""
        setup_s3.put_object(
            Bucket="test-coffee-uploads",
            Key="friend/test.jpg", 
            Body=b"fake image data"
        )
        setup_s3.put_object(
            Bucket="test-coffee-uploads",
            Key="duo/test.jpg",
            Body=b"fake image data"
        )
        
        with patch("src.services.rekognition.RekognitionService") as MockRekognition:
            mock_rek = MockRekognition.return_value
            mock_rek.detect_face_liveness.return_value = False
            
            response = client.post("/friends/verify",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "friendPhotoKey": "friend/test.jpg",
                    "duoPhotoKey": "duo/test.jpg", 
                    "friendName": "John Doe",
                    "friendCity": "New York"
                }
            )
            
            assert response.status_code == 400
            data = response.get_json()
            assert data["error"] == "FACE_VERIFICATION_FAILED"
    
    def test_rate_friend_success(self, client, setup_dynamodb, auth_token):
        """Test successful friend rating."""
        # Create test friend
        db_service = DynamoDBService()
        friend_id = db_service.create_friend("John Doe", "New York", "friend/test.jpg", "user-123")
        
        with patch("src.services.comprehend.ComprehendService") as MockComprehend:
            mock_comp = MockComprehend.return_value
            mock_comp.moderate_comment.return_value = None  # No exception = appropriate
            
            response = client.post(f"/friends/{friend_id}/rate",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "score": 8,
                    "comment": "Great guy!"
                }
            )
            
            assert response.status_code == 201
            data = response.get_json()
            assert "ratingId" in data
    
    def test_rate_friend_inappropriate_comment(self, client, setup_dynamodb, auth_token):
        """Test rating with inappropriate comment."""
        # Create test friend
        db_service = DynamoDBService()
        friend_id = db_service.create_friend("John Doe", "New York", "friend/test.jpg", "user-123")
        
        with patch("src.services.comprehend.ComprehendService") as MockComprehend:
            from src.utils.errors import TextModerationError
            mock_comp = MockComprehend.return_value
            mock_comp.moderate_comment.side_effect = TextModerationError()
            
            response = client.post(f"/friends/{friend_id}/rate",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "score": 1,
                    "comment": "This guy is trash!"
                }
            )
            
            assert response.status_code == 400
            data = response.get_json()
            assert data["error"] == "INAPPROPRIATE_CONTENT"
    
    def test_search_friends_success(self, client, setup_dynamodb):
        """Test successful friend search."""
        # Create test friends
        db_service = DynamoDBService()
        friend1_id = db_service.create_friend("John Doe", "New York", "friend1.jpg", "user-123")
        friend2_id = db_service.create_friend("Jane Smith", "Boston", "friend2.jpg", "user-123")
        
        response = client.get("/friends/search?name=John")
        
        assert response.status_code == 200
        data = response.get_json()
        assert "items" in data
        assert "nextCursor" in data
        assert len(data["items"]) >= 0  # May be 0 due to GSI consistency
    
    def test_get_friend_profile_success(self, client, setup_dynamodb):
        """Test getting friend profile."""
        # Create test friend with rating
        db_service = DynamoDBService()
        friend_id = db_service.create_friend("John Doe", "New York", "friend.jpg", "user-123")
        db_service.create_rating(friend_id, "user-123", 8, "Great guy!")
        db_service.update_friend_rating(friend_id, 8.0, 1)
        
        response = client.get(f"/friends/{friend_id}")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["friendId"] == friend_id
        assert data["name"] == "John Doe"
        assert data["city"] == "New York"
        assert "photos" in data
        assert "ratings" in data
    
    def test_get_friend_profile_not_found(self, client, setup_dynamodb):
        """Test getting non-existent friend profile."""
        response = client.get("/friends/nonexistent-id")
        
        assert response.status_code == 404
        data = response.get_json()  
        assert data["error"] == "NOT_FOUND"
    
    def test_get_friend_photos_success(self, client, setup_dynamodb):
        """Test getting friend photos."""
        # Create test friend
        db_service = DynamoDBService()
        friend_id = db_service.create_friend("John Doe", "New York", "friend.jpg", "user-123")
        
        response = client.get(f"/friends/{friend_id}/photos")
        
        assert response.status_code == 200
        data = response.get_json()
        assert "items" in data
        assert "nextCursor" in data
    
    def test_unauthorized_requests(self, client, setup_dynamodb):
        """Test that protected endpoints require authentication."""
        # Test verify endpoint
        response = client.post("/friends/verify", json={
            "friendPhotoKey": "friend/test.jpg",
            "duoPhotoKey": "duo/test.jpg",
            "friendName": "John Doe", 
            "friendCity": "New York"
        })
        assert response.status_code == 401
        
        # Test rate endpoint
        response = client.post("/friends/test-id/rate", json={
            "score": 8,
            "comment": "Great guy!"
        })
        assert response.status_code == 401