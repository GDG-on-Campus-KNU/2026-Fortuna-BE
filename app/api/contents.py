from fastapi import APIRouter, Depends

from app.core.deps import get_content_service, get_current_user_id
from app.domain.content.schemas import ContentListItem, ContentResponse
from app.domain.content.service import ContentService


router = APIRouter(tags=["contents"])


@router.get("/contents", response_model=list[ContentListItem])
def list_contents(
    user_id: str = Depends(get_current_user_id),
    content_service: ContentService = Depends(get_content_service),
) -> list[ContentListItem]:
    return [
        ContentListItem(**content)
        for content in content_service.list_contents(user_id)
    ]


@router.get("/contents/{content_id}", response_model=ContentResponse)
def get_content(
    content_id: str,
    user_id: str = Depends(get_current_user_id),
    content_service: ContentService = Depends(get_content_service),
) -> ContentResponse:
    return ContentResponse(**content_service.get_content(user_id, content_id))

