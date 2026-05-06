from sqlalchemy import inspect, text

from app.extensions import db
from app.schema import ensure_runtime_schema


def test_runtime_schema_adds_client_request_id_to_existing_messages_table(app):
    with app.app_context():
        db.drop_all()
        with db.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE messages (
                        id INTEGER PRIMARY KEY,
                        consultation_id INTEGER NOT NULL,
                        role VARCHAR(32) NOT NULL,
                        content TEXT NOT NULL,
                        risk_level VARCHAR(32) NOT NULL,
                        created_at DATETIME NOT NULL
                    )
                    """
                )
            )

        ensure_runtime_schema()

        inspector = inspect(db.engine)
        columns = {column["name"] for column in inspector.get_columns("messages")}
        indexes = {index["name"] for index in inspector.get_indexes("messages")}

        assert "client_request_id" in columns
        assert "ix_messages_client_request_id" in indexes
