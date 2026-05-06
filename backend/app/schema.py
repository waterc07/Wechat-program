from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError, ProgrammingError

from .extensions import db


MESSAGES_TABLE = "messages"
CLIENT_REQUEST_ID_COLUMN = "client_request_id"
CLIENT_REQUEST_ID_INDEX = "ix_messages_client_request_id"


def ensure_runtime_schema():
    """Apply small additive schema fixes that db.create_all() cannot perform."""
    if not _table_exists(MESSAGES_TABLE):
        return

    if not _column_exists(MESSAGES_TABLE, CLIENT_REQUEST_ID_COLUMN):
        _execute_schema_ddl(
            f"ALTER TABLE {MESSAGES_TABLE} "
            f"ADD COLUMN {CLIENT_REQUEST_ID_COLUMN} VARCHAR(128) NULL"
        )

    if not _index_exists(MESSAGES_TABLE, CLIENT_REQUEST_ID_INDEX):
        _execute_schema_ddl(
            f"CREATE INDEX {CLIENT_REQUEST_ID_INDEX} "
            f"ON {MESSAGES_TABLE} ({CLIENT_REQUEST_ID_COLUMN})"
        )


def _table_exists(table_name):
    return table_name in inspect(db.engine).get_table_names()


def _column_exists(table_name, column_name):
    return column_name in {
        column["name"] for column in inspect(db.engine).get_columns(table_name)
    }


def _index_exists(table_name, index_name):
    return index_name in {
        index["name"] for index in inspect(db.engine).get_indexes(table_name)
    }


def _execute_schema_ddl(statement):
    try:
        with db.engine.begin() as connection:
            connection.execute(text(statement))
    except (OperationalError, ProgrammingError) as error:
        if _is_duplicate_schema_error(error):
            return
        raise


def _is_duplicate_schema_error(error):
    original = getattr(error, "orig", error)
    code = None
    if getattr(original, "args", None):
        code = original.args[0]
    message = str(original).lower()

    return (
        code in {1060, 1061}
        or "duplicate column" in message
        or "duplicate key name" in message
        or "already exists" in message
    )
