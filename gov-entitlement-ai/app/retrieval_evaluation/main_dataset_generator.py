# app/retrieval_evaluation/main_dataset_generator.py

from app.core.database import get_db_conn, release_db_conn
from app.retrieval_evaluation.dataset_generator import (
    generate_dataset,
    clean_dataset,
    balance_dataset,
    save_dataset
)

conn = get_db_conn()

try:
    raw = generate_dataset(conn, per_doc_limit=20)

    cleaned = clean_dataset(raw)

    final = balance_dataset(cleaned, per_type_limit=25)

    save_dataset(final)

    print(f"Final dataset size: {len(final)}")

finally:
    release_db_conn(conn)