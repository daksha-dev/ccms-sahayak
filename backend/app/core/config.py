from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    sarvam_api_key: str | None = None
    openrouter_api_key: str | None = None
    gemini_model: str = "google/gemini-2.0-flash-001"
    ocr_confidence_threshold: float = 0.55
    database_url: str = "sqlite:///./ccms_sahayak.db"
    pdf_storage_path: str = "./storage/pdfs"
    sarvam_translate_url: str = "https://api.sarvam.ai/translate"
    sarvam_document_intelligence_url: str = "https://api.sarvam.ai/doc-digitization/job/v1"
    openrouter_url: str = "https://openrouter.ai/api/v1/chat/completions"

    model_config = SettingsConfigDict(env_file=("../.env", ".env"), env_file_encoding="utf-8")

    @property
    def pdf_storage_dir(self) -> Path:
        path = Path(self.pdf_storage_path)
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()
