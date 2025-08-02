"""Health check blueprint."""

from flask import Blueprint, jsonify

from src.models.common import HealthResponse

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health_check() -> tuple[dict, int]:
    """Health check endpoint."""
    response = HealthResponse()
    return jsonify(response.dict()), 200