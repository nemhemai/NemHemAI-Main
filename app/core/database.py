# app/core/database.py
import psycopg2
from psycopg2 import pool
from app.core.config import settings
import sys

try:
    db_pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=20,
        dsn=settings.DATABASE_URL
    )

    if db_pool:
        print("Database Connection Pool Established")

except Exception as e:
    print("Database connection failed")
    print(settings.DATABASE_URL)
    print(e)
    sys.exit(1)


def get_db_conn():
    return db_pool.getconn()


def release_db_conn(conn):
    db_pool.putconn(conn)