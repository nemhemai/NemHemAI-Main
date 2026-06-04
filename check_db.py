import asyncio
import asyncpg

async def check():
    pool = await asyncpg.create_pool(
        'postgresql://postgres:12345678@localhost:5433/nemhem_db',
        min_size=1, max_size=2
    )
    async with pool.acquire() as conn:
        tables = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname='public'")
        print("=== TABLES ===")
        for t in tables:
            print(" -", t['tablename'])

        # Try to find docs table
        for tname in ['documents', 'document', 'files', 'ingestion_jobs']:
            try:
                rows = await conn.fetch(
                    f"SELECT filename, status, error_message FROM {tname} WHERE status IN ('extracting','failed') LIMIT 10"
                )
                print(f"\n=== {tname} stuck rows ===")
                for r in rows:
                    print(r['filename'], '|', r['status'], '|', str(r.get('error_message', ''))[:100])
            except Exception as e:
                pass

    await pool.close()

asyncio.run(check())
