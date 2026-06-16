# create_db.py
import psycopg2
from app.core.config import settings

def main():
    try:
        # Connect to default 'postgres' database first to create 'nemhem_db'
        conn = psycopg2.connect(
            user=settings.DB_USER,
            password=settings.DB_PASS,
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            database="postgres"
        )
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = 'nemhem_db'")
            exists = cur.fetchone()
            if not exists:
                cur.execute("CREATE DATABASE nemhem_db")
                print("Database 'nemhem_db' created successfully.")
            else:
                print("Database 'nemhem_db' already exists.")
        conn.close()
    except Exception as e:
        print("Error creating database:", e)

if __name__ == "__main__":
    main()
