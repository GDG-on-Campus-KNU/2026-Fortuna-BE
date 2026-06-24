from fastapi import APIRouter, Depends, File, UploadFile, status
from app.core.deps import (
    get_current_user_id,
    get_notebook_service,
    get_podcast_service,
    get_source_service,
    get_settings,
)
from app.core.config import Settings
from app.domain.notebook.service import NotebookService
from app.domain.podcast.service import PodcastService
from app.domain.source.service import SourceService
from app.domain.notebook.schemas import (
    NotebookCreateRequest,
    NotebookResponse,
    SourceResponse,
)

router = APIRouter(tags=["notebooks"])


@router.get("/notebooks", response_model=list[NotebookResponse])
def list_notebooks(
    user_id: str = Depends(get_current_user_id),
    notebook_service: NotebookService = Depends(get_notebook_service),
    podcast_service: PodcastService = Depends(get_podcast_service),
    source_service: SourceService = Depends(get_source_service),
) -> list[NotebookResponse]:
    notebooks = notebook_service.list_notebooks(user_id)
    return [
        NotebookResponse(
            **notebook_service.assemble_notebook_response(
                user_id, n, podcast_service, source_service
            )
        )
        for n in notebooks
    ]


@router.get("/notebooks/{notebook_id}", response_model=NotebookResponse)
def get_notebook(
    notebook_id: str,
    user_id: str = Depends(get_current_user_id),
    notebook_service: NotebookService = Depends(get_notebook_service),
    podcast_service: PodcastService = Depends(get_podcast_service),
    source_service: SourceService = Depends(get_source_service),
) -> NotebookResponse:
    notebook = notebook_service.get_notebook(user_id, notebook_id)
    return NotebookResponse(
        **notebook_service.assemble_notebook_response(
            user_id, notebook, podcast_service, source_service
        )
    )


@router.post("/notebooks", response_model=NotebookResponse, status_code=201)
def create_notebook(
    request: NotebookCreateRequest,
    user_id: str = Depends(get_current_user_id),
    notebook_service: NotebookService = Depends(get_notebook_service),
    podcast_service: PodcastService = Depends(get_podcast_service),
    source_service: SourceService = Depends(get_source_service),
) -> NotebookResponse:
    notebook = notebook_service.create_notebook(user_id, request.title)
    return NotebookResponse(
        **notebook_service.assemble_notebook_response(
            user_id, notebook, podcast_service, source_service
        )
    )


@router.delete("/notebooks/{notebook_id}", status_code=204)
def delete_notebook(
    notebook_id: str,
    user_id: str = Depends(get_current_user_id),
    notebook_service: NotebookService = Depends(get_notebook_service),
) -> None:
    notebook_service.delete_notebook(user_id, notebook_id)


@router.post(
    "/notebooks/{notebook_id}/sources",
    response_model=SourceResponse,
    status_code=201,
)
async def upload_source(
    notebook_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    notebook_service: NotebookService = Depends(get_notebook_service),
    source_service: SourceService = Depends(get_source_service),
    settings: Settings = Depends(get_settings),
) -> SourceResponse:
    content = await file.read(settings.max_upload_bytes + 1)
    file_record = source_service.upload_and_extract(
        user_id=user_id,
        filename=file.filename,
        content_type=file.content_type,
        content=content,
    )
    notebook_service.add_source(user_id, notebook_id, file_record)
    return _source_response(file_record)


@router.post(
    "/notebooks/{notebook_id}/sources/batch",
    response_model=list[SourceResponse],
    status_code=201,
)
async def upload_sources_batch(
    notebook_id: str,
    files: list[UploadFile] = File(...),
    user_id: str = Depends(get_current_user_id),
    notebook_service: NotebookService = Depends(get_notebook_service),
    source_service: SourceService = Depends(get_source_service),
    settings: Settings = Depends(get_settings),
) -> list[SourceResponse]:
    uploaded: list[SourceResponse] = []
    for file in files:
        content = await file.read(settings.max_upload_bytes + 1)
        file_record = source_service.upload_and_extract(
            user_id=user_id,
            filename=file.filename,
            content_type=file.content_type,
            content=content,
        )
        notebook_service.add_source(user_id, notebook_id, file_record)
        uploaded.append(_source_response(file_record))
    return uploaded


@router.delete("/notebooks/{notebook_id}/sources/{source_id}", status_code=204)
def remove_source(
    notebook_id: str,
    source_id: str,
    user_id: str = Depends(get_current_user_id),
    notebook_service: NotebookService = Depends(get_notebook_service),
    source_service: SourceService = Depends(get_source_service),
) -> None:
    notebook_service.remove_source(user_id, notebook_id, source_id)
    source_service.delete_source(user_id, source_id)


def _source_response(file_record: dict) -> SourceResponse:
    return SourceResponse(
        id=file_record["file_id"],
        name=file_record["filename"],
        type="PDF" if file_record["content_type"] == "application/pdf" else "txt",
        created_at=file_record["created_at"],
        updated_at=file_record.get("updated_at") or file_record["created_at"],
    )
