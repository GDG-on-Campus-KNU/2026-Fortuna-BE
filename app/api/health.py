import os

from fastapi import APIRouter


router = APIRouter(tags=["health"])

# Deploy marker for CD verification. Render injects RENDER_GIT_COMMIT; GIT_COMMIT
# is a portable fallback (e.g. a build arg on Cloud Run). Read once at import.
COMMIT = os.getenv("RENDER_GIT_COMMIT") or os.getenv("GIT_COMMIT") or "unknown"


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "commit": COMMIT}
