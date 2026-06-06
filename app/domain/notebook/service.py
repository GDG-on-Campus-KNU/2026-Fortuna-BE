from app.core.errors import AppError
from app.domain.notebook.repository import NotebookRepository
from app.domain.podcast.service import PodcastService
from app.domain.source.service import SourceService
from app.shared.ids import new_id
from app.shared.time import utc_now_iso

class NotebookService:
    def __init__(self, repository: NotebookRepository) -> None:
        self.repository = repository

    def create_notebook(self, user_id: str, title: str) -> dict:
        notebook_id = new_id("nb")
        now = utc_now_iso()
        record = {
            "notebook_id": notebook_id,
            "user_id": user_id,
            "title": title,
            "sources": [],
            "podcasts": [],
            "created_at": now,
            "updated_at": now,
        }
        return self.repository.save_notebook(record)

    def get_notebook(self, user_id: str, notebook_id: str) -> dict:
        record = self.repository.get_notebook(notebook_id, user_id)
        if not record:
            raise AppError("NOTEBOOK_NOT_FOUND", "Notebook not found.", status_code=404)
        return record

    def list_notebooks(self, user_id: str) -> list[dict]:
        return self.repository.list_notebooks(user_id)

    def delete_notebook(self, user_id: str, notebook_id: str) -> None:
        self.get_notebook(user_id, notebook_id)
        self.repository.delete_notebook(notebook_id, user_id)

    def add_source(self, user_id: str, notebook_id: str, file_record: dict) -> dict:
        notebook = self.get_notebook(user_id, notebook_id)
        sources = list(notebook.get("sources", []))
        file_id = file_record["file_id"]
        if file_id not in sources:
            sources.append(file_id)
            notebook["sources"] = sources
            notebook["updated_at"] = utc_now_iso()
            self.repository.save_notebook(notebook)
        return file_record

    def remove_source(self, user_id: str, notebook_id: str, source_id: str) -> None:
        notebook = self.get_notebook(user_id, notebook_id)
        sources = list(notebook.get("sources", []))
        if source_id in sources:
            sources.remove(source_id)
            notebook["sources"] = sources
            notebook["updated_at"] = utc_now_iso()
            self.repository.save_notebook(notebook)

    def add_podcast(self, user_id: str, notebook_id: str, podcast_id: str) -> None:
        notebook = self.get_notebook(user_id, notebook_id)
        podcasts = list(notebook.get("podcasts", []))
        if podcast_id not in podcasts:
            podcasts.append(podcast_id)
            notebook["podcasts"] = podcasts
            notebook["updated_at"] = utc_now_iso()
            self.repository.save_notebook(notebook)

    def assemble_notebook_response(
        self,
        user_id: str,
        notebook: dict,
        podcast_service: PodcastService,
        source_service: SourceService,
    ) -> dict:
        sources_list = []
        for file_id in notebook.get("sources", []):
            file_record = source_service.repository.get_file(file_id, user_id)
            if file_record:
                sources_list.append({
                    "id": file_record["file_id"],
                    "name": file_record["filename"],
                    "type": "PDF" if file_record["content_type"] == "application/pdf" else "txt",
                    "created_at": file_record["created_at"],
                    "updated_at": file_record.get("updated_at") or file_record["created_at"],
                })

        notebook_podcasts = []
        for podcast_id in notebook.get("podcasts", []):
            try:
                p = podcast_service.get_podcast(user_id, podcast_id)
                notebook_podcasts.append(p)
            except Exception:
                continue

        return {
            "id": notebook["notebook_id"],
            "title": notebook["title"],
            "podcasts": notebook_podcasts,
            "sources": sources_list,
            "created_at": notebook["created_at"],
            "updated_at": notebook["updated_at"],
        }
