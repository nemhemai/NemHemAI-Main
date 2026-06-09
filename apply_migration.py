import psycopg2
import os

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5433")
DB_NAME = os.getenv("DB_NAME", "nemhem_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "12345678")

def apply():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    conn.autocommit = True
    
    with conn.cursor() as cur:
        with open("app/database/schemas/05_grievance_schema.sql", "r") as f:
            cur.execute(f.read())
        with open("app/database/schemas/05b_alter_grievances.sql", "r") as f:
            cur.execute(f.read())
        with open("app/database/schemas/06_add_severity_context.sql", "r") as f:
            cur.execute(f.read())
        with open("app/database/schemas/07_add_official_response.sql", "r") as f:
            cur.execute(f.read())
        print("Migrations 05, 05b, 06, 07 applied successfully.")
        
    conn.close()

if __name__ == "__main__":
    apply()
