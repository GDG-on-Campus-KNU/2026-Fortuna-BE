from typing import Any

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Index,
    MetaData,
    String,
    Table,
    create_engine,
    delete,
    func,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import insert as postgresql_insert

from app.core.config import Settings
from app.core.errors import AppError


metadata = MetaData()

files = Table(
    "metadata_files",
    metadata,
    Column("file_id", String(128), primary_key=True),
    Column("user_id", String(128), nullable=False),
    Column("record", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column(
        "updated_at",
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    ),
    Index("ix_metadata_files_user_id", "user_id"),
)
scripts = Table(
    "metadata_scripts",
    metadata,
    Column("script_id", String(128), primary_key=True),
    Column("user_id", String(128), nullable=False),
    Column("record", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column(
        "updated_at",
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    ),
    Index("ix_metadata_scripts_user_id", "user_id"),
)
audio = Table(
    "metadata_audio",
    metadata,
    Column("audio_id", String(128), primary_key=True),
    Column("user_id", String(128), nullable=False),
    Column("record", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column(
        "updated_at",
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    ),
    Index("ix_metadata_audio_user_id", "user_id"),
)
jobs = Table(
    "metadata_jobs",
    metadata,
    Column("job_id", String(128), primary_key=True),
    Column("user_id", String(128), nullable=False),
    Column("record", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column(
        "updated_at",
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    ),
    Index("ix_metadata_jobs_user_id", "user_id"),
)


notebooks = Table(
    "metadata_notebooks",
    metadata,
    Column("notebook_id", String(128), primary_key=True),
    Column("user_id", String(128), nullable=False),
    Column("record", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column(
        "updated_at",
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    ),
    Index("ix_metadata_notebooks_user_id", "user_id"),
)


TABLES: dict[str, tuple[Table, str]] = {
    "files": (files, "file_id"),
    "scripts": (scripts, "script_id"),
    "audio": (audio, "audio_id"),
    "jobs": (jobs, "job_id"),
    "notebooks": (notebooks, "notebook_id"),
}


class PostgresMetadataRepository:
    def __init__(self, settings: Settings, engine: Engine | None = None) -> None:
        self.settings = settings
        self.engine = engine or create_engine(
            self._sync_database_url(settings.DATABASE_URL),
            pool_pre_ping=True,
            future=True,
        )
        try:
            metadata.create_all(self.engine)
        except SQLAlchemyError as exc:
            raise AppError(
                "METADATA_INITIALIZATION_FAILED",
                "Failed to initialize PostgreSQL metadata tables.",
                status_code=500,
                detail={"reason": exc.__class__.__name__},
            ) from exc

    def save_file(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._upsert("files", record)

    def get_file(self, file_id: str, user_id: str | None = None) -> dict | None:
        return self._get_scoped("files", file_id, user_id)

    def list_files(self, user_id: str) -> list[dict]:
        return self._list("files", user_id)

    def save_script(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._upsert("scripts", record)

    def get_script(self, script_id: str, user_id: str | None = None) -> dict | None:
        return self._get_scoped("scripts", script_id, user_id)

    def list_scripts(self, user_id: str) -> list[dict]:
        return self._list("scripts", user_id)

    def save_audio(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._upsert("audio", record)

    def get_audio(self, audio_id: str, user_id: str | None = None) -> dict | None:
        return self._get_scoped("audio", audio_id, user_id)

    def list_audio(self, user_id: str) -> list[dict]:
        return self._list("audio", user_id)

    def save_job(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._upsert("jobs", record)

    def update_job(
        self, job_id: str, user_id: str | None, changes: dict[str, Any]
    ) -> dict | None:
        table, key = TABLES["jobs"]
        try:
            with self.engine.begin() as conn:
                row = conn.execute(
                    select(table.c.record).where(table.c[key] == job_id)
                ).first()
                if row is None:
                    return None
                record = dict(row._mapping["record"])
                if user_id is not None and record.get("user_id") != user_id:
                    return None
                record = {**record, **changes}
                conn.execute(
                    update(table)
                    .where(table.c[key] == job_id)
                    .values(user_id=record["user_id"], record=record)
                )
                return record
        except SQLAlchemyError as exc:
            raise self._metadata_error("jobs", exc) from exc

    def get_job(self, job_id: str, user_id: str | None = None) -> dict | None:
        return self._get_scoped("jobs", job_id, user_id)

    def list_jobs(self, user_id: str) -> list[dict]:
        return self._list("jobs", user_id)

    def save_notebook(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._upsert("notebooks", record)

    def get_notebook(self, notebook_id: str, user_id: str | None = None) -> dict | None:
        return self._get_scoped("notebooks", notebook_id, user_id)

    def list_notebooks(self, user_id: str) -> list[dict]:
        return self._list("notebooks", user_id)

    def delete_notebook(self, notebook_id: str, user_id: str) -> None:
        self._delete("notebooks", notebook_id, user_id)

    def delete_audio(self, audio_id: str, user_id: str) -> None:
        self._delete("audio", audio_id, user_id)

    def delete_file(self, file_id: str, user_id: str) -> None:
        self._delete("files", file_id, user_id)

    def _delete(self, collection: str, key_value: str, user_id: str) -> None:
        table, key = TABLES[collection]
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    delete(table).where(
                        (table.c[key] == key_value) & (table.c.user_id == user_id)
                    )
                )
        except SQLAlchemyError as exc:
            raise AppError(
                "METADATA_DELETE_FAILED",
                "Failed to delete metadata.",
                status_code=500,
                detail={"collection": collection, "reason": exc.__class__.__name__},
            ) from exc

    def _upsert(self, collection: str, record: dict[str, Any]) -> dict[str, Any]:
        table, key = TABLES[collection]
        key_value = record[key]
        values = {
            key: key_value,
            "user_id": record["user_id"],
            "record": dict(record),
        }
        try:
            with self.engine.begin() as conn:
                if self.engine.dialect.name == "postgresql":
                    statement = postgresql_insert(table).values(**values)
                    conn.execute(
                        statement.on_conflict_do_update(
                            index_elements=[table.c[key]],
                            set_={
                                "user_id": statement.excluded.user_id,
                                "record": statement.excluded.record,
                                "updated_at": func.now(),
                            },
                        )
                    )
                    return record

                exists = conn.execute(
                    select(table.c[key]).where(table.c[key] == key_value)
                ).first()
                if exists is None:
                    conn.execute(insert(table).values(**values))
                    return record
                conn.execute(
                    update(table).where(table.c[key] == key_value).values(**values)
                )
                return record
        except SQLAlchemyError as exc:
            raise self._metadata_error(collection, exc) from exc

    def _get_scoped(
        self, collection: str, key_value: str, user_id: str | None
    ) -> dict | None:
        table, key = TABLES[collection]
        try:
            with self.engine.connect() as conn:
                row = conn.execute(
                    select(table.c.record).where(table.c[key] == key_value)
                ).first()
                if row is None:
                    return None
                record = row._mapping["record"]
                if user_id is not None and record.get("user_id") != user_id:
                    return None
                return record
        except SQLAlchemyError as exc:
            raise self._metadata_error(collection, exc) from exc

    def _list(self, collection: str, user_id: str) -> list[dict]:
        table, key = TABLES[collection]
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(
                    select(table.c.record)
                    .where(table.c.user_id == user_id)
                    .order_by(table.c.created_at, table.c[key])
                ).all()
                return [row._mapping["record"] for row in rows]
        except SQLAlchemyError as exc:
            raise self._metadata_error(collection, exc) from exc

    def _metadata_error(self, collection: str, exc: SQLAlchemyError) -> AppError:
        return AppError(
            "METADATA_SAVE_FAILED",
            "Failed to save metadata.",
            status_code=500,
            detail={"collection": collection, "reason": exc.__class__.__name__},
        )

    def _sync_database_url(self, url: str) -> str:
        if url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url
