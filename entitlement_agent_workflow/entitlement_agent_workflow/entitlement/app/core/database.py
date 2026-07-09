# app/core/database.py
import os
import psycopg2
from psycopg2 import pool

db_pool = None


def _get_pool():
    global db_pool
    if db_pool is not None:
        return db_pool

    # Connect to local postgres DB on port 5433 (default for nemhem_db)
    db_user = os.getenv("DB_USER", "postgres")
    db_pass = os.getenv("DB_PASS", "postgres")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5433")
    db_name = os.getenv("DB_NAME", "nemhem_db")

    database_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

    try:
        db_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=20,
            dsn=database_url
        )
        print("Database Connection Pool Established")
        return db_pool
    except Exception as e:
        raise RuntimeError(
            f"Database connection failed for {database_url}: {e}"
        ) from e


def get_db_conn():
    return _get_pool().getconn()


def release_db_conn(conn):
    if conn is not None:
        _get_pool().putconn(conn)
