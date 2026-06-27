import React, { useState } from 'react';
import { Connection } from '../types';
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { Settings, ChevronDown, ChevronUp } from 'lucide-react';
import ChannelHealthDashboard from '../features/channels/ChannelHealthDashboard';
import ChannelConfigExpansion from '../features/channels/ChannelConfigExpansion';
import ChannelActionResult from '../features/channels/ChannelActionResult';
import IMessagePlatformGuard from '../features/channels/iMessagePlatformGuard';

interface BridgeCenterProps {
    connections: Connection[];
    startAuthFlow: (conn: Connection) => void;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onSocialAction: (id: string, action: string, params: any) => Promise<any> | void;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onEnterpriseAction: (id: string, action: string, params: any) => Promise<any> | void;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onPulse: (id: string) => Promise<any> | void;
}

export const BridgeCard: React.FC<{
    conn: Connection;
    startAuthFlow: (conn: Connection) => void;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onSocialAction: (id: string, action: string, params: any) => Promise<any> | void;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onEnterpriseAction: (id: string, action: string, params: any) => Promise<any> | void;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onPulse: (id: string) => Promise<any> | void;
}> = ({ conn, startAuthFlow, onSocialAction, onEnterpriseAction, onPulse }) => {
    const isConnected = conn.status === 'CONNECTED';
    const [configOpen, setConfigOpen] = useState(false);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [actionResult, setActionResult] = useState<any>(null);

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const handleActionWrapper = async (actionFn: () => Promise<any> | void) => {
        setActionResult({ status: 'pending', message: 'Executing...' });
        try {
            const res = await actionFn();
            setActionResult(res || { status: 'ok', message: 'Dispatched successfully' });
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        } catch (err: any) {
            setActionResult({ status: 'error', message: err.message || 'Action failed' });
        }
    };

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

            {conn.id === 'imessage' && <IMessagePlatformGuard />}

            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <div>
                        <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>{conn.name}</p>
                        <p style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>{conn.type}</p>
                    </div>
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
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {(conn.accounts && conn.accounts.length > 0 ? conn.accounts : [{ id: 'default', alias: conn.accountAlias, avatar_url: conn.profileImg }]).map((acc: any, i: number) => (
                        <div key={acc.id || i} style={{
                            display: 'flex', alignItems: 'center', gap: 10,
                            padding: '8px 10px', borderRadius: 10,
                            background: 'var(--fill-quaternary)',
                            border: '1px solid var(--separator)',
                        }}>
                            <div style={{ position: 'relative', flexShrink: 0 }}>
                                <img
                                    src={acc.avatar_url || conn.profileImg || `https://api.dicebear.com/7.x/identicon/svg?seed=${conn.id}`}
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
                                    {acc.alias || conn.accountAlias}
                                </p>
                                <p style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-quaternary)' }}>
                                    ID: {conn.id.substring(0, 8)}
                                </p>
                            </div>

                            {/* Contextual actions — compact */}
                            {conn.id === 'imessage' && (
                                <button onClick={() => handleActionWrapper(() => onPulse(conn.id))} className="glass-btn" style={{ fontSize: 10, padding: '3px 8px', flexShrink: 0 }}>
                                    Pulse
                                </button>
                            )}
                            {['tg', 'sg', 'wa', 'dc', 'x', 'fb', 'ig'].includes(conn.id) && (
                                <button onClick={() => handleActionWrapper(() => onSocialAction(conn.id, 'SYNC_FEED', {}))} className="glass-btn" style={{ fontSize: 10, padding: '3px 8px', flexShrink: 0 }}>
                                    Sync
                                </button>
                            )}
                            {['sl', 'mt', 'gm', 'gd', 'wechat', 'webchat'].includes(conn.id) && (
                                <button onClick={() => handleActionWrapper(() => onEnterpriseAction(conn.id, 'SEARCH_FILES', {}))} className="glass-btn" style={{ fontSize: 10, padding: '3px 8px', flexShrink: 0 }}>
                                    Search
                                </button>
                            )}
                        </div>
                    ))}
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

            {actionResult && (
                <ChannelActionResult
                    result={actionResult}
                    onDismiss={() => setActionResult(null)}
                />
            )}

            {/* Action button — compact */}
            <div style={{ display: 'flex', gap: 8, width: '100%', marginTop: 'auto' }}>
                <button
                    onClick={() => startAuthFlow(conn)}
                    className={`glass-btn ${isConnected ? 'glass-btn--danger' : 'glass-btn--primary'}`}
                    style={{ flex: 1, padding: '7px', fontSize: 12, fontWeight: 500, textAlign: 'center' }}
                >
                    {isConnected ? 'Disconnect' : 'Connect'}
                </button>
                <button
                    onClick={() => setConfigOpen(!configOpen)}
                    className="glass-btn px-2 text-text-tertiary hover:text-accent flex items-center justify-center transition-colors border border-glass-edge bg-glass-1"
                >
                    <Settings size={14} />
                </button>
            </div>

            <ChannelConfigExpansion
                channelId={conn.id}
                isOpen={configOpen}
                onClose={() => setConfigOpen(false)}
                conn={conn}
                startAuthFlow={startAuthFlow}
            />
        </div>
    );
};

const BridgeCenter: React.FC<BridgeCenterProps> = ({
    connections = [],
    startAuthFlow,
    onSocialAction,
    onEnterpriseAction,
    onPulse
}) => {
    const formatGroupName = (name: string) => name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

    const sortConnections = (conns: Connection[]) => {
        return [...(conns || [])].sort((a, b) => {
            if (a.status === 'CONNECTED' && b.status !== 'CONNECTED') return -1;
            if (a.status !== 'CONNECTED' && b.status === 'CONNECTED') return 1;
            return (a.name || '').localeCompare(b.name || '');
        });
    };

    const appleIds = ['icloud', 'email', 'imessage', 'iwatch', 'iphone'];
    const socialIds = ['wa', 'tg', 'dc', 'sg', 'ig', 'fb', 'x'];
    const enterpriseIds = ['sl', 'mt', 'gm', 'gd', 'notion', 'github', 'webchat', 'wechat'];
    const verusIds = ['verus'];

    const grouped = {
        'APPLE_ECOSYSTEM': connections.filter(c => c && appleIds.includes(c.id)),
        'SOCIAL_MANIFOLD': connections.filter(c => c && socialIds.includes(c.id)),
        'ENTERPRISE_CORE': connections.filter(c => c && enterpriseIds.includes(c.id)),
        'VERUS_IDENTITY': connections.filter(c => c && verusIds.includes(c.id)),
        'OTHER_BRIDGES': connections.filter(c => c && ![...appleIds, ...socialIds, ...enterpriseIds, ...verusIds].includes(c.id))
    };

    return (
        <div style={{ maxWidth: 960, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 32, paddingBottom: 40 }}>
            <ChannelHealthDashboard />

            {Object.entries(grouped).map(([groupName, groupConns]) => {
                if (groupConns.length === 0) return null;

                return (
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
                            {sortConnections(groupConns).map(conn => (
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
                );
            })}

            {connections.length === 0 && (
                <div style={{ textAlign: 'center', padding: '100px 20px', opacity: 0.5 }}>
                    <p className="glass-label">NO_CONNECTION_HANDSHAKES_INITIALIZED</p>
                    <p style={{ fontSize: 10, marginTop: 10 }}>Check integrity of components/constants.tsx</p>
                </div>
            )}
        </div>
    );
};

export default BridgeCenter;
