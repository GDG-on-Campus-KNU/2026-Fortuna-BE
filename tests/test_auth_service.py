import asyncio

import pytest
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.schemas.user import UserCreate
from app.services.auth_service import AuthService


class DuplicateRaceRepository:
    async def get_by_email(self, email: str) -> None:
        return None

    async def create(self, email: str, hashed_password: str) -> None:
        raise IntegrityError(
            statement="INSERT INTO users",
            params={"email": email},
            orig=Exception("duplicate key value violates unique constraint"),
        )


def test_register_user_maps_unique_race_to_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.auth_service.security.hash_password",
        lambda _: "hashed-password",
    )
    service = AuthService.__new__(AuthService)
    service.repository = DuplicateRaceRepository()
    user_in = UserCreate(email="user@example.com", password="password123")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.register_user(user_in))

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    assert exc_info.value.detail == "Email already registered"
