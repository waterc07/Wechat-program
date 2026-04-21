from datetime import datetime, timezone

from flask import Blueprint

from ..schemas.response import success_response


health_bp = Blueprint("health", __name__, url_prefix="/api")


@health_bp.record_once
def register_root_route(state):
    app = state.app

    @app.get("/")
    def root():
        return success_response(
            {
                "service": "medical-pre-diagnosis-assistant",
                "status": "running",
                "health_endpoint": "/api/health",
            },
            message="Service is running.",
        )


@health_bp.get("/health")
def health_check():
    return success_response(
        {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
