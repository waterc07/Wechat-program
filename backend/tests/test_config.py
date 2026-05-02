from app import create_app
from app.config import validate_runtime_config


def test_database_engine_options_are_enabled():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    assert app.config["SQLALCHEMY_ENGINE_OPTIONS"]["pool_pre_ping"] is True
    assert app.config["SQLALCHEMY_ENGINE_OPTIONS"]["pool_recycle"] == 1800


def test_production_rejects_mock_llm_provider(app):
    app.config.update(
        {
            "FLASK_ENV": "production",
            "TESTING": False,
            "SECRET_KEY": "production-secret",
            "SQLALCHEMY_DATABASE_URI": "mysql+pymysql://user:pass@db:3306/app",
            "LLM_PROVIDER": "mock",
        }
    )

    try:
        validate_runtime_config(app)
    except RuntimeError as error:
        assert "LLM_PROVIDER must not be mock" in str(error)
    else:
        raise AssertionError("Expected production mock LLM provider to be rejected.")


def test_production_requires_qwen_api_key(app):
    app.config.update(
        {
            "FLASK_ENV": "production",
            "TESTING": False,
            "SECRET_KEY": "production-secret",
            "SQLALCHEMY_DATABASE_URI": "mysql+pymysql://user:pass@db:3306/app",
            "LLM_PROVIDER": "qwen",
            "LLM_API_KEY": "",
        }
    )

    try:
        validate_runtime_config(app)
    except RuntimeError as error:
        assert "LLM_API_KEY is required" in str(error)
    else:
        raise AssertionError("Expected production qwen LLM without API key to be rejected.")
