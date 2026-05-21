from fastapi import HTTPException, status
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
        new_user = await self.repository.create(
            email=user_in.email, hashed_password=hashed_password
        )
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
        Generates a standard bearer JWT token for the authenticated user.
        """
        # The 'sub' field in JWT typically represents the subject (the email in this case)
        access_token = security.create_access_token(data={"sub": user.email})
        return Token(access_token=access_token, token_type="bearer")
