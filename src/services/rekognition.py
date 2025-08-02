"""Amazon Rekognition service for face detection and verification."""

import boto3
from botocore.exceptions import ClientError
from typing import List, Dict, Any, Optional

from src.config import settings
from src.utils.errors import FaceVerificationError


class RekognitionService:
    """Service for Amazon Rekognition operations."""
    
    def __init__(self) -> None:
        """Initialize Rekognition service."""
        self.client = boto3.client("rekognition", region_name=settings.aws_region)
        self.s3_bucket = settings.s3_bucket_name
        self.collection_id = settings.rekognition_collection_id
    
    def verify_male_gender(self, s3_key: str) -> bool:
        """Verify that the person in the image is male with high confidence."""
        try:
            response = self.client.detect_faces(
                Image={
                    "S3Object": {
                        "Bucket": self.s3_bucket,
                        "Name": s3_key
                    }
                },
                Attributes=["ALL"]
            )
            
            faces = response.get("FaceDetails", [])
            if not faces:
                raise FaceVerificationError("No faces detected in image")
            
            # Check the first (primary) face
            face = faces[0]
            gender = face.get("Gender", {})
            
            return (
                gender.get("Value") == "Male" and
                gender.get("Confidence", 0) >= settings.gender_confidence_threshold
            )
            
        except ClientError as e:
            raise FaceVerificationError(f"Face detection failed: {e}")
    
    def detect_face_liveness(self, s3_key: str) -> bool:
        """Detect if the face in the image is from a live person."""
        try:
            # Use detect_faces with quality attributes as liveness indicator
            response = self.client.detect_faces(
                Image={
                    "S3Object": {
                        "Bucket": self.s3_bucket,
                        "Name": s3_key
                    }
                },
                Attributes=["QUALITY"]
            )
            
            faces = response.get("FaceDetails", [])
            if not faces:
                raise FaceVerificationError("No faces detected for liveness check")
            
            # Check quality attributes as liveness indicators
            face = faces[0]
            quality = face.get("Quality", {})
            
            brightness = quality.get("Brightness", 0)
            sharpness = quality.get("Sharpness", 0)
            
            # Basic liveness check based on quality metrics
            return brightness > 30 and sharpness > 50
            
        except ClientError as e:
            raise FaceVerificationError(f"Liveness detection failed: {e}")
    
    def compare_faces(self, source_s3_key: str, target_s3_key: str) -> float:
        """Compare two faces and return similarity confidence."""
        try:
            response = self.client.compare_faces(
                SourceImage={
                    "S3Object": {
                        "Bucket": self.s3_bucket,
                        "Name": source_s3_key
                    }
                },
                TargetImage={
                    "S3Object": {
                        "Bucket": self.s3_bucket,
                        "Name": target_s3_key
                    }
                },
                SimilarityThreshold=70.0
            )
            
            matches = response.get("FaceMatches", [])
            if not matches:
                return 0.0
            
            # Return highest similarity score
            return max(match["Similarity"] for match in matches)
            
        except ClientError as e:
            raise FaceVerificationError(f"Face comparison failed: {e}")
    
    def search_faces_in_collection(self, s3_key: str) -> Optional[str]:
        """Search for a face in the Rekognition collection."""
        try:
            # First, detect faces in the image
            response = self.client.detect_faces(
                Image={
                    "S3Object": {
                        "Bucket": self.s3_bucket,
                        "Name": s3_key
                    }
                }
            )
            
            faces = response.get("FaceDetails", [])
            if not faces:
                return None
            
            # Index the face temporarily to search
            index_response = self.client.index_faces(
                CollectionId=self.collection_id,
                Image={
                    "S3Object": {
                        "Bucket": self.s3_bucket,
                        "Name": s3_key
                    }
                },
                MaxFaces=1,
                QualityFilter="AUTO"
            )
            
            if not index_response.get("FaceRecords"):
                return None
            
            face_id = index_response["FaceRecords"][0]["Face"]["FaceId"]
            
            # Search for similar faces
            search_response = self.client.search_faces(
                CollectionId=self.collection_id,
                FaceId=face_id,
                MaxFaces=1,
                FaceMatchThreshold=settings.face_match_threshold
            )
            
            # Clean up the temporarily indexed face
            self.client.delete_faces(
                CollectionId=self.collection_id,
                FaceIds=[face_id]
            )
            
            matches = search_response.get("FaceMatches", [])
            if matches and matches[0]["Similarity"] >= settings.face_match_threshold:
                return matches[0]["Face"]["FaceId"]
            
            return None
            
        except ClientError as e:
            if "ResourceNotFoundException" in str(e):
                # Collection doesn't exist, create it
                self._create_collection()
                return None
            raise FaceVerificationError(f"Face search failed: {e}")
    
    def add_face_to_collection(self, s3_key: str, external_image_id: str) -> str:
        """Add a face to the Rekognition collection."""
        try:
            response = self.client.index_faces(
                CollectionId=self.collection_id,
                Image={
                    "S3Object": {
                        "Bucket": self.s3_bucket,
                        "Name": s3_key
                    }
                },
                ExternalImageId=external_image_id,
                MaxFaces=1,
                QualityFilter="AUTO"
            )
            
            face_records = response.get("FaceRecords", [])
            if not face_records:
                raise FaceVerificationError("Could not index face")
            
            return face_records[0]["Face"]["FaceId"]
            
        except ClientError as e:
            if "ResourceNotFoundException" in str(e):
                # Collection doesn't exist, create it
                self._create_collection()
                return self.add_face_to_collection(s3_key, external_image_id)
            raise FaceVerificationError(f"Face indexing failed: {e}")
    
    def _create_collection(self) -> None:
        """Create the Rekognition collection if it doesn't exist."""
        try:
            self.client.create_collection(CollectionId=self.collection_id)
        except ClientError as e:
            if "ResourceAlreadyExistsException" not in str(e):
                raise FaceVerificationError(f"Collection creation failed: {e}")
    
    def get_face_id_hash(self, face_id: str) -> str:
        """Generate a deterministic hash from a Rekognition face ID."""
        import hashlib
        return hashlib.sha256(face_id.encode()).hexdigest()[:16]