from flask import Flask

from .config import get_config
from .extensions import db
from .routes import register_blueprints
from .utils.errors import register_error_handlers
from .utils.logging import configure_logging


def create_app(config_override=None):
    app = Flask(__name__)
    app.config.from_object(get_config())
    if config_override:
        app.config.update(config_override)

    app.json.ensure_ascii = False

    configure_logging(app)
    db.init_app(app)
    register_blueprints(app)
    register_error_handlers(app)

    with app.app_context():
        from . import models  # noqa: F401

        db.create_all()

    return app

