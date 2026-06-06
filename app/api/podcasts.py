from fastapi import APIRouter, Depends
from app.core.deps import get_podcast_service, get_current_user_id
from app.domain.podcast.schemas import PodcastListItem, PodcastResponse
from app.domain.podcast.service import PodcastService

router = APIRouter(tags=["podcasts"])


@router.get("/podcasts", response_model=list[PodcastListItem])
def list_podcasts(
    user_id: str = Depends(get_current_user_id),
    podcast_service: PodcastService = Depends(get_podcast_service),
) -> list[PodcastListItem]:
    return [
        PodcastListItem(**podcast)
        for podcast in podcast_service.list_podcasts(user_id)
    ]


@router.get("/podcasts/{podcast_id}", response_model=PodcastResponse)
def get_podcast(
    podcast_id: str,
    user_id: str = Depends(get_current_user_id),
    podcast_service: PodcastService = Depends(get_podcast_service),
) -> PodcastResponse:
    return PodcastResponse(**podcast_service.get_podcast(user_id, podcast_id))


@router.delete("/podcasts/{podcast_id}", status_code=204)
def delete_podcast(
    podcast_id: str,
    user_id: str = Depends(get_current_user_id),
    podcast_service: PodcastService = Depends(get_podcast_service),
) -> None:
    podcast_service.delete_podcast(user_id, podcast_id)
