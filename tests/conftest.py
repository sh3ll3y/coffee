"""Test configuration and fixtures."""

import pytest
import os
from unittest.mock import patch
from moto import mock_dynamodb, mock_s3, mock_rekognition

from src.app import create_app
from src.config import Settings


@pytest.fixture
def app():
    """Create Flask app for testing."""
    # Override settings for testing
    test_settings = Settings(
        dynamodb_table_name="test-coffee-table",
        s3_bucket_name="test-coffee-uploads",
        rekognition_collection_id="test-coffee-faces",
        jwt_secret_key="test-secret-key",
        flask_env="testing",
        flask_debug=True
    )
    
    with patch("src.config.settings", test_settings):
        app = create_app()
        app.config["TESTING"] = True
        yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def mock_aws():
    """Mock AWS services."""
    with mock_dynamodb(), mock_s3(), mock_rekognition():
        yield


@pytest.fixture
def setup_dynamodb(mock_aws):
    """Set up DynamoDB table for testing."""
    import boto3
    
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    
    # Create table
    table = dynamodb.create_table(
        TableName="test-coffee-table",
        KeySchema=[
            {
                "AttributeName": "PK",
                "KeyType": "HASH"
            },
            {
                "AttributeName": "SK", 
                "KeyType": "RANGE"
            }
        ],
        AttributeDefinitions=[
            {
                "AttributeName": "PK",
                "AttributeType": "S"
            },
            {
                "AttributeName": "SK",
                "AttributeType": "S"
            },
            {
                "AttributeName": "username",
                "AttributeType": "S"
            },
            {
                "AttributeName": "name_city",
                "AttributeType": "S"
            }
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "username-index",
                "KeySchema": [
                    {
                        "AttributeName": "username",
                        "KeyType": "HASH"
                    }
                ],
                "Projection": {
                    "ProjectionType": "ALL"
                },
                "BillingMode": "PAY_PER_REQUEST"
            },
            {
                "IndexName": "name_city-index",
                "KeySchema": [
                    {
                        "AttributeName": "name_city",
                        "KeyType": "HASH"
                    }
                ],
                "Projection": {
                    "ProjectionType": "ALL"
                },
                "BillingMode": "PAY_PER_REQUEST"
            }
        ],
        BillingMode="PAY_PER_REQUEST"
    )
    
    # Wait for table to be created
    table.wait_until_exists()
    
    yield table


@pytest.fixture
def setup_s3(mock_aws):
    """Set up S3 bucket for testing."""
    import boto3
    
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="test-coffee-uploads")
    
    yield s3


@pytest.fixture
def setup_rekognition(mock_aws):
    """Set up Rekognition collection for testing."""
    import boto3
    
    rekognition = boto3.client("rekognition", region_name="us-east-1")
    
    try:
        rekognition.create_collection(CollectionId="test-coffee-faces")
    except rekognition.exceptions.ResourceAlreadyExistsException:
        pass
    
    yield rekognition


@pytest.fixture
def auth_token(client, setup_dynamodb):
    """Create a test user and return auth token."""
    from src.services.dynamodb import DynamoDBService
    from src.utils.auth import hash_password, generate_jwt_token
    
    db_service = DynamoDBService()
    user_id = db_service.create_user("testuser", hash_password("testpass123"))
    
    return generate_jwt_token(user_id)