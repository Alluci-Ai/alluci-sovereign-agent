import asyncio
import sqlite3
import redis
from backend.database import engine

def clear_sql():
    from sqlmodel import Session, text
    with Session(engine) as session:
        for table in ["hlsm_working", "hlsm_episodic", "hlsm_episodic_fts"]:
            try:
                session.execute(text(f"DELETE FROM {table}"))
            except Exception as e:
                pass
        session.commit()
    print("SQL cleared.")

def clear_redis():
    try:
        r = redis.Redis(host='localhost', port=6379, db=0)
        keys = r.keys("hlsm:working:*")
        for k in keys:
            r.delete(k)
        print("Redis cleared.")
    except Exception:
        print("Redis not available.")

def clear_kuzu():
    import kuzu
    try:
        from backend.config import settings
        db = kuzu.Database(settings.KUZU_DB_PATH)
        conn = kuzu.Connection(db)
        conn.execute("MATCH (a)-[r]->(b) DELETE r")
        conn.execute("MATCH (n) DELETE n")
        print("Kuzu cleared.")
    except Exception as e:
        print("Kuzu not cleared:", e)

if __name__ == "__main__":
    clear_sql()
    clear_redis()
    clear_kuzu()
