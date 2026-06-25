"""Settings derived from main app config."""
from app.core.config import settings as main_settings

class Settings:
    @property
    def database_url(self):
        # SQLAlchemy needs +psycopg2 for postgres URLs sometimes, but modern versions parse postgresql:// fine.
        url = main_settings.DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg2://")
        return url

    @property
    def neo4j_uri(self):
        return main_settings.NEO4J_URI

    @property
    def neo4j_user(self):
        return main_settings.NEO4J_USER

    @property
    def neo4j_password(self):
        return main_settings.NEO4J_PASSWORD

    app_env: str = "dev"

settings = Settings()
