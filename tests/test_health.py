"""Tests for health endpoint."""

import pytest


class TestHealthEndpoint:
    """Test health endpoint."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"