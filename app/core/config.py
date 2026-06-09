#app/core/config.py
import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "NEMHEM AI - SWM HYBRID RAG"

    # Database Settings
    DB_USER: str = "postgres"
    DB_PASS: str = "12345678"
    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"
    DB_NAME: str = "nemhem_db"

    # AI Model Settings
    EMBED_MODEL_PATH: str = os.path.join(os.getcwd(), "models/bge-m3")
    VECTOR_DIM: int = 1024

    # Neo4j Graph Settings
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    # Voice Agent Settings (Phase 3)
    BHASHINI_API_KEY: str = ""
    BHASHINI_ENDPOINT: str = "https://bhashini.gov.in/api"
    WHISPER_MODEL_PATH: str = os.path.join(os.getcwd(), "models/whisper")
    INDICBERT_MODEL_PATH: str = os.path.join(os.getcwd(), "models/indicbert")
    HAPTIK_WEBHOOK_SECRET: str = ""

    @property
    def DATABASE_URL(self):
        return f"postgresql://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()