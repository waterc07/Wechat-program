from app import create_app


def test_database_engine_options_are_enabled():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    assert app.config["SQLALCHEMY_ENGINE_OPTIONS"]["pool_pre_ping"] is True
    assert app.config["SQLALCHEMY_ENGINE_OPTIONS"]["pool_recycle"] == 1800
