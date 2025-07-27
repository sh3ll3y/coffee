"""Uploads blueprint for presigned S3 URLs."""

from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from src.models.uploads import PresignRequest, PresignResponse
from src.services.s3 import S3Service
from src.utils.auth import require_auth

uploads_bp = Blueprint("uploads", __name__)


@uploads_bp.route("/presign", methods=["POST"])
@require_auth
def create_presigned_url() -> tuple[dict, int]:
    """Generate a presigned S3 upload URL."""
    try:
        # Parse request
        data = PresignRequest(**request.get_json())
    except ValidationError as e:
        raise ValidationError(e.errors())
    
    # Initialize S3 service
    s3_service = S3Service()
    
    # Generate presigned URL
    presign_data = s3_service.generate_presigned_upload_url(data.kind.value)
    
    # Return response (simplified for the API spec)
    response = PresignResponse(
        upload_url=presign_data["upload_url"],
        file_key=presign_data["file_key"],
        expires_in=presign_data["expires_in"]
    )
    
    return jsonify(response.dict(by_alias=True)), 200