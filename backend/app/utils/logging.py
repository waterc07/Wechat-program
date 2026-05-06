import logging
import time

from flask import g, request


def configure_logging(app):
    level_name = app.config.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )
    app.logger.setLevel(level)

    @app.before_request
    def log_request_start():
        g.request_started_at = time.perf_counter()

    @app.after_request
    def log_request_end(response):
        started_at = getattr(g, "request_started_at", None)
        elapsed_ms = (
            round((time.perf_counter() - started_at) * 1000, 2)
            if started_at is not None
            else None
        )
        app.logger.info(
            "request complete method=%s path=%s status=%s elapsed_ms=%s",
            request.method,
            request.full_path.rstrip("?"),
            response.status_code,
            elapsed_ms,
        )
        return response


def get_logger(name):
    return logging.getLogger(name)
