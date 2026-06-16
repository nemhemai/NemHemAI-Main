from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):

    # =========================================
    # APPLICATION
    # =========================================

    APP_NAME: str = (
        "NemHemAI - Government Document Verification AI Agent"
    )

    APP_ENV: str = "development"

    DEBUG: bool = True

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # =========================================
    # STORAGE
    # =========================================

    STORAGE_DIR: str = "storage"

    UPLOAD_DIR: str = "storage/uploads"

    NORMALIZED_DIR: str = (
        "storage/normalized"
    )

    PROCESSED_DIR: str = (
        "storage/processed"
    )

    TEMP_DIR: str = "storage/temp"

    LOG_DIR: str = "storage/logs"

    # =========================================
    # VALIDATION
    # =========================================

    MAX_FILE_SIZE_MB: int = 10

    # =========================================
    # ENV CONFIG
    # =========================================

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()