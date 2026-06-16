#app/core/config.py
import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):

    APP_NAME: str = "NEMHEM AI - SWM HYBRID RAG"

    # Database Settings
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASS: str = os.getenv("DB_PASS", "sana")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "nemhem_db")

    # AI Model Settings
    EMBED_MODEL_PATH: str = os.path.join(os.getcwd(), "models/bge-m3")
    VECTOR_DIM: int = 1024

    @property
    def DATABASE_URL(self):
        return f"postgresql://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()