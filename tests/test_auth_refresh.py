import pytest
from unittest.mock import Mock, AsyncMock
from fastapi import HTTPException, status

from app.core import security
from app.services.auth_service import AuthService
from app.models.user import User
from app.schemas.user import Token


def test_refresh_token_creation_and_decoding():
    payload = {"sub": "user@example.com"}
    token = security.create_refresh_token(payload)
    
    decoded = security.decode_refresh_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user@example.com"
    assert decoded["type"] == "refresh"
    
    # Access token decode should fail on refresh token
    assert security.decode_access_token(token) is None


def test_access_token_creation_and_decoding():
    payload = {"sub": "user@example.com"}
    token = security.create_access_token(payload)
    
    decoded = security.decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user@example.com"
    assert decoded["type"] == "access"
    
    # Refresh token decode should fail on access token
    assert security.decode_refresh_token(token) is None


@pytest.mark.anyio
async def test_auth_service_refresh_token_valid():
    # Mock user repository
    user = User(
        email="user@example.com",
        hashed_password="hashed_password",
        is_active=True,
    )
    mock_repository = Mock()
    mock_repository.get_by_email = AsyncMock(return_value=user)
    
    service = AuthService.__new__(AuthService)
    service.repository = mock_repository
    
    # Create valid refresh token
    refresh_token = security.create_refresh_token({"sub": "user@example.com"})
    
    # Refresh access token
    new_token = await service.refresh_access_token(refresh_token)
    
    assert isinstance(new_token, Token)
    assert new_token.access_token is not None
    assert new_token.refresh_token is not None
    assert new_token.token_type == "bearer"
    
    # Validate new tokens
    assert security.decode_access_token(new_token.access_token)["sub"] == "user@example.com"
    assert security.decode_refresh_token(new_token.refresh_token)["sub"] == "user@example.com"


@pytest.mark.anyio
async def test_auth_service_refresh_token_invalid():
    mock_repository = Mock()
    service = AuthService.__new__(AuthService)
    service.repository = mock_repository
    
    # Invalid token string
    with pytest.raises(HTTPException) as exc:
        await service.refresh_access_token("invalid_token")
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid or expired" in exc.value.detail

    # Access token passed instead of refresh token
    access_token = security.create_access_token({"sub": "user@example.com"})
    with pytest.raises(HTTPException) as exc:
        await service.refresh_access_token(access_token)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid or expired" in exc.value.detail
