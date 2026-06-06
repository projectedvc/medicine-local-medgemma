from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Radiology AI Assistant"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./data/medicine.db"
    jwt_secret: str = Field(default="change-me-in-production", alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8

    upload_dir: Path = Path("./data/uploads")
    export_dir: Path = Path("./data/exports")
    max_upload_mb: int = 50
    allowed_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="ALLOWED_ORIGINS",
    )

    ai_provider: str = Field(default="local_medgemma", alias="AI_PROVIDER")
    ai_service_url: str | None = Field(default=None, alias="AI_SERVICE_URL")
    ai_timeout_seconds: int = 120
    ai_confidence_threshold: float = Field(default=0.70, alias="AI_CONFIDENCE_THRESHOLD")
    ai_allow_mock: bool = Field(default=False, alias="AI_ALLOW_MOCK")
    ai_model_version: str = Field(default="local-ai", alias="AI_MODEL_VERSION")
    ai_dataset_version: str = Field(default="local-unvalidated", alias="AI_DATASET_VERSION")
    local_medgemma_model_id: str = Field(default="google/medgemma-1.5-4b-it", alias="LOCAL_MEDGEMMA_MODEL_ID")
    local_medgemma_model_path: Path = Field(
        default=Path("../models/medgemma-1.5-4b-it"),
        alias="LOCAL_MEDGEMMA_MODEL_PATH",
    )
    local_medgemma_local_files_only: bool = Field(default=True, alias="LOCAL_MEDGEMMA_LOCAL_FILES_ONLY")
    local_medgemma_device: str = Field(default="auto", alias="LOCAL_MEDGEMMA_DEVICE")
    local_medgemma_dtype: str = Field(default="auto", alias="LOCAL_MEDGEMMA_DTYPE")
    local_medgemma_load_in_4bit: bool = Field(default=False, alias="LOCAL_MEDGEMMA_LOAD_IN_4BIT")
    local_medgemma_max_new_tokens: int = Field(default=350, alias="LOCAL_MEDGEMMA_MAX_NEW_TOKENS")
    local_medgemma_max_image_side: int = Field(default=1600, alias="LOCAL_MEDGEMMA_MAX_IMAGE_SIDE")

    pdf_font_path: str | None = Field(default=None, alias="PDF_FONT_PATH")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
