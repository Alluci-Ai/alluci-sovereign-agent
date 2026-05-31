import React, { useState, useEffect } from 'react';
import { useStore } from '../../store/useStore';
import { FileCode, Save, FilePlus, RefreshCcw } from 'lucide-react';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://127.0.0.1:8000';

interface WorkspaceEditorProps {
    agentId: string;
}

export const WorkspaceEditor: React.FC<WorkspaceEditorProps> = ({ agentId }) => {
    const { accessToken } = useStore();
    const [files, setFiles] = useState<string[]>([]);
    const [selectedFile, setSelectedFile] = useState<string>('');
    const [content, setContent] = useState<string>('');
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);

    const loadFiles = async () => {
        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/agents/${agentId}/files`, {
                headers: { 'Authorization': `Bearer ${accessToken}` },
                credentials: 'include'
            });
            if (res.ok) {
                const data = await res.json();
                setFiles(data.files || []);
                if (!selectedFile && data.files?.length > 0) {
                    setSelectedFile(data.files[0]);
                }
            }
        } catch (err) {
            console.error('Failed fetching agent workspace', err);
        }
    };

    const loadContent = async (filename: string) => {
        setLoading(true);
        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/agents/${agentId}/files/${encodeURIComponent(filename)}`, {
                headers: { 'Authorization': `Bearer ${accessToken}` },
                credentials: 'include'
            });
            if (res.ok) {
                const data = await res.json();
                setContent(data.content || '');
            }
        } catch (err) {
            console.error('Failed fetching file content', err);
        } finally {
            setLoading(false);
        }
    };

    const saveContent = async () => {
        setSaving(true);
        try {
            await fetch(`${DAEMON_URL}/api/v1/agents/${agentId}/files/${encodeURIComponent(selectedFile)}`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${accessToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ content }),
                credentials: 'include'
            });
        } catch (err) {
            console.error('Failed saving file content', err);
        } finally {
            setSaving(false);
        }
    };

    useEffect(() => {
        loadFiles();
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [agentId, accessToken]);

    useEffect(() => {
        if (selectedFile) loadContent(selectedFile);
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedFile]);

    return (
        <div className="w-full h-full min-h-[500px] flex border border-glass-edge bg-glass-1 rounded-xl overflow-hidden animate-in fade-in duration-300">
            {/* Sidebar File Tree */}
            <div className="w-56 border-r border-glass-edge bg-glass-pressed flex flex-col">
                <div className="p-3 border-b border-glass-edge flex items-center justify-between text-text-tertiary">
                    <span className="text-[10px] glass-label uppercase tracking-widest">Virtual VFS</span>
                    <button className="hover:text-accent transition-colors"><FilePlus size={12} /></button>
                </div>
                <div className="flex-1 overflow-y-auto p-2">
                    {files.map(f => (
                        <button
                            key={f}
                            onClick={() => setSelectedFile(f)}
                            className={`w-full text-left flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-mono transition-colors ${selectedFile === f ? 'bg-glass-1 text-accent border border-white/5' : 'text-text-secondary hover:bg-white/5'}`}
                        >
                            <FileCode size={12} className={selectedFile === f ? 'opacity-100' : 'opacity-40'} /> {f}
                        </button>
                    ))}
                </div>
            </div>

            {/* Editor Pane */}
            <div className="flex-1 flex flex-col bg-black/40">
                <div className="h-10 border-b border-glass-edge flex items-center justify-between px-4 bg-glass-1">
                    <span className="text-xs font-mono tracking-widest opacity-60 flex items-center gap-2">
                        {selectedFile || 'NONE_SELECTED'}
                        {loading && <RefreshCcw size={10} className="animate-spin text-accent" />}
                    </span>
                    <button
                        onClick={saveContent}
                        disabled={saving || !selectedFile}
                        className="glass-btn gap-2" style={{ padding: '3px 10px', fontSize: 10 }}
                    >
                        <Save size={12} /> {saving ? 'Committing' : 'Save to Volume'}
                    </button>
                </div>

                <textarea
                    value={content}
                    onChange={e => setContent(e.target.value)}
                    className="flex-1 w-full p-4 bg-transparent border-none outline-none text-[12px] font-mono leading-relaxed text-blue-200 resize-none selection:bg-accent/40"
                    spellCheck="false"
                    placeholder="// Agent specific context loops..."
                />
            </div>
        </div>
    );
};

export default WorkspaceEditor;
