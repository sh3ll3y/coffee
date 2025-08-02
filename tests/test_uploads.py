"""Tests for uploads endpoints."""

import pytest
from unittest.mock import patch


class TestUploadsEndpoints:
    """Test uploads endpoints."""
    
    def test_presign_success(self, client, setup_s3, auth_token):
        """Test successful presigned URL generation."""
        with patch("src.services.s3.S3Service.generate_presigned_upload_url") as mock_presign:
            mock_presign.return_value = {
                "upload_url": "https://s3.amazonaws.com/test-bucket/upload",
                "file_key": "friend/test-file.jpg",
                "expires_in": 900,
                "fields": {}
            }
            
            response = client.post("/uploads/presign",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={"kind": "friend"}
            )
            
            assert response.status_code == 200
            data = response.get_json()
            assert "uploadUrl" in data
            assert "fileKey" in data
            assert "expiresIn" in data
    
    def test_presign_duo_kind(self, client, setup_s3, auth_token):
        """Test presigned URL for duo photo."""
        with patch("src.services.s3.S3Service.generate_presigned_upload_url") as mock_presign:
            mock_presign.return_value = {
                "upload_url": "https://s3.amazonaws.com/test-bucket/upload",
                "file_key": "duo/test-file.jpg", 
                "expires_in": 900,
                "fields": {}
            }
            
            response = client.post("/uploads/presign",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={"kind": "duo"}
            )
            
            assert response.status_code == 200
            data = response.get_json()
            assert "uploadUrl" in data
            assert "fileKey" in data
    
    def test_presign_invalid_kind(self, client, auth_token):
        """Test presigned URL with invalid kind."""
        response = client.post("/uploads/presign",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"kind": "invalid"}
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data["error"] == "VALIDATION_ERROR"
    
    def test_presign_unauthorized(self, client):
        """Test presigned URL without authentication."""
        response = client.post("/uploads/presign", json={"kind": "friend"})
        
        assert response.status_code == 401
        data = response.get_json()
        assert data["error"] == "BAD_CREDENTIALS"