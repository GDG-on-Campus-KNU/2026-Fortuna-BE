from app.core.errors import AppError
from app.domain.audio.schemas import AudioAsset, MusicOptions


class NullMusicGenerator:
    def generate(self, options: MusicOptions) -> AudioAsset | None:
        if options.enabled:
            raise AppError(
                "MUSIC_GENERATION_NOT_IMPLEMENTED",
                "Music generation is not implemented yet.",
                status_code=501,
            )
        return None

