import React, { useEffect, useState } from 'react';
import { useStore } from '../../store/useStore';
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { Settings, CheckCircle2, Clock, XCircle, FileCode2 } from 'lucide-react';
import WebhookUrlDisplay from './WebhookUrlDisplay';
import ChannelToggle from './ChannelToggle';
import NostrProfileForm from './NostrProfileForm';
import PerAccountList from './PerAccountList';
import WhatsAppQRPairer from './WhatsAppQRPairer';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://127.0.0.1:8000';

interface ConfigExpansionProps {
    channelId: string;
    isOpen: boolean;
    onClose: () => void;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    conn?: any;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    startAuthFlow?: (conn: any) => void;
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export const ChannelConfigExpansion: React.FC<ConfigExpansionProps> = ({ channelId, isOpen, onClose, conn, startAuthFlow }) => {
    const { accessToken } = useStore();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [config, setConfig] = useState<any>({});
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (!isOpen) return;
        const fetchConfig = async () => {
            setLoading(true);
            try {
                const res = await fetch(`${DAEMON_URL}/api/v1/channels/${channelId}/config`, {
                    headers: { 'Authorization': `Bearer ${accessToken}` },
                    credentials: 'include'
                });
                if (res.ok) {
                    setConfig(await res.json());
                }
            } catch (err) {
                console.error('Failed fetching channel config:', err);
            } finally {
                setLoading(false);
            }
        };
        fetchConfig();
    }, [channelId, isOpen, accessToken]);

    const handleSave = async () => {
        setSaving(true);
        try {
            const { getCsrfToken } = await import('../../csrfStore');
            const csrfToken = await getCsrfToken(DAEMON_URL, accessToken);
            await fetch(`${DAEMON_URL}/api/v1/channels/${channelId}/config`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${accessToken}`,
                    'Content-Type': 'application/json',
                    ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
                },
                body: JSON.stringify(config),
                credentials: 'include'
            });
            alert('Config persisted securely to Vault.');
        } catch (err) {
            console.error('Config save failed', err);
        } finally {
            setSaving(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="mt-4 pt-4 border-t border-white/5 flex flex-col gap-4 animate-in slide-in-from-top-2 duration-300 relative z-20">
            <div className="flex justify-between items-center">
                <h4 className="glass-label text-[10px] tracking-widest text-text-tertiary uppercase flex items-center gap-2">
                    <Settings size={12} /> Integration Settings
                </h4>
                <ChannelToggle channelId={channelId} initialEnabled={config?.enabled ?? false} />
            </div>

            {loading ? (
                <div className="text-xs font-mono opacity-50 py-4 animate-pulse">DECRYPTING_VAULT_PAYLOAD...</div>
            ) : (
                <div className="flex flex-col gap-3">

                    {/* Common Token Input */}
                    {['tg'].includes(channelId) && (
                        <div className="flex flex-col gap-1">
                            <label className="text-[10px] text-text-tertiary font-mono">Channel Token / Secret</label>
                            <input
                                type="password"
                                value={config.token || ''}
                                onChange={e => setConfig({ ...config, token: e.target.value })}
                                className="glass-input text-xs w-full font-mono"
                                placeholder="************************"
                            />
                        </div>
                    )}

                    {/* Webhook Read Only */}
                    {['tg', 'wa', 'discord'].includes(channelId) && (
                        <WebhookUrlDisplay channelId={channelId} secret={config.webhook_secret || 'default-secret'} />
                    )}

                    {/* WhatsApp explicit components */}
                    {channelId === 'wa' && <WhatsAppQRPairer />}

                    {/* Nostr profile settings */}
                    {channelId === 'nostr' && <NostrProfileForm channelId={channelId} />}

                    {/* Per-Account Management Lists */}
                    <PerAccountList channelId={channelId} />
                    
                    {['gm', 'sl', 'x', 'fb', 'ig', 'dc', 'gd'].includes(channelId) && startAuthFlow && conn && (
                        <div className="flex justify-start pt-1">
                            <button onClick={() => startAuthFlow(conn)} className="glass-btn px-3 py-1.5 text-[11px] flex items-center gap-2 border-glass-edge">
                                + Add Another Account
                            </button>
                        </div>
                    )}

                    <div className="flex justify-end pt-2">
                        <button onClick={handleSave} disabled={saving} className="glass-btn gap-2" style={{ fontSize: 11, padding: '4px 12px' }}>
                            {saving ? 'Encrypting...' : 'Save Configuration'}
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ChannelConfigExpansion;
