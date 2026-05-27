from fastapi import APIRouter, Depends, File, UploadFile

from app.core.config import Settings, get_settings
from app.core.deps import get_current_user_id, get_source_service
from app.domain.source.schemas import UploadResponse
from app.domain.source.service import SourceService


router = APIRouter(tags=["uploads"])


@router.post("/uploads", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    settings: Settings = Depends(get_settings),
    source_service: SourceService = Depends(get_source_service),
) -> UploadResponse:
    content = await file.read(settings.max_upload_bytes + 1)
    record = source_service.upload_and_extract(
        user_id=user_id,
        filename=file.filename,
        content_type=file.content_type,
        content=content,
    )
    return UploadResponse(**record)

