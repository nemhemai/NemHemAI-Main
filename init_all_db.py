import psycopg2
import os
from glob import glob

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "5433")
DB_NAME = os.getenv("DB_NAME", "nemhem_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "12345678")

def apply_all():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    conn.autocommit = True
    
    # Get all sql files and sort them to run in correct order
    files = sorted(glob("app/database/schemas/*.sql"))
    
    with conn.cursor() as cur:
        for file in files:
            print(f"Executing {file}...")
            with open(file, "r", encoding="utf-8") as f:
                try:
                    cur.execute(f.read())
                    print(f"Success: {file}")
                except Exception as e:
                    print(f"Error in {file}: {e}")
                    
    conn.close()

if __name__ == "__main__":
    apply_all()
