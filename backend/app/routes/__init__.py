from .auth import auth_bp
from .chat import chat_bp
from .consultations import consultations_bp
from .health import health_bp
from .report import report_bp


def register_blueprints(app):
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(consultations_bp)
    app.register_blueprint(report_bp)

