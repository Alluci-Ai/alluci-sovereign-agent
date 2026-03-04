import React from 'react';
import { Connection } from '../types';

interface BridgeCenterProps {
    groupedConnections: Record<string, Connection[]>;
    startAuthFlow: (conn: Connection) => void;
    onSocialAction: (id: string, action: string, params: any) => void;
    onEnterpriseAction: (id: string, action: string, params: any) => void;
    onPulse: (id: string) => void;
}

export const BridgeCard: React.FC<{
    conn: Connection;
    startAuthFlow: (conn: Connection) => void;
    onSocialAction: (id: string, action: string, params: any) => void;
    onEnterpriseAction: (id: string, action: string, params: any) => void;
    onPulse: (id: string) => void;
}> = ({ conn, startAuthFlow, onSocialAction, onEnterpriseAction, onPulse }) => {
    const isConnected = conn.status === 'CONNECTED';

    return (
        <div style={{
            background: 'var(--glass-bg)',
            border: `1px solid ${isConnected ? 'rgba(48,209,88,0.20)' : 'var(--separator)'}`,
            borderRadius: 14,
            padding: 16,
            transition: 'all 0.2s ease',
            display: 'flex', flexDirection: 'column', gap: 10,
            backdropFilter: 'blur(16px)',
            position: 'relative',
            overflow: 'hidden',
        }}>
            {/* Subtle top highlight for connected */}
            {isConnected && (
                <div style={{
                    position: 'absolute', top: 0, left: 0, right: 0, height: 2,
                    background: 'linear-gradient(90deg, rgba(48, 209, 88, 0.3), rgba(48, 209, 88, 0.15))', borderRadius: '14px 14px 0 0',
                }} />
            )}

            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                    <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>{conn.name}</p>
                    <p style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>{conn.type}</p>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 3 }}>
                    <span className={`glass-tag ${isConnected ? 'glass-tag--connected' : 'glass-tag--offline'}`} style={{ fontSize: 10 }}>
                        {conn.authType}
                    </span>
                    {conn.isEncrypted && (
                        <span style={{ fontSize: 9, fontWeight: 500, color: 'rgba(48, 209, 88, 0.65)' }}>E2EE</span>
                    )}
                </div>
            </div>

            {/* Connected user info */}
            {isConnected ? (
                <div style={{
                    display: 'flex', alignItems: 'center', gap: 10,
                    padding: '8px 10px', borderRadius: 10,
                    background: 'var(--fill-quaternary)',
                    border: '1px solid var(--separator)',
                }}>
                    <div style={{ position: 'relative', flexShrink: 0 }}>
                        <img
                            src={conn.profileImg || `https://api.dicebear.com/7.x/identicon/svg?seed=${conn.id}`}
                            style={{ width: 28, height: 28, borderRadius: '50%', border: '1px solid var(--separator)', objectFit: 'cover' }}
                            alt=""
                        />
                        <div style={{
                            position: 'absolute', bottom: -1, right: -1,
                            width: 8, height: 8, borderRadius: '50%',
                            background: 'rgba(48, 209, 88, 0.65)', border: '2px solid var(--bg-elevated)',
                            boxShadow: '0 0 4px rgba(48, 209, 88, 0.2)',
                        }} />
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                        <p style={{ fontSize: 12, fontWeight: 600, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {conn.accountAlias}
                        </p>
                        <p style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-quaternary)' }}>
                            ID: {conn.id.substring(0, 8)}
                        </p>
                    </div>

                    {/* Contextual actions — compact */}
                    {conn.id === 'imessage' && (
                        <button onClick={() => onPulse(conn.id)} className="glass-btn" style={{ fontSize: 10, padding: '3px 8px', flexShrink: 0 }}>
                            Pulse
                        </button>
                    )}
                    {['tg', 'sg', 'wa', 'dc', 'x', 'fb', 'ig'].includes(conn.id) && (
                        <button onClick={() => onSocialAction(conn.id, 'SYNC_FEED', {})} className="glass-btn" style={{ fontSize: 10, padding: '3px 8px', flexShrink: 0 }}>
                            Sync
                        </button>
                    )}
                    {['sl', 'mt', 'gm', 'gd', 'wechat', 'webchat'].includes(conn.id) && (
                        <button onClick={() => onEnterpriseAction(conn.id, 'SEARCH_FILES', {})} className="glass-btn" style={{ fontSize: 10, padding: '3px 8px', flexShrink: 0 }}>
                            Search
                        </button>
                    )}
                </div>
            ) : (
                <div style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    padding: '8px', borderRadius: 8,
                    border: '1px dashed var(--separator)',
                    background: 'var(--fill-quaternary)',
                }}>
                    <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-quaternary)' }}>Offline</span>
                </div>
            )}

            {/* Action button — compact */}
            <button
                onClick={() => startAuthFlow(conn)}
                className={`glass-btn ${isConnected ? 'glass-btn--danger' : 'glass-btn--primary'}`}
                style={{ width: '100%', padding: '7px', fontSize: 12, fontWeight: 500, textAlign: 'center' }}
            >
                {isConnected ? 'Disconnect' : 'Connect'}
            </button>
        </div>
    );
};

const BridgeCenter: React.FC<BridgeCenterProps> = ({
    groupedConnections,
    startAuthFlow,
    onSocialAction,
    onEnterpriseAction,
    onPulse
}) => {
    const formatGroupName = (name: string) => name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

    return (
        <div style={{ maxWidth: 960, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 32, paddingBottom: 40 }}>
            {(Object.entries(groupedConnections) as [string, Connection[]][]).map(([groupName, groupConns]) => (
                <div key={groupName}>
                    <h3 style={{
                        fontSize: 13, fontWeight: 600, color: 'var(--text-tertiary)',
                        textTransform: 'uppercase', letterSpacing: '0.04em',
                        paddingBottom: 8, marginBottom: 14,
                        borderBottom: '1px solid var(--separator)',
                    }}>
                        {formatGroupName(groupName)}
                    </h3>
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
                        gap: 12,
                    }}>
                        {groupConns.map(conn => (
                            <BridgeCard
                                key={conn.id}
                                conn={conn}
                                startAuthFlow={startAuthFlow}
                                onSocialAction={onSocialAction}
                                onEnterpriseAction={onEnterpriseAction}
                                onPulse={onPulse}
                            />
                        ))}
                    </div>
                </div>
            ))}
        </div>
    );
};

export default BridgeCenter;
