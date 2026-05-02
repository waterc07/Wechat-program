import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")


class Config:
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.getenv("SECRET_KEY", "replace-me")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{(BASE_DIR / 'pre_diagnosis.db').as_posix()}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": os.getenv("DB_POOL_PRE_PING", "true").lower() == "true",
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE_SECONDS", "1800")),
    }
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock")
    LLM_BASE_URL = os.getenv(
        "LLM_BASE_URL",
        os.getenv("LLM_API_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    )
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "qwen3.6-plus")
    LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
    WECHAT_APPID = os.getenv("WECHAT_APPID", "")
    WECHAT_APPSECRET = os.getenv("WECHAT_APPSECRET", "")
    WECHAT_USE_REAL_AUTH = os.getenv("WECHAT_USE_REAL_AUTH", "false").lower() == "true"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    FLASK_ENV = "production"
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    FLASK_ENV = "testing"
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


def get_config():
    if os.getenv("FLASK_ENV") == "testing":
        return TestingConfig
    if os.getenv("FLASK_ENV") == "production":
        return ProductionConfig
    return Config


def validate_runtime_config(app):
    if app.config.get("TESTING"):
        return

    environment = app.config.get("FLASK_ENV", "development")
    secret_key = app.config.get("SECRET_KEY", "")
    database_url = app.config.get("SQLALCHEMY_DATABASE_URI", "")

    if environment == "production":
        if not secret_key or secret_key == "replace-me":
            raise RuntimeError("SECRET_KEY must be set to a non-default value in production.")

        if database_url.startswith("sqlite"):
            raise RuntimeError("SQLite must not be used in production. Set DATABASE_URL to a managed MySQL-compatible database.")

        llm_provider = (app.config.get("LLM_PROVIDER") or "").lower()
        if llm_provider == "mock":
            raise RuntimeError("LLM_PROVIDER must not be mock in production.")

        if llm_provider == "qwen" and not app.config.get("LLM_API_KEY"):
            raise RuntimeError("LLM_API_KEY is required when LLM_PROVIDER=qwen in production.")

        if app.config.get("WECHAT_USE_REAL_AUTH") and (
            not app.config.get("WECHAT_APPID") or not app.config.get("WECHAT_APPSECRET")
        ):
            raise RuntimeError(
                "WECHAT_APPID and WECHAT_APPSECRET are required when WECHAT_USE_REAL_AUTH=true in production."
            )
