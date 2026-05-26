from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core import security
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserRead, Token
from app.services.auth_service import AuthService

# Defines the token URL for swagger interactive docs compatibility
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

router = APIRouter(prefix="/auth", tags=["Authentication"])


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency function that extracts and validates the JWT from incoming request headers.
    Returns the User model or raises HTTP 401.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decrypt and decode the token
    payload = security.decode_access_token(token)
    if payload is None:
        raise credentials_exception

    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception

    # Verify the user exists in our DB
    repository = UserRepository(db)
    user = await repository.get_by_email(email)
    if user is None:
        raise credentials_exception

    return user


@router.post(
    "/signup",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def signup(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Creates a new user profile.
    Checks password strength, duplicates, and hashes plain text passwords safely.
    """
    auth_service = AuthService(db)
    new_user = await auth_service.register_user(user_in)
    return new_user


@router.post("/login", response_model=Token, summary="User Login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    """
    Standard OAuth2-compliant login endpoint.
    Accepts application/x-www-form-urlencoded inputs (username & password).
    Returns a JWT access token if validation succeeds.
    """
    auth_service = AuthService(db)
    # OAuth2PasswordRequestForm stores email inside the 'username' attribute
    authenticated_user = await auth_service.authenticate_user(
        email=form_data.username, plain_password=form_data.password
    )
    token = auth_service.create_user_token(authenticated_user)
    return token


@router.get("/me", response_model=UserRead, summary="Get current user profile")
async def read_current_user(current_user: User = Depends(get_current_user)):
    """
    Protected route. Returns the profile of the currently logged-in user.
    """
    return current_user
