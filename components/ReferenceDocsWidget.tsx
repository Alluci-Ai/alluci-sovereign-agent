import React, { useState, useEffect } from 'react';
import { adminService } from '../adminService';

/**
 * ReferenceDocsWidget — a production-ready file reference manager
 * that displays live ingestion status via the existing admin WebSocket gateway.
 *
 * Listens for `doc.ingest.status` JSON-RPC notifications pushed by
 * tool_manager._quarantine_and_ingest / skill_manager._quarantine_and_ingest.
 *
 * The backend broadcasts:
 *   { jsonrpc: "2.0", method: "doc.ingest.status", params: { source_path, status, component_id } }
 *
 * The adminService dispatches these via its listener system as (method, params).
 */
export const ReferenceDocsWidget: React.FC<{
    label: string;
    items: string[];
    onChange: (newItems: string[]) => void;
    placeholder: string;
}> = ({ label, items, onChange, placeholder }) => {
    const [val, setVal] = useState('');
    const [statuses, setStatuses] = useState<Record<string, string>>({});

    useEffect(() => {
        // Subscribe to doc.ingest.status events via the shared admin WebSocket
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const handleEvent = (method: string, params: any) => {
            if (method === 'doc.ingest.status' && params?.source_path) {
                setStatuses(prev => ({ ...prev, [params.source_path]: params.status }));
            }
        };

        adminService.addListener(handleEvent);

        return () => {
            adminService.removeListener(handleEvent);
        };
    }, []);

    const add = () => {
        if (!val.trim()) return;
        if (!items.includes(val.trim())) {
            onChange([...items, val.trim()]);
            setStatuses(prev => ({ ...prev, [val.trim()]: 'Pending...' }));
        }
        setVal('');
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}>
            <label style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.02em' }}>{label}</label>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {items.map((it, i) => (
                    <div key={i} style={{
                        display: 'flex', flexDirection: 'column',
                        background: 'var(--fill-quaternary)',
                        border: '1px solid var(--separator)',
                        borderRadius: 6,
                        padding: '6px 10px',
                        minWidth: 200
                    }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', wordBreak: 'break-all', paddingRight: 8 }}>
                                {it}
                            </span>
                            <button onClick={() => onChange(items.filter((_, idx) => idx !== i))}
                                style={{ background: 'none', border: 'none', color: 'var(--accent-danger)', cursor: 'pointer', fontSize: 16, lineHeight: 1, padding: 0 }}>
                                ×
                            </button>
                        </div>
                        <div style={{
                            fontSize: 10,
                            marginTop: 4,
                            color: statuses[it]?.includes('Error') || statuses[it]?.includes('Rupture')
                                ? 'var(--accent-danger)'
                                : statuses[it]?.includes('Embedded')
                                    ? 'var(--accent-success, #34d399)'
                                    : 'var(--accent)',
                        }}>
                            ● {statuses[it] || 'Ready for ingestion'}
                        </div>
                    </div>
                ))}
            </div>

            <div style={{ display: 'flex', gap: 6 }}>
                <input
                    className="glass-input"
                    value={val}
                    onChange={e => setVal(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && add()}
                    placeholder={placeholder}
                    style={{ flex: 1, padding: '8px 12px', fontSize: 13 }}
                />
                <button onClick={add} className="glass-btn" style={{ padding: '8px 16px', flexShrink: 0 }}>+</button>
            </div>
            <p style={{ fontSize: 10, color: 'var(--text-tertiary)', margin: 0 }}>Enter a local path (e.g. /Users/name/doc.md) or a URL (e.g. https://example.com/doc.md)</p>
        </div>
    );
};
