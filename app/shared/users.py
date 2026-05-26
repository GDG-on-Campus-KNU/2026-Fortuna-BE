import re

from app.core.errors import AppError


USER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def validate_user_id(value: str) -> str:
    user_id = value.strip()
    if not USER_ID_PATTERN.fullmatch(user_id):
        raise AppError(
            "INVALID_USER",
            "User id must match ^[A-Za-z0-9_-]{1,64}$.",
            status_code=400,
            detail={"allowed_pattern": USER_ID_PATTERN.pattern},
        )
    return user_id
