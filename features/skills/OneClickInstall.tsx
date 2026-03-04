import React, { useState } from 'react';
import { useStore } from '../../store/useStore';
import { DownloadCloud, Loader2 } from 'lucide-react';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

export const OneClickInstall: React.FC = () => {
    const { accessToken } = useStore();
    const [url, setUrl] = useState('');
    const [installing, setInstalling] = useState(false);
    const [result, setResult] = useState<{ status: 'ok' | 'error', msg: string } | null>(null);

    const handleInstall = async () => {
        if (!url.trim()) return;
        setInstalling(true);
        setResult(null);
        try {
            const res = await fetch(`${DAEMON_URL}/api/skills/install`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ url }),
                credentials: 'include'
            });
            const data = await res.json();
            if (res.ok) {
                setResult({ status: 'ok', msg: data.message || 'Remote sequence acquired' });
                setUrl('');
            } else {
                setResult({ status: 'error', msg: data.detail || 'Install failed' });
            }
        } catch (err: any) {
            setResult({ status: 'error', msg: err.message || 'Network exception' });
        } finally {
            setInstalling(false);
        }
    };

    return (
        <div className="flex flex-col gap-2 bg-glass-pressed border border-glass-edge rounded-xl p-3">
            <span className="text-[10px] glass-label uppercase tracking-widest text-text-tertiary">Remote Module Provisioning</span>
            <div className="flex items-center gap-2">
                <input
                    type="text"
                    placeholder="https://github.com/..."
                    value={url}
                    onChange={e => setUrl(e.target.value)}
                    className="glass-input text-xs flex-1 font-mono"
                    onKeyDown={e => e.key === 'Enter' && handleInstall()}
                />
                <button
                    onClick={handleInstall}
                    disabled={installing || !url.trim()}
                    className="glass-btn flex items-center justify-center gap-2 flex-shrink-0"
                    style={{ padding: '6px 12px' }}
                >
                    {installing ? <Loader2 size={14} className="animate-spin" /> : <DownloadCloud size={14} />}
                    {installing ? 'Binding...' : 'Install'}
                </button>
            </div>
            {result && (
                <span className={`text-[10px] font-mono ${result.status === 'ok' ? 'text-status-good' : 'text-status-error'}`}>
                    {result.status === 'ok' ? 'SUCCESS: ' : 'ERROR: '} {result.msg}
                </span>
            )}
        </div>
    );
};

export default OneClickInstall;
