import os
from celery import Celery

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "worker",
    broker=REDIS_URL,
    backend=REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # We want exactly 1 concurrent worker to process PDF extraction/embeddings
    # safely without running out of RAM (BGE-M3 is heavy).
    worker_concurrency=1,
    worker_prefetch_multiplier=1,
)

# Autodiscover tasks so we don't have to import them manually here
celery_app.autodiscover_tasks(['app.ingestion_orchestrator'])
