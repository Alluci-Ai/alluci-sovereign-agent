-- 001_fts5_episodic.sql
-- Enables high-performance full-text search for the episodic memory layer.
-- This script is idempotent and can be run safely on every startup.

-- 1. Create the FTS5 virtual table if it doesn't exist
CREATE VIRTUAL TABLE IF NOT EXISTS episodic_memory_fts USING fts5(
    content,
    content='episodic_memory',
    content_rowid='id'
);

-- 2. Create triggers to keep the FTS index in sync with the base table
-- Trigger for INSERT
CREATE TRIGGER IF NOT EXISTS episodic_memory_ai AFTER INSERT ON episodic_memory BEGIN
  INSERT INTO episodic_memory_fts(rowid, content) VALUES (new.id, new.content);
END;

-- Trigger for DELETE
CREATE TRIGGER IF NOT EXISTS episodic_memory_ad AFTER DELETE ON episodic_memory BEGIN
  INSERT INTO episodic_memory_fts(episodic_memory_fts, rowid, content) VALUES('delete', old.id, old.content);
END;

-- Trigger for UPDATE
CREATE TRIGGER IF NOT EXISTS episodic_memory_au AFTER UPDATE ON episodic_memory BEGIN
  INSERT INTO episodic_memory_fts(episodic_memory_fts, rowid, content) VALUES('delete', old.id, old.content);
  INSERT INTO episodic_memory_fts(rowid, content) VALUES (new.id, new.content);
END;
