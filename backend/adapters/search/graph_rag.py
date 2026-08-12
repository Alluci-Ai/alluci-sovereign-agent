import sqlite3, os, logging, json
from typing import List, Dict, Any, Optional

logger = logging.getLogger("GraphRAG")

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "polytope_data.db"))

def init_graph_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS graph_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            entity_name TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            url TEXT,
            metadata JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS graph_edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            source_entity TEXT NOT NULL,
            relationship TEXT NOT NULL,
            target_entity TEXT NOT NULL,
            weight REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Failed initializing GraphRAG schema: {e}")

class GraphRAGStore:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        init_graph_db()

    def add_node(self, run_id: str, entity_name: str, entity_type: str, url: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(
                "INSERT INTO graph_nodes (run_id, entity_name, entity_type, url, metadata) VALUES (?, ?, ?, ?, ?)",
                (run_id, entity_name, entity_type, url, json.dumps(metadata or {}))
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Failed adding GraphRAG node '{entity_name}': {e}")

    def add_edge(self, run_id: str, source: str, relationship: str, target: str, weight: float = 1.0):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(
                "INSERT INTO graph_edges (run_id, source_entity, relationship, target_entity, weight) VALUES (?, ?, ?, ?, ?)",
                (run_id, source, relationship, target, weight)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Failed adding GraphRAG edge '{source} -> {target}': {e}")

    def query_graph(self, run_id: Optional[str] = None, entity_name: Optional[str] = None) -> Dict[str, Any]:
        nodes, edges = [], []
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            if run_id:
                c.execute("SELECT run_id, entity_name, entity_type, url, metadata FROM graph_nodes WHERE run_id = ?", (run_id,))
                nodes = c.fetchall()
                c.execute("SELECT run_id, source_entity, relationship, target_entity, weight FROM graph_edges WHERE run_id = ?", (run_id,))
                edges = c.fetchall()
            elif entity_name:
                c.execute("SELECT run_id, entity_name, entity_type, url, metadata FROM graph_nodes WHERE entity_name LIKE ?", (f"%{entity_name}%",))
                nodes = c.fetchall()
                c.execute("SELECT run_id, source_entity, relationship, target_entity, weight FROM graph_edges WHERE source_entity LIKE ? OR target_entity LIKE ?", (f"%{entity_name}%", f"%{entity_name}%"))
                edges = c.fetchall()
            conn.close()
        except Exception as e:
            logger.warning(f"Failed querying GraphRAG: {e}")
        return {"nodes": nodes, "edges": edges}
