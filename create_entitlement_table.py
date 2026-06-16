import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_db_conn, release_db_conn

def create_table():
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS entitlement_queries (
                    query_id VARCHAR(255) PRIMARY KEY,
                    user_id VARCHAR(255),
                    citizen_id VARCHAR(255),
                    raw_query TEXT NOT NULL,
                    extracted_profile JSONB,
                    scheme_matches JSONB,
                    determination JSONB,
                    status VARCHAR(50) DEFAULT 'PENDING',
                    error_message TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
        conn.commit()
        print("Table 'entitlement_queries' created successfully.")
    except Exception as e:
        print(f"Error creating table: {e}")
    finally:
        release_db_conn(conn)

if __name__ == "__main__":
    create_table()
