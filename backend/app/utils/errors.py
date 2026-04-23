from sqlalchemy.exc import OperationalError
from werkzeug.exceptions import HTTPException

from .logging import get_logger


logger = get_logger(__name__)


class AppError(Exception):
    status_code = 400
    error_code = "APP_ERROR"

    def __init__(self, message, *, status_code=None, error_code=None, data=None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if error_code is not None:
            self.error_code = error_code
        self.data = data or {}


class ValidationError(AppError):
    status_code = 400
    error_code = "VALIDATION_ERROR"


class NotFoundError(AppError):
    status_code = 404
    error_code = "NOT_FOUND"


class ServiceError(AppError):
    status_code = 502
    error_code = "SERVICE_ERROR"


def register_error_handlers(app):
    from ..schemas.response import error_response
    from ..extensions import db

    @app.errorhandler(AppError)
    def handle_app_error(error):
        return error_response(
            error.message,
            code=error.error_code,
            status=error.status_code,
            data=error.data,
        )

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return error_response(
            error.description,
            code=error.name.upper().replace(" ", "_"),
            status=error.code or 500,
        )

    @app.errorhandler(OperationalError)
    def handle_operational_error(error):
        logger.exception("Database operational error: %s", error)
        try:
            db.session.remove()
            db.engine.dispose()
        except Exception:  # noqa: BLE001
            logger.exception("Failed to reset database engine after operational error.")
        return error_response(
            "Database connection is temporarily unavailable.",
            code="DATABASE_UNAVAILABLE",
            status=503,
        )

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        logger.exception("Unhandled exception: %s", error)
        return error_response(
            "Internal server error.",
            code="INTERNAL_SERVER_ERROR",
            status=500,
        )
