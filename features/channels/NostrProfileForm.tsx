import React, { useState } from 'react';
import { useStore } from '../../store/useStore';
import { Save, UserCircle, Globe, AtSign, Zap } from 'lucide-react';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';

interface NostrProfileFormProps {
    channelId: string;
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export const NostrProfileForm: React.FC<NostrProfileFormProps> = ({ channelId }) => {
    const { accessToken } = useStore();
    const [profile, setProfile] = useState({
        displayName: '',
        about: '',
        pictureUrl: '',
        nip05: '',
        lud16: ''
    });
    const [saving, setSaving] = useState(false);

    const handleSave = async () => {
        setSaving(true);
        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/channels/nostr/profile`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${accessToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(profile),
                credentials: 'include'
            });
            if (res.ok) alert('Nostr Relay Protocol Updated.');
        } catch (err) {
            console.error('Failed updating relay identity logic loops', err);
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="flex flex-col gap-3 mt-2 bg-glass-2 border border-glass-edge rounded-lg p-3">
            <h5 className="glass-label text-[10px] opacity-70 mb-1 flex items-center gap-1">
                <Globe size={12} /> Decentralized Profile Record (Metadata 0)
            </h5>

            <div className="flex flex-col gap-2 relative z-10">
                <div className="flex items-center gap-2 border border-glass-edge rounded-md p-1.5 focus-within:border-accent/40 bg-glass-1">
                    <UserCircle size={14} className="text-text-tertiary ml-1" />
                    <input
                        type="text"
                        placeholder="Display Name"
                        value={profile.displayName}
                        onChange={e => setProfile(p => ({ ...p, displayName: e.target.value }))}
                        className="bg-transparent text-[11px] text-text-primary w-full outline-none"
                    />
                </div>

                <textarea
                    placeholder="About..."
                    value={profile.about}
                    onChange={e => setProfile(p => ({ ...p, about: e.target.value }))}
                    className="bg-glass-1 text-[11px] text-text-primary w-full outline-none border border-glass-edge rounded-md p-2 h-16 resize-none focus:border-accent/40"
                    spellCheck="false"
                />

                <div className="flex items-center gap-2 border border-glass-edge rounded-md p-1.5 focus-within:border-accent/40 bg-glass-1">
                    <AtSign size={14} className="text-text-tertiary ml-1" />
                    <input
                        type="text"
                        placeholder="NIP-05 DNS Alias (bob@example.com)"
                        value={profile.nip05}
                        onChange={e => setProfile(p => ({ ...p, nip05: e.target.value }))}
                        className="bg-transparent text-[11px] text-text-primary w-full outline-none font-mono tracking-tight"
                    />
                </div>

                <div className="flex items-center gap-2 border border-glass-edge rounded-md p-1.5 focus-within:border-accent/40 bg-glass-1">
                    <Zap size={14} className="text-amber-500 opacity-60 ml-1" />
                    <input
                        type="text"
                        placeholder="LUD-16 Lightning Address"
                        value={profile.lud16}
                        onChange={e => setProfile(p => ({ ...p, lud16: e.target.value }))}
                        className="bg-transparent text-[11px] text-text-primary w-full outline-none font-mono tracking-tight"
                    />
                </div>

            </div>

            <div className="flex justify-end mt-1">
                <button
                    onClick={handleSave}
                    disabled={saving}
                    className="glass-btn gap-1"
                    style={{ fontSize: 10, padding: '4px 10px' }}
                >
                    <Save size={12} /> {saving ? 'Pushing 0...' : 'Broadcast'}
                </button>
            </div>
        </div>
    );
};

export default NostrProfileForm;
