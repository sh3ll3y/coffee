"""Main Flask application factory and Lambda handler."""

from typing import Any, Dict

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.middleware import lambda_handler_decorator
from flask import Flask, jsonify
from pydantic import ValidationError

from src.blueprints.auth import auth_bp
from src.blueprints.friends import friends_bp
from src.blueprints.health import health_bp
from src.blueprints.uploads import uploads_bp
from src.blueprints.user import user_bp
from src.config import settings
from src.models.common import ErrorResponse
from src.utils.errors import CoffeeException

# Initialize AWS Powertools
logger = Logger()
tracer = Tracer()


def create_app() -> Flask:
    """Create and configure Flask application."""
    app = Flask(__name__)
    
    # Configure Flask
    app.config["DEBUG"] = settings.flask_debug
    app.config["SECRET_KEY"] = settings.jwt_secret_key
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(uploads_bp, url_prefix="/uploads")
    app.register_blueprint(friends_bp, url_prefix="/friends")
    app.register_blueprint(user_bp)
    app.register_blueprint(health_bp)
    
    # Register error handlers
    register_error_handlers(app)
    
    return app


def register_error_handlers(app: Flask) -> None:
    """Register global error handlers."""
    
    @app.errorhandler(CoffeeException)
    def handle_coffee_exception(error: CoffeeException) -> tuple[Any, int]:
        """Handle custom application exceptions."""
        logger.error(f"CoffeeException: {error.message}", extra={"error_code": error.error_code})
        response = ErrorResponse(
            error=error.error_code,
            message=error.message
        )
        return jsonify(response.dict()), error.status_code
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError) -> tuple[Any, int]:
        """Handle Pydantic validation errors."""
        logger.error(f"ValidationError: {error}")
        response = ErrorResponse(
            error="VALIDATION_ERROR",
            message="Invalid input data",
            details={"errors": error.errors()}
        )
        return jsonify(response.dict()), 400
    
    @app.errorhandler(404)
    def handle_not_found(error: Any) -> tuple[Any, int]:
        """Handle 404 errors."""
        response = ErrorResponse(
            error="NOT_FOUND",
            message="Endpoint not found"
        )
        return jsonify(response.dict()), 404
    
    @app.errorhandler(405)
    def handle_method_not_allowed(error: Any) -> tuple[Any, int]:
        """Handle 405 errors."""
        response = ErrorResponse(
            error="METHOD_NOT_ALLOWED",
            message="Method not allowed"
        )
        return jsonify(response.dict()), 405
    
    @app.errorhandler(500)
    def handle_internal_error(error: Any) -> tuple[Any, int]:
        """Handle internal server errors."""
        logger.error(f"Internal server error: {error}")
        response = ErrorResponse(
            error="INTERNAL_ERROR",
            message="An internal error occurred"
        )
        return jsonify(response.dict()), 500


# Create Flask app instance
app = create_app()


@lambda_handler_decorator
@tracer.capture_lambda_handler
@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda handler for API Gateway integration."""
    from werkzeug.serving import WSGIRequestHandler
    from werkzeug.wrappers import Response
    
    # Use awsgi to handle API Gateway event
    try:
        import awsgi
        return awsgi.response(app, event, context)
    except ImportError:
        # Fallback for local testing
        logger.warning("awsgi not available, using local handler")
        return {
            "statusCode": 500,
            "body": '{"error": "CONFIGURATION_ERROR", "message": "Lambda handler not properly configured"}'
        }


if __name__ == "__main__":
    # For local development
    app.run(debug=settings.flask_debug, port=5000)