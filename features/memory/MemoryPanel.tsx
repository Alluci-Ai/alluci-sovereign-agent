
import React, { useState, useEffect, useCallback } from 'react';
import { useStore } from '../../store/useStore';
import { Search, Plus, Trash2, FileText, Database, Info, Upload } from 'lucide-react';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

export const MemoryPanel: React.FC<{ onClose: () => void }> = ({ onClose }) => {
    const { accessToken } = useStore();
    const [memories, setMemories] = useState<any[]>([]);
    const [stats, setStats] = useState<any>(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [isIngesting, setIsIngesting] = useState(false);
    const [ingestPath, setIngestPath] = useState('');

    const fetchMemories = useCallback(async () => {
        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/memory?limit=50`, {
                headers: { 'Authorization': `Bearer ${accessToken}` }
            });
            if (res.ok) {
                const data = await res.json();
                // ChromaDB response format: { ids: [], documents: [], metadatas: [] }
                const formatted = (data.ids || []).map((id: string, i: number) => ({
                    id,
                    content: data.documents[i],
                    metadata: data.metadatas[i]
                }));
                setMemories(formatted);
            }
        } catch (e) { console.error("Failed to fetch memories", e); }
    }, [accessToken]);

    const fetchStats = useCallback(async () => {
        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/memory/stats`, {
                headers: { 'Authorization': `Bearer ${accessToken}` }
            });
            if (res.ok) setStats(await res.json());
        } catch (e) { }
    }, [accessToken]);

    useEffect(() => {
        fetchMemories();
        fetchStats();
    }, [fetchMemories, fetchStats]);

    const handleSearch = async () => {
        if (!searchQuery.trim()) {
            fetchMemories();
            return;
        }
        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/memory/search?q=${encodeURIComponent(searchQuery)}`, {
                headers: { 'Authorization': `Bearer ${accessToken}` }
            });
            if (res.ok) setMemories(await res.json());
        } catch (e) { }
    };

    const handleDelete = async (id: string) => {
        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/memory/${id}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${accessToken}` }
            });
            if (res.ok) {
                setMemories(prev => prev.filter(m => m.id !== id));
                fetchStats();
            }
        } catch (e) { }
    };

    const handleIngest = async () => {
        if (!ingestPath.trim()) return;
        setIsIngesting(true);
        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/memory/ingest`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${accessToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(ingestPath)
            });
            if (res.ok) {
                setIngestPath('');
                fetchMemories();
                fetchStats();
            }
        } catch (e) { }
        setIsIngesting(false);
    };

    return (
        <div style={{
            maxWidth: 800, width: '100%', margin: '0 auto',
            display: 'flex', flexDirection: 'column', height: '100%',
        }}>
            {/* Header / Stats */}
            <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                    <h3 style={{ fontSize: 24, fontWeight: 700, letterSpacing: '-0.02em', marginBottom: 4 }}>Semantic Memory</h3>
                    <p style={{ fontSize: 13, color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
                        CHROMA_PERSISTENT_COLLECTION: {stats?.name || 'Loading...'}
                    </p>
                </div>
                {stats && (
                    <div className="glass-card" style={{ padding: '8px 16px', display: 'flex', gap: 16 }}>
                        <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: 10, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Vectors</div>
                            <div style={{ fontSize: 18, fontWeight: 600 }}>{stats.count}</div>
                        </div>
                        <div style={{ width: 1, background: 'var(--separator)' }} />
                        <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: 10, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Space</div>
                            <div style={{ fontSize: 18, fontWeight: 600 }}>Cosine</div>
                        </div>
                    </div>
                )}
            </div>

            {/* Ingestion & Search Bar */}
            <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
                <div style={{ flex: 1, position: 'relative' }}>
                    <Search size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', opacity: 0.5 }} />
                    <input
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                        placeholder="Search semantic memory..."
                        className="glass-input"
                        style={{ paddingLeft: 38, width: '100%' }}
                    />
                </div>
                <div style={{ display: 'flex', gap: 8, background: 'var(--fill-quaternary)', borderRadius: 12, padding: 4, border: '1px solid var(--separator)' }}>
                    <input
                        value={ingestPath}
                        onChange={(e) => setIngestPath(e.target.value)}
                        placeholder="Path to PDF/DOCX/TXT..."
                        className="glass-input"
                        style={{ width: 200, fontSize: 12, border: 'none', background: 'transparent' }}
                    />
                    <button
                        onClick={handleIngest}
                        disabled={isIngesting}
                        className="glass-btn glass-btn--primary"
                        style={{ fontSize: 11, padding: '4px 12px' }}
                    >
                        {isIngesting ? 'Ingesting...' : 'Ingest'}
                    </button>
                </div>
            </div>

            {/* Memory List */}
            <div style={{ flex: 1, overflowY: 'auto' }} className="scrollbar-hide">
                {memories.length === 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 64, opacity: 0.3 }}>
                        <Database size={48} strokeWidth={1} style={{ marginBottom: 16 }} />
                        <p>Long-term memory is currently empty.</p>
                    </div>
                ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                        {memories.map((m) => (
                            <div key={m.id} className="glass-card" style={{ padding: 16 }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                                    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                                        <FileText size={14} className="text-accent" />
                                        <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
                                            {m.id}
                                        </span>
                                    </div>
                                    <button onClick={() => handleDelete(m.id)} className="hover:text-accent-danger transition-colors opacity-50 hover:opacity-100">
                                        <Trash2 size={14} />
                                    </button>
                                </div>
                                <p style={{ fontSize: 13, lineHeight: 1.6, color: 'var(--text-primary)' }}>
                                    {m.content}
                                </p>
                                {m.metadata && (
                                    <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--separator)', display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                                        {Object.entries(m.metadata).map(([k, v]: [string, any]) => (
                                            <div key={k} style={{ display: 'flex', gap: 4, alignItems: 'center', fontSize: 10, color: 'var(--text-tertiary)' }}>
                                                <Info size={10} />
                                                <span style={{ fontWeight: 600 }}>{k}:</span>
                                                <span>{String(v)}</span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};
