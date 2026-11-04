from flask import jsonify


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}

    def to_dict(self):
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details
            }
        }

class ValidationError(AppError):
    def __init__(self, message: str = "Invalid input data", details: dict | None = None):
        super().__init__("VALIDATION_ERROR", message, 400, details)

class AuthRequiredError(AppError):
    def __init__(self, message: str = "Authentication token is required"):
        super().__init__("AUTH_REQUIRED", message, 401)

class InvalidCredentialsError(AppError):
    def __init__(self, message: str = "Invalid PRN/username or password"):
        super().__init__("INVALID_CREDENTIALS", message, 401)

class PasswordChangeRequiredError(AppError):
    def __init__(self, message: str = "Password change required before accessing other resources"):
        super().__init__("PASSWORD_CHANGE_REQUIRED", message, 403)

class ForbiddenError(AppError):
    def __init__(self, message: str = "Access forbidden"):
        super().__init__("FORBIDDEN", message, 403)

class WrongCampusError(AppError):
    def __init__(self, message: str = "Action not permitted for this campus"):
        super().__init__("WRONG_CAMPUS", message, 403)

class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__("NOT_FOUND", message, 404)

class ConflictError(AppError):
    def __init__(self, message: str = "Operation conflict with existing record", details: dict | None = None):
        super().__init__("CONFLICT", message, 409, details)

class PayloadTooLargeError(AppError):
    def __init__(self, message: str = "Uploaded file exceeds size limit (3 MB)"):
        super().__init__("PAYLOAD_TOO_LARGE", message, 413)

class UnsupportedMediaError(AppError):
    def __init__(self, message: str = "Unsupported media type. Allowed: JPEG, PNG, WebP"):
        super().__init__("UNSUPPORTED_MEDIA", message, 415)

class AccountLockedError(AppError):
    def __init__(self, message: str = "Account locked due to multiple failed login attempts", details: dict | None = None):
        super().__init__("ACCOUNT_LOCKED", message, 423, details)

class RateLimitedError(AppError):
    def __init__(self, message: str = "Rate limit exceeded. Please try again later."):
        super().__init__("RATE_LIMITED", message, 429)

class InternalError(AppError):
    def __init__(self, message: str = "An internal server error occurred"):
        super().__init__("INTERNAL", message, 500)

def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        return jsonify(err.to_dict()), err.status_code

    @app.errorhandler(404)
    def handle_404(err):
        return jsonify({
            "error": {
                "code": "NOT_FOUND",
                "message": "The requested endpoint does not exist",
                "details": {}
            }
        }), 404

    @app.errorhandler(405)
    def handle_405(err):
        return jsonify({
            "error": {
                "code": "METHOD_NOT_ALLOWED",
                "message": "HTTP method not allowed for this route",
                "details": {}
            }
        }), 405

    @app.errorhandler(Exception)
    def handle_unexpected_error(err):
        # Log error in production
        return jsonify({
            "error": {
                "code": "INTERNAL",
                "message": "Internal server error occurred",
                "details": str(err) if app.debug else {}
            }
        }), 500

