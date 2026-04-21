import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "replace-me")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{(BASE_DIR / 'pre_diagnosis.db').as_posix()}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
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


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


def get_config():
    if os.getenv("FLASK_ENV") == "testing":
        return TestingConfig
    return Config
