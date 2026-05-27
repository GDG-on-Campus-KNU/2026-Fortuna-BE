from io import BytesIO

from app.core.errors import AppError


class PDFExtractor:
    def extract_text(self, content: bytes) -> str:
        try:
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(content))
            parts = [page.extract_text() or "" for page in reader.pages]
        except Exception as exc:
            raise AppError(
                "PDF_EXTRACTION_FAILED",
                "Failed to extract text from PDF.",
                status_code=422,
                detail={"reason": exc.__class__.__name__},
            ) from exc

        text = "\n\n".join(part.strip() for part in parts if part.strip()).strip()
        if not text:
            raise AppError(
                "PDF_EXTRACTION_FAILED",
                "No extractable text found in PDF.",
                status_code=422,
            )
        return text

