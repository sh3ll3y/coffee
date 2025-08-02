"""Custom exception classes for the application."""


class CoffeeException(Exception):
    """Base exception class for Coffee application."""
    
    def __init__(self, message: str, error_code: str = "INTERNAL_ERROR", status_code: int = 500):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(CoffeeException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR", 400)


class AuthenticationError(CoffeeException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "BAD_CREDENTIALS", 401)


class AuthorizationError(CoffeeException):
    """Raised when authorization fails."""
    
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, "ACCESS_DENIED", 403)


class NotFoundError(CoffeeException):
    """Raised when a resource is not found."""
    
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, "NOT_FOUND", 404)


class ConflictError(CoffeeException):
    """Raised when a resource conflict occurs."""
    
    def __init__(self, message: str, error_code: str = "CONFLICT"):
        super().__init__(message, error_code, 409)


class InvalidGenderError(CoffeeException):
    """Raised when gender detection fails."""
    
    def __init__(self, message: str = "Selfie not detected as male"):
        super().__init__(message, "INVALID_GENDER", 400)


class FaceVerificationError(CoffeeException):
    """Raised when face verification fails."""
    
    def __init__(self, message: str):
        super().__init__(message, "FACE_VERIFICATION_FAILED", 400)


class TextModerationError(CoffeeException):
    """Raised when text moderation fails."""
    
    def __init__(self, message: str = "Comment contains inappropriate content"):
        super().__init__(message, "INAPPROPRIATE_CONTENT", 400)