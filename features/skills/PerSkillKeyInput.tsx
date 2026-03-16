import React, { useState, useEffect } from 'react';
import { useStore } from '../../store/useStore';
import { Key, Save, Loader2, Link2Off } from 'lucide-react';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

interface PerSkillKeyInputProps {
    skillId: string;
    keyName: string;
    description?: string;
}

export const PerSkillKeyInput: React.FC<PerSkillKeyInputProps> = ({ skillId, keyName, description }) => {
    const { accessToken } = useStore();
    const [value, setValue] = useState('');
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [status, setStatus] = useState<'IDLE' | 'SAVED' | 'ERROR'>('IDLE');

    useEffect(() => {
        const fetchKey = async () => {
            try {
                // If it exists in vault it might return masked
                const res = await fetch(`${DAEMON_URL}/api/v1/skills/${skillId}/keys/${keyName}`, {
                    headers: { 'Authorization': `Bearer ${accessToken}` },
                    credentials: 'include'
                });
                if (res.ok) {
                    const data = await res.json();
                    setValue(data.value || '');
                }
            } catch (err) {
                console.error(`Failed to fetch mapped key ${keyName}`, err);
            } finally {
                setLoading(false);
            }
        };

        fetchKey();
    }, [skillId, keyName, accessToken]);

    const handleSave = async () => {
        setSaving(true);
        setStatus('IDLE');
        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/skills/${skillId}/keys`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: keyName, value }),
                credentials: 'include'
            });
            if (res.ok) {
                setStatus('SAVED');
                setTimeout(() => setStatus('IDLE'), 3000);
            } else {
                setStatus('ERROR');
            }
        } catch (err) {
            console.error('Save loop failed natively', err);
            setStatus('ERROR');
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return <div className="animate-pulse h-10 bg-glass-pressed rounded-lg border border-white/5" />;
    }

    return (
        <div className="flex flex-col gap-2 p-3 bg-glass-1 border border-glass-edge rounded-lg relative z-10 transition-colors focus-within:border-accent/30 focus-within:shadow-[0_0_10px_rgba(43,158,255,0.05)]">
            <label className="text-[10px] text-text-tertiary font-mono flex items-center justify-between uppercase">
                <span className="flex items-center gap-1"><Key size={10} /> {keyName.replace(/_/g, ' ')}</span>
                {status === 'SAVED' && <span className="text-status-good tracking-wider">SECURE_STORE OK</span>}
                {status === 'ERROR' && <span className="text-status-error tracking-wider"><Link2Off size={10} className="inline" /> VAULT_ERR</span>}
            </label>

            {description && <p className="text-[9px] text-text-quaternary m-0">{description}</p>}

            <div className="flex gap-2 relative h-[32px]">
                <input
                    type="password"
                    value={value}
                    onChange={e => setValue(e.target.value)}
                    placeholder="************************"
                    className="glass-input flex-1 font-mono text-xs w-full bg-black/40 h-full"
                    autoComplete="off"
                />

                <button
                    onClick={handleSave}
                    disabled={saving}
                    className="glass-btn gap-2 flex-shrink-0"
                    style={{ padding: '0 12px', fontSize: 10, height: '100%', minHeight: '32px' }}
                >
                    {saving ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
                </button>
            </div>
        </div>
    );
};

export default PerSkillKeyInput;
