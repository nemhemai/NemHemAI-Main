# app/core/database.py
import psycopg2
from psycopg2 import pool
from app.core.config import settings

db_pool = None


def _get_pool():
    global db_pool
    if db_pool is not None:
        return db_pool

    try:
        db_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=20,
            dsn=settings.DATABASE_URL
        )
        print("Database Connection Pool Established")
        return db_pool
    except Exception as e:
        raise RuntimeError(
            f"Database connection failed for {settings.DATABASE_URL}: {e}"
        ) from e


def get_db_conn():
    return _get_pool().getconn()


def release_db_conn(conn):
    if conn is not None:
        _get_pool().putconn(conn)
