from pydantic import BaseModel
from typing import Literal
from app.domain.podcast.schemas import PodcastResponse

class NotebookCreateRequest(BaseModel):
    title: str

class SourceResponse(BaseModel):
    id: str
    name: str
    type: Literal["PDF", "txt"]
    created_at: str
    updated_at: str

class NotebookResponse(BaseModel):
    id: str
    title: str
    podcasts: list[PodcastResponse]
    sources: list[SourceResponse]
    created_at: str
    updated_at: str
