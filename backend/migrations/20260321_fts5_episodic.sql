-- SQLite FTS5 Migration for HLSM Episodic Memory
-- This script creates a virtual table for full-text search and synchronization triggers.

-- 1. Create a contentless-delete FTS5 table (optimized for storage)
-- We store 'id' to map back to the main table and 'content' for indexing.
CREATE VIRTUAL TABLE IF NOT EXISTS hlsm_episodic_fts USING fts5(
    id UNINDEXED,
    content,
    tokenize='unicode61 remove_diacritics 1'
);

-- 2. Initial Data Load
INSERT OR IGNORE INTO hlsm_episodic_fts(id, content)
SELECT id, content FROM hlsm_episodic;

-- 3. Synchronization Triggers
-- After Insert
CREATE TRIGGER IF NOT EXISTS hlsm_episodic_after_insert
AFTER INSERT ON hlsm_episodic
BEGIN
    INSERT INTO hlsm_episodic_fts(id, content) VALUES (new.id, new.content);
END;

-- After Delete
CREATE TRIGGER IF NOT EXISTS hlsm_episodic_after_delete
AFTER DELETE ON hlsm_episodic
BEGIN
    DELETE FROM hlsm_episodic_fts WHERE id = old.id;
END;

-- After Update (if content changes)
CREATE TRIGGER IF NOT EXISTS hlsm_episodic_after_update
AFTER UPDATE OF content ON hlsm_episodic
BEGIN
    UPDATE hlsm_episodic_fts SET content = new.content WHERE id = old.id;
END;
