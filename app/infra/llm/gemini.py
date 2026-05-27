from app.core.config import Settings
from app.core.errors import AppError


class GeminiService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_script(self, prompt: str) -> str:
        if not self.settings.gemini_api_key:
            raise AppError(
                "GEMINI_GENERATION_FAILED",
                "GEMINI_API_KEY is not configured.",
                status_code=503,
            )
        try:
            from google import genai

            client = genai.Client(api_key=self.settings.gemini_api_key)
            response = client.models.generate_content(
                model=self.settings.gemini_model,
                contents=prompt,
            )
            script = (response.text or "").strip()
        except Exception as exc:
            raise AppError(
                "GEMINI_GENERATION_FAILED",
                "Failed to generate script with Gemini API.",
                status_code=502,
                detail={"reason": exc.__class__.__name__},
            ) from exc
        if not script:
            raise AppError(
                "GEMINI_GENERATION_FAILED",
                "Gemini API returned an empty script.",
                status_code=502,
            )
        return script

