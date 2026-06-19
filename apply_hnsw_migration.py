import psycopg2
import os

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5433")
DB_NAME = os.getenv("DB_NAME", "nemhem_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "12345678")

def apply():
    print("Connecting to database...")
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    conn.autocommit = True
    
    print("Applying 05_chunks_embedding_schema.sql...")
    with conn.cursor() as cur:
        with open("app/database/schemas/05_chunks_embedding_schema.sql", "r", encoding="utf-8") as f:
            cur.execute(f.read())
        print("Migration 05_chunks_embedding_schema.sql applied successfully.")
        
    conn.close()

if __name__ == "__main__":
    apply()
