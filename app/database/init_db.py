# app/database/init_db.py

import os
from pathlib import Path

from app.core.database import get_db_conn, release_db_conn


def execute_sql_file(cursor, file_path):
    print(f"\nRunning: {file_path.name}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            sql = f.read()
        
        # Split statements and execute individually
        cursor.execute(sql)
    except Exception as e:
        print(f"Error executing {file_path.name}: {e}")
        raise


def initialize_database():

    conn = None
    cur = None

    try:

        conn = get_db_conn()
        cur = conn.cursor()

        schema_dir = Path(__file__).parent / "schemas"

        sql_files = sorted(schema_dir.glob("*.sql"))

        print("\n--- INITIALIZING DATABASE SCHEMA ---\n")

        for file in sql_files:

            print(f"Running: {file.name}")

            execute_sql_file(cur, file)

        conn.commit()

        print("\nDatabase schema initialized successfully.\n")

    except Exception as e:

        if conn:
            conn.rollback()

        print("\nDatabase initialization failed\n")
        print(e)

        raise

    finally:

        if cur:
            cur.close()

        if conn:
            release_db_conn(conn)


if __name__ == "__main__":
    initialize_database()