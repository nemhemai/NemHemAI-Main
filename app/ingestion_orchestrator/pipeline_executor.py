# app/ingestion_orchestrator/pipeline_executor.py

from concurrent.futures import ThreadPoolExecutor
from app.ingestion_orchestrator.ingestion_orchestrator import run_full_pipeline
import threading


# keep small to avoid CPU overload (OCR + embedding heavy)
executor = ThreadPoolExecutor(max_workers=2)
executor_lock = threading.Lock()
    
def safe_pipeline_runner(job_id, file_path, metadata):
    try:
        run_full_pipeline(job_id, file_path, metadata)
    except Exception as e:
        print(f"Background pipeline failed: {e}")

def start_pipeline_async(job_id, file_path, metadata):
    try:
        with executor_lock:
            executor.submit(safe_pipeline_runner, job_id, file_path, metadata)
    except RuntimeError as e:
        print(f"Executor rejected task: {e}")