"""DynamoDB service for single-table design."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

from src.config import settings


class DynamoDBService:
    """Service for DynamoDB operations using single-table design."""
    
    def __init__(self) -> None:
        """Initialize DynamoDB service."""
        self.dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
        self.table = self.dynamodb.Table(settings.dynamodb_table_name)
    
    def create_user(self, username: str, password_hash: str) -> str:
        """Create a new user record."""
        user_id = str(uuid.uuid4())
        
        try:
            self.table.put_item(
                Item={
                    "PK": f"USER#{user_id}",
                    "SK": "PROFILE",
                    "username": username,
                    "password_hash": password_hash,
                    "created": datetime.utcnow().isoformat(),
                    "ratings_count": 0,
                },
                ConditionExpression="attribute_not_exists(PK)"
            )
            return user_id
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ValueError("User already exists")
            raise
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username using GSI."""
        try:
            response = self.table.query(
                IndexName="username-index",
                KeyConditionExpression=Key("username").eq(username)
            )
            items = response.get("Items", [])
            return items[0] if items else None
        except ClientError:
            return None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        try:
            response = self.table.get_item(
                Key={
                    "PK": f"USER#{user_id}",
                    "SK": "PROFILE"
                }
            )
            return response.get("Item")
        except ClientError:
            return None
    
    def username_exists(self, username: str) -> bool:
        """Check if username already exists."""
        return self.get_user_by_username(username) is not None
    
    def create_friend(self, name: str, city: str, photo_key: str, uploaded_by: str) -> str:
        """Create a new friend record."""
        friend_id = str(uuid.uuid4())
        
        with self.table.batch_writer() as batch:
            # Friend metadata
            batch.put_item(
                Item={
                    "PK": f"FRIEND#{friend_id}",
                    "SK": "METADATA",
                    "name": name,
                    "city": city,
                    "avg_rating": Decimal("0"),
                    "num_ratings": 0,
                    "created": datetime.utcnow().isoformat(),
                    "name_city": f"{name}#{city}",  # For GSI
                }
            )
            
            # Friend photo
            batch.put_item(
                Item={
                    "PK": f"FRIEND#{friend_id}",
                    "SK": f"PHOTO#{photo_key}",
                    "s3_key": photo_key,
                    "uploaded_by": uploaded_by,
                    "created": datetime.utcnow().isoformat(),
                }
            )
        
        return friend_id
    
    def get_friend(self, friend_id: str) -> Optional[Dict[str, Any]]:
        """Get friend metadata."""
        try:
            response = self.table.get_item(
                Key={
                    "PK": f"FRIEND#{friend_id}",
                    "SK": "METADATA"
                }
            )
            return response.get("Item")
        except ClientError:
            return None
    
    def add_friend_photo(self, friend_id: str, photo_key: str, uploaded_by: str) -> None:
        """Add a photo to existing friend."""
        self.table.put_item(
            Item={
                "PK": f"FRIEND#{friend_id}",
                "SK": f"PHOTO#{photo_key}",
                "s3_key": photo_key,
                "uploaded_by": uploaded_by,
                "created": datetime.utcnow().isoformat(),
            }
        )
    
    def create_rating(self, friend_id: str, user_id: str, score: int, comment: str) -> str:
        """Create a rating for a friend."""
        rating_id = str(uuid.uuid4())
        
        # Create rating record
        self.table.put_item(
            Item={
                "PK": f"FRIEND#{friend_id}",
                "SK": f"RATING#{user_id}#{rating_id}",
                "rating_id": rating_id,
                "user_id": user_id,
                "score": score,
                "comment": comment,
                "created": datetime.utcnow().isoformat(),
            }
        )
        
        return rating_id
    
    def update_friend_rating(self, friend_id: str, new_avg: float, new_count: int) -> None:
        """Update friend's aggregate rating."""
        self.table.update_item(
            Key={
                "PK": f"FRIEND#{friend_id}",
                "SK": "METADATA"
            },
            UpdateExpression="SET avg_rating = :avg, num_ratings = :count",
            ExpressionAttributeValues={
                ":avg": Decimal(str(new_avg)),
                ":count": new_count
            }
        )
    
    def get_friend_ratings(self, friend_id: str) -> List[Dict[str, Any]]:
        """Get all ratings for a friend."""
        try:
            response = self.table.query(
                KeyConditionExpression=Key("PK").eq(f"FRIEND#{friend_id}") & 
                                     Key("SK").begins_with("RATING#"),
                ScanIndexForward=False  # Latest first
            )
            return response.get("Items", [])
        except ClientError:
            return []
    
    def get_friend_photos(self, friend_id: str, cursor: Optional[str] = None, limit: int = 20) -> Tuple[List[str], Optional[str]]:
        """Get friend photos with pagination."""
        try:
            query_kwargs = {
                "KeyConditionExpression": Key("PK").eq(f"FRIEND#{friend_id}") & 
                                        Key("SK").begins_with("PHOTO#"),
                "Limit": limit,
                "ScanIndexForward": False
            }
            
            if cursor:
                query_kwargs["ExclusiveStartKey"] = self._decode_cursor(cursor)
            
            response = self.table.query(**query_kwargs)
            
            photos = [item["s3_key"] for item in response.get("Items", [])]
            next_cursor = None
            
            if "LastEvaluatedKey" in response:
                next_cursor = self._encode_cursor(response["LastEvaluatedKey"])
            
            return photos, next_cursor
        except ClientError:
            return [], None
    
    def search_friends(
        self, 
        name_prefix: Optional[str] = None, 
        city_prefix: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 20
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Search friends by name and city prefixes."""
        try:
            if name_prefix and city_prefix:
                # Search using name_city GSI
                query_kwargs = {
                    "IndexName": "name_city-index",
                    "KeyConditionExpression": Key("name_city").begins_with(f"{name_prefix}#{city_prefix}"),
                    "Limit": limit
                }
            elif name_prefix:
                # Filter by name prefix
                query_kwargs = {
                    "FilterExpression": Attr("name").begins_with(name_prefix),
                    "Limit": limit
                }
            elif city_prefix:
                # Filter by city prefix  
                query_kwargs = {
                    "FilterExpression": Attr("city").begins_with(city_prefix),
                    "Limit": limit
                }
            else:
                # Get all friends
                query_kwargs = {"Limit": limit}
            
            if cursor:
                query_kwargs["ExclusiveStartKey"] = self._decode_cursor(cursor)
            
            if "IndexName" in query_kwargs:
                response = self.table.query(**query_kwargs)
            else:
                response = self.table.scan(**query_kwargs)
            
            friends = []
            for item in response.get("Items", []):
                if item.get("SK") == "METADATA":
                    friends.append(item)
            
            next_cursor = None
            if "LastEvaluatedKey" in response:
                next_cursor = self._encode_cursor(response["LastEvaluatedKey"])
            
            return friends, next_cursor
        except ClientError:
            return [], None
    
    def increment_user_ratings_count(self, user_id: str) -> None:
        """Increment user's ratings count."""
        self.table.update_item(
            Key={
                "PK": f"USER#{user_id}",
                "SK": "PROFILE"
            },
            UpdateExpression="ADD ratings_count :inc",
            ExpressionAttributeValues={":inc": 1}
        )
    
    def _encode_cursor(self, last_key: Dict[str, Any]) -> str:
        """Encode DynamoDB LastEvaluatedKey as cursor."""
        import base64
        import json
        
        # Convert Decimal to float for JSON serialization
        serializable_key = {}
        for k, v in last_key.items():
            if isinstance(v, Decimal):
                serializable_key[k] = float(v)
            else:
                serializable_key[k] = v
        
        return base64.b64encode(json.dumps(serializable_key).encode()).decode()
    
    def _decode_cursor(self, cursor: str) -> Dict[str, Any]:
        """Decode cursor back to DynamoDB key."""
        import base64
        import json
        
        try:
            return json.loads(base64.b64decode(cursor.encode()).decode())
        except Exception:
            raise ValueError("Invalid cursor")