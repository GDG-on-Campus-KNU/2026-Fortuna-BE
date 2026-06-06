import asyncio
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.core.database import Base
from app.infra.repositories.postgres import PostgresMetadataRepository
from app.models.user import User


def _sync_database_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def _async_database_url(url: str) -> str:
    if url.startswith("postgresql+psycopg://"):
        return url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


async def _create_auth_state(database_url: str, schema: str) -> None:
    engine = create_async_engine(
        database_url,
        connect_args={"server_settings": {"search_path": schema}},
        future=True,
    )
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            session.add(
                User(
                    email=f"{schema}@example.com",
                    hashed_password="hashed-password",
                )
            )
            await session.commit()
    finally:
        await engine.dispose()


def test_postgres_auth_and_metadata_share_fresh_database_path() -> None:
    database_url = os.getenv("POSTGRES_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("POSTGRES_TEST_DATABASE_URL is not configured.")
    if not database_url.startswith("postgresql"):
        pytest.skip("POSTGRES_TEST_DATABASE_URL must be a PostgreSQL URL.")

    sync_url = _sync_database_url(database_url)
    async_url = _async_database_url(database_url)
    schema = f"fortuna_test_{uuid4().hex}"
    setup_engine = create_engine(sync_url, future=True)
    metadata_engine = None

    with setup_engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))

    try:
        asyncio.run(_create_auth_state(async_url, schema))

        metadata_engine = create_engine(
            sync_url,
            connect_args={"options": f"-csearch_path={schema}"},
            future=True,
        )
        repository = PostgresMetadataRepository(
            Settings(DATABASE_URL=database_url, _env_file=None),
            engine=metadata_engine,
        )
        assert repository.engine.dialect.name == "postgresql"

        file_record = {
            "file_id": "file_pg_upsert",
            "user_id": "user_pg",
            "filename": "original.txt",
            "content_type": "text/plain",
            "size": 1,
            "storage_uri": "gs://bucket/uploads/user_pg/file_pg_upsert/original.txt",
            "extracted_text_uri": (
                "gs://bucket/uploads/user_pg/file_pg_upsert/extracted.txt"
            ),
            "extracted_text_chars": 1,
            "created_at": "2026-05-27T00:00:00+00:00",
        }
        updated_file_record = {
            **file_record,
            "filename": "updated.txt",
            "size": 2,
        }

        assert repository.save_file(file_record) == file_record
        assert repository.save_file(updated_file_record) == updated_file_record
        assert (
            repository.get_file("file_pg_upsert", "user_pg")["filename"]
            == "updated.txt"
        )

        tables = set(inspect(metadata_engine).get_table_names(schema=schema))
        assert {
            "users",
            "metadata_files",
            "metadata_scripts",
            "metadata_audio",
            "metadata_jobs",
            "metadata_notebooks",
        }.issubset(tables)
    finally:
        if metadata_engine is not None:
            metadata_engine.dispose()
        with setup_engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        setup_engine.dispose()
