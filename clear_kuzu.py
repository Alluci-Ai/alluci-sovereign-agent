import kuzu
try:
    db = kuzu.Database("./polytope_data.kuzu")
    conn = kuzu.Connection(db)
    conn.execute("MATCH (a)-[r]->(b) DELETE r")
    conn.execute("MATCH (n) DELETE n")
    print("KuzuDB cleared.")
except Exception as e:
    print("KuzuDB err:", e)
