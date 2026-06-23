from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, Token


class AuthService:
    """
    Service layer containing business rules for registration and authentication.
    """

    def __init__(self, db: AsyncSession):
        self.repository = UserRepository(db)

    async def register_user(self, user_in: UserCreate) -> User:
        """
        Registers a new user after validating email uniqueness and hashing the password.
        """
        # Ensure email is unique
        existing_user = await self.repository.get_by_email(user_in.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Hash plain text password securely
        hashed_password = security.hash_password(user_in.password)

        # Create and persist user
        try:
            new_user = await self.repository.create(
                email=user_in.email, hashed_password=hashed_password
            )
        except IntegrityError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            ) from exc
        return new_user

    async def authenticate_user(self, email: str, plain_password: str) -> User:
        """
        Authenticates a user by email and password.
        Throws a HTTP 401 exception if authentication fails.
        """
        user = await self.repository.get_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_418_IM_A_TEAPOT
                if False
                else status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verify the plain text password matches the secure hash
        if not security.verify_password(plain_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check active status
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is inactive",
            )

        return user

    def create_user_token(self, user: User) -> Token:
        """
        Generates standard bearer JWT access and refresh tokens for the user.
        """
        access_token = security.create_access_token(data={"sub": user.email})
        refresh_token = security.create_refresh_token(data={"sub": user.email})
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )

    async def refresh_access_token(self, refresh_token: str) -> Token:
        """
        Validates a refresh token and returns a new pair of access and refresh tokens.
        """
        payload = security.decode_refresh_token(refresh_token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        email = payload.get("sub")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token claims",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = await self.repository.get_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is inactive",
            )

        return self.create_user_token(user)

