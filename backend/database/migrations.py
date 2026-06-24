from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


SQLITE_COLUMNS: dict[str, dict[str, str]] = {
    "students": {
        "user_id": "INTEGER",
        "email": "VARCHAR",
        "password": "VARCHAR",
        "name": "VARCHAR",
        "created_at": "DATETIME",
        "topic": "VARCHAR",
        "level": "VARCHAR",
        "accuracy": "FLOAT DEFAULT 0",
        "total_quizzes": "INTEGER DEFAULT 0",
        "correct_answers": "INTEGER DEFAULT 0",
        "notes_generated": "INTEGER DEFAULT 0",
        "quizzes_generated": "INTEGER DEFAULT 0",
        "last_updated": "DATETIME",
    },
    "quiz_results": {
        "student_id": "INTEGER",
        "topic": "VARCHAR",
        "score": "INTEGER",
        "total_questions": "INTEGER",
        "accuracy": "FLOAT",
        "details_json": "TEXT",
        "created_at": "DATETIME",
    },
    "notes": {
        "student_id": "INTEGER",
        "subject": "VARCHAR",
        "topic": "VARCHAR",
        "level": "VARCHAR",
        "created_at": "DATETIME",
    },
    "documents": {
        "student_id": "INTEGER",
        "conversation_id": "INTEGER",
        "title": "VARCHAR",
        "source": "VARCHAR",
        "file_type": "VARCHAR DEFAULT 'pdf'",
        "file_path": "VARCHAR",
        "uploaded_at": "DATETIME",
    },
    "document_chunks": {
        "document_id": "INTEGER",
        "chunk_index": "INTEGER DEFAULT 0",
        "text": "TEXT",
        "embedding_id": "INTEGER",
        "created_at": "DATETIME",
    },
}


def ensure_sqlite_schema(engine: Engine) -> None:
    """
    create_all creates missing tables, but it will not add columns to older
    recovered SQLite tables. This small repair path keeps existing local data
    and adds only missing nullable/defaulted columns.
    """
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table_name, columns in SQLITE_COLUMNS.items():
            if table_name not in existing_tables:
                continue

            existing_columns = {
                column["name"] for column in inspector.get_columns(table_name)
            }
            for column_name, ddl in columns.items():
                if column_name in existing_columns:
                    continue
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}"))

        if "document_chunks" in existing_tables:
            refreshed_columns = {
                column["name"] for column in inspect(engine).get_columns("document_chunks")
            }
            if "chunk_text" in refreshed_columns and "text" in refreshed_columns:
                conn.execute(
                    text(
                        "UPDATE document_chunks "
                        "SET text = chunk_text "
                        "WHERE text IS NULL AND chunk_text IS NOT NULL"
                    )
                )
