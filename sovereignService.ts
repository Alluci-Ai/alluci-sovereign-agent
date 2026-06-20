import { getCsrfToken } from './csrfStore';

export interface SovereignCallbacks {
    onAudioOutput: (base64Audio: string) => void;
    onTranscription: (text: string, isUser: boolean) => void;
    onLLMChunk: (text: string) => void;
    onOpen: () => void;
    onClose: () => void;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onError: (error: any) => void;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onGroundingSources?: (sources: any[]) => void;
    onInterrupted?: () => void;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onCanvasManifest?: (node: any) => void;
}

export class AlluciSovereignService {
    private socket: WebSocket | null = null;
    private audioContext: AudioContext | null = null;
    private DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';
    private WS_URL = (this.DAEMON_URL.startsWith('https') ? this.DAEMON_URL.replace('https', 'wss') : this.DAEMON_URL.replace('http', 'ws')) + '/ws/sovereign';

    constructor() { }

    async connect(callbacks: SovereignCallbacks, token: string) {
        this.socket = new WebSocket(this.WS_URL);

        this.socket.onopen = () => {
            console.log("[ SOVEREIGN ]: Connected.");
            // Send auth token as the first frame
            this.socket?.send(JSON.stringify({ type: 'auth', token }));
            callbacks.onOpen();
        };

        this.socket.onmessage = async (event) => {
            if (typeof event.data === 'string') {
                const msg = JSON.parse(event.data);
                if (msg.type === 'transcript') {
                    callbacks.onTranscription(msg.text, true);
                } else if (msg.type === 'llm_chunk') {
                    callbacks.onLLMChunk(msg.text);
                } else if (msg.type === 'audio_out') {
                    callbacks.onAudioOutput(msg.data);
                } else if (msg.type === 'manifest' && callbacks.onCanvasManifest) {
                    callbacks.onCanvasManifest(msg.node);
                } else if (msg.type === 'telemetry') {
                    window.dispatchEvent(new CustomEvent('alluci.system.telemetry', { detail: msg.data }));
                }
            }
        };

        this.socket.onerror = (err) => {
            console.error("[ SOVEREIGN ]: Socket error", err);
            callbacks.onError(err);
        };

        this.socket.onclose = () => {
            console.log("[ SOVEREIGN ]: Disconnected.");
            callbacks.onClose();
        };
    }

    sendAudio(audioData: Float32Array) {
        if (this.socket?.readyState === WebSocket.OPEN) {
            // Convert to Int16 for whisper.cpp efficiency
            const pcm = new Int16Array(audioData.length);
            for (let i = 0; i < audioData.length; i++) {
                pcm[i] = Math.max(-1, Math.min(1, audioData[i])) * 32767;
            }
            this.socket.send(pcm.buffer);
        }
    }

    sendChat(text: string) {
        if (this.socket?.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({ type: 'chat', text }));
        }
    }

    disconnect() {
        this.socket?.close();
        this.socket = null;
    }

    // ─── H-LSM Memory REST API ──────────────────────────────────────────────

    private async _fetch(path: string, options: RequestInit = {}) {
        const token = localStorage.getItem('alluci_access_token');
        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
            ...(options.headers as Record<string, string> || {}),
        };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        // Attach CSRF token for mutating requests (POST, PUT, PATCH, DELETE)
        const method = (options.method || 'GET').toUpperCase();
        if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
            const csrfToken = await getCsrfToken(this.DAEMON_URL, token);
            if (csrfToken) {
                headers['X-CSRF-Token'] = csrfToken;
            }
        }

        const resp = await fetch(`${this.DAEMON_URL}/api/v1${path}`, { 
            ...options, 
            headers,
            credentials: 'include'
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ detail: resp.statusText }));
            throw new Error(err.detail || `Request failed: ${resp.status}`);
        }
        return resp.json();
    }

    async getMemoryStats() {
        return this._fetch('/memory/stats');
    }

    async listMemories(limit: number = 50, offset: number = 0) {
        return this._fetch(`/memory?limit=${limit}&offset=${offset}`);
    }

    async consolidateMemory() {
        return this._fetch('/memory/consolidate', { method: 'POST' });
    }

    async deleteMemory(id: string) {
        return this._fetch(`/memory/${id}`, { method: 'DELETE' });
    }

    async pinMemory(id: string, isPinned: boolean) {
        return this._fetch(`/memory/${id}/pin`, { 
            method: 'PATCH',
            body: JSON.stringify({ is_pinned: isPinned })
        });
    }

    async promoteMemory(id: string) {
        return this._fetch(`/memory/${id}/promote`, { method: 'POST' });
    }

    async tagMemory(id: string, tags: string[]) {
        return this._fetch(`/memory/${id}/tags`, { 
            method: 'PATCH',
            body: JSON.stringify({ tags })
        });
    }
}

export const sovereignService = new AlluciSovereignService();
