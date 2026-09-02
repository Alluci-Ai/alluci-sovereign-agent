import kuzu
from backend.config import settings

def clear_kuzu():
    try:
        db = kuzu.Database(settings.GRAPH_DB_PATH)
        conn = kuzu.Connection(db)
        del_queries = [
            "MATCH ()-[r:DEFINES_CONCEPT]->() DELETE r",
            "MATCH ()-[r:HAS_PAGE]->() DELETE r",
            "MATCH ()-[r:HAS_KEY_POINT]->() DELETE r",
            "MATCH ()-[r:RELATES_TO]->() DELETE r",
            "MATCH (a)-[r]->(b) DELETE r",
            "MATCH (c:ConceptNode) DELETE c",
            "MATCH (k:KeyPointNode) DELETE k",
            "MATCH (p:PageNode) DELETE p",
            "MATCH (d:DocumentNode) DELETE d",
            "MATCH (g:GraphNode) DELETE g",
            "MATCH (m:SemanticMemory) DELETE m",
            "MATCH (l:L3Memory) DELETE l",
            "MATCH (n) DELETE n",
        ]
        for q in del_queries:
            try:
                conn.execute(q)
            except Exception:
                pass
        print("KuzuDB L3 memories cleared successfully.")
    except Exception as e:
        print("KuzuDB err:", e)

if __name__ == "__main__":
    clear_kuzu()
