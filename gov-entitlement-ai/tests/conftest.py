import os
from pathlib import Path

import pytest
import psycopg2
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def db_conn():
    load_dotenv(PROJECT_ROOT / ".env")
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
        )
    except psycopg2.Error as exc:
        pytest.skip(f"Postgres is not available for integration tests: {exc}")

    try:
        yield conn
    finally:
        conn.close()
