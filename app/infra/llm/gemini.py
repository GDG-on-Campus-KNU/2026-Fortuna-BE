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

    def generate_title(self, source_text: str) -> str:
        if not self.settings.gemini_api_key:
            return "무제 팟캐스트"
        try:
            from google import genai

            client = genai.Client(api_key=self.settings.gemini_api_key)
            prompt = (
                "자료 내용을 바탕으로 팟캐스트에 어울리는 짧고 매력적인 한글 제목을 하나 지어줘. "
                "다른 부연 설명이나 따옴표 없이 오직 제목만 한 줄로 출력해야 해. 자료 내용:\n\n"
                f"{source_text[:2000]}"
            )
            response = client.models.generate_content(
                model=self.settings.gemini_model,
                contents=prompt,
            )
            title = (response.text or "").strip()
            # Clean up wrap quotes
            return title.strip('"').strip("'")
        except Exception:
            return ""

