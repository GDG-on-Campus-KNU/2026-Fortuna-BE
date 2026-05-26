import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    """
    Data Access Object (DAO) for the User entity.
    Encapsulates database operations for cleaner service-level calls.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Fetches a user by their unique email.
        """
        query = select(User).where(User.email == email)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """
        Fetches a user by their primary key UUID.
        """
        return await self.db.get(User, user_id)

    async def create(self, email: str, hashed_password: str) -> User:
        """
        Creates and inserts a new user record into the database.
        """
        db_user = User(email=email, hashed_password=hashed_password)
        self.db.add(db_user)
        await (
            self.db.flush()
        )  # Flushes changes to populate model ID and default constraints
        return db_user
