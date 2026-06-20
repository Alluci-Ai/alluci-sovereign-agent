import React, { useEffect, useState } from 'react';
import { useStore } from '../../store/useStore';
import { Settings, Save, Code, LayoutList, Eye, EyeOff } from 'lucide-react';
import GatewayUrlCard from '../shell/GatewayUrlCard';
import LocaleSelector from '../shell/LocaleSelector';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';

interface SchemaDef {
    title?: string;
    description?: string;
    type?: string;
    readOnly?: boolean;
}

export const ConfigPanel: React.FC = () => {
    const { accessToken } = useStore();
    const [mode, setMode] = useState<'form' | 'raw'>('form');

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [schema, setSchema] = useState<any>(null);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [config, setConfig] = useState<Record<string, any>>({});
    const [rawJson, setRawJson] = useState<string>('');
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    // Mask toggles for sensitive fields
    const [revealed, setRevealed] = useState<Record<string, boolean>>({});

    useEffect(() => {
        const fetchConfig = async () => {
            setLoading(true);
            try {
                const [cfgRes, schemaRes] = await Promise.all([
                    fetch(`${DAEMON_URL}/api/v1/config`, {
                        headers: { 'Authorization': `Bearer ${accessToken}` },
                        credentials: 'include'
                    }),
                    fetch(`${DAEMON_URL}/api/v1/config/schema`, {
                        headers: { 'Authorization': `Bearer ${accessToken}` },
                        credentials: 'include'
                    })
                ]);

                if (cfgRes.ok && schemaRes.ok) {
                    const cfgData = await cfgRes.json();
                    const struct = await schemaRes.json();
                    setSchema(struct);
                    setConfig(cfgData);
                    setRawJson(JSON.stringify(cfgData, null, 2));
                }
            } catch (err) {
                console.error('[ConfigPanel] Failed fetching daemon configuration:', err);
            } finally {
                setLoading(false);
            }
        };
        fetchConfig();
    }, [accessToken]);

    const handleSave = async () => {
        setSaving(true);
        try {
            const payload = mode === 'raw' ? JSON.parse(rawJson) : config;

            const res = await fetch(`${DAEMON_URL}/api/v1/config`, { // Maps to PUT /api/v1/config update endpoint
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${accessToken}`,
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                const result = await res.json();
                if (result.applied && result.applied.length > 0) {
                    alert(`Successfully applied config overrides: \n${result.applied.join(', ')}`);
                }
            } else {
                const err = await res.json();
                alert(`Error saving config: ${err.detail || 'Unknown error'}`);
            }
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        } catch (err: any) {
            alert(`JSON Parse or API error: ${err.message}`);
        } finally {
            setSaving(false);
        }
    };

    const toggleReveal = (key: string) => {
        setRevealed(prev => ({ ...prev, [key]: !prev[key] }));
    };

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const handleFieldChange = (key: string, value: any) => {
        setConfig(prev => {
            const upd = { ...prev, [key]: value };
            setRawJson(JSON.stringify(upd, null, 2));
            return upd;
        });
    };

    // Grouping schema properties by logical sections prefix if applicable
    const renderFormMode = () => {
        if (!schema || !schema.properties) return <div className="p-4 opacity-50">Schema not loaded.</div>;

        const props = Object.entries(schema.properties);

        return (
            <div className="flex flex-col gap-5 p-4 animate-in fade-in zoom-in-95 duration-300">
                {props.map(([key, def]: [string, SchemaDef]) => {
                    const val = config[key];
                    const isSensitive = key.toLowerCase().includes('key') || key.toLowerCase().includes('secret') || key.toLowerCase().includes('token');
                    const isMasked = isSensitive && typeof val === 'string' && val.includes('****') && !revealed[key];
                    const readOnly = def.readOnly === true;

                    return (
                        <div key={key} className="flex flex-col gap-1.5 border-b border-glass-edge pb-4">
                            <label className="text-xs glass-label tracking-wide flex justify-between">
                                <span className={readOnly ? 'opacity-50' : 'text-text-primary'}>{def.title || key}</span>
                                {def.type && <span className="opacity-40 text-[9px] font-mono">{def.type}</span>}
                            </label>

                            {def.description && <p className="text-[10px] text-text-tertiary opacity-70 mb-1 leading-snug">{def.description}</p>}

                            {def.type === 'boolean' ? (
                                <select
                                    className="glass-input text-xs w-40"
                                    value={val ? 'true' : 'false'}
                                    disabled={readOnly}
                                    onChange={e => handleFieldChange(key, e.target.value === 'true')}
                                >
                                    <option value="true">True</option>
                                    <option value="false">False</option>
                                </select>
                            ) : def.type === 'integer' || def.type === 'number' ? (
                                <input
                                    type="number"
                                    className="glass-input text-xs w-full max-w-sm font-mono"
                                    disabled={readOnly}
                                    value={val ?? ''}
                                    onChange={e => handleFieldChange(key, def.type === 'integer' ? parseInt(e.target.value) : parseFloat(e.target.value))}
                                />
                            ) : (
                                <div className="relative w-full max-w-lg">
                                    <input
                                        type={isMasked ? 'password' : 'text'}
                                        disabled={readOnly}
                                        className={`glass-input text-xs w-full font-mono pr-10 ${readOnly ? 'opacity-40 cursor-not-allowed' : ''}`}
                                        value={val ?? ''}
                                        onChange={e => handleFieldChange(key, e.target.value)}
                                        placeholder={`Enter ${key}...`}
                                    />
                                    {isSensitive && (
                                        <button
                                            onClick={() => toggleReveal(key)}
                                            className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-text-tertiary hover:text-accent transition-colors"
                                        >
                                            {revealed[key] ? <EyeOff size={14} /> : <Eye size={14} />}
                                        </button>
                                    )}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        );
    };

    return (
        <div className="inline-panel-wrapper overflow-auto">
            <div className="max-w-4xl mx-auto w-full flex flex-col gap-6 lg:p-6 p-4">

                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                        <Settings size={20} className="text-accent" />
                        <h2 className="text-xl font-medium tracking-tight text-text-primary">Daemon Configuration</h2>
                    </div>

                    <div className="flex items-center gap-2 bg-glass-1 p-1 rounded-xl border border-glass-edge">
                        <button
                            onClick={() => setMode('form')}
                            className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs transition-all ${mode === 'form' ? 'bg-glass-pressed text-accent shadow-sm' : 'text-text-tertiary hover:text-text-primary'}`}
                        >
                            <LayoutList size={14} /> Schema Form
                        </button>
                        <button
                            onClick={() => setMode('raw')}
                            className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs transition-all ${mode === 'raw' ? 'bg-glass-pressed text-accent shadow-sm' : 'text-text-tertiary hover:text-text-primary'}`}
                        >
                            <Code size={14} /> Raw JSON
                        </button>
                    </div>
                </div>

                <div className="bg-glass-1 border border-glass-edge rounded-xl overflow-hidden relative min-h-[500px] flex flex-col">
                    {loading ? (
                        <div className="absolute inset-0 flex items-center justify-center font-mono text-xs opacity-50 animate-pulse tracking-widest">
                            READING_ENV_SCHEMA...
                        </div>
                    ) : (
                        <div className="flex-1 overflow-auto flex flex-col p-4 gap-6">

                            {mode === 'form' && (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-in fade-in duration-300">
                                    <GatewayUrlCard />
                                    <LocaleSelector />
                                </div>
                            )}

                            {mode === 'form' ? renderFormMode() : (
                                <textarea
                                    className="w-full h-full min-h-[500px] bg-transparent text-text-primary p-4 text-xs font-mono focus:outline-none resize-none"
                                    value={rawJson}
                                    onChange={e => setRawJson(e.target.value)}
                                    spellCheck={false}
                                />
                            )}
                        </div>
                    )}

                    <div className="p-4 border-t border-glass-edge bg-glass-2 flex justify-between items-center">
                        <span className="text-[10px] glass-label text-text-tertiary font-mono">
                            {mode === 'form' ? 'Strict Schema Validation Active' : 'Unsafe Direct Memory Editor'}
                        </span>

                        <button
                            onClick={handleSave}
                            disabled={saving || loading}
                            className="glass-btn flex items-center gap-2"
                        >
                            {saving ? <span className="animate-pulse">Writing Overrides...</span> : <><Save size={14} /> Apply Changes</>}
                        </button>
                    </div>
                </div>

            </div>
        </div>
    );
};

export default ConfigPanel;
