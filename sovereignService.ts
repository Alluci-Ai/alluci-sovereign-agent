
export interface SovereignCallbacks {
    onAudioOutput: (base64Audio: string) => void;
    onTranscription: (text: string, isUser: boolean) => void;
    onLLMChunk: (text: string) => void;
    onOpen: () => void;
    onClose: () => void;
    onError: (error: any) => void;
    onGroundingSources?: (sources: any[]) => void;
    onInterrupted?: () => void;
    onCanvasManifest?: (node: any) => void;
}

export class AlluciSovereignService {
    private socket: WebSocket | null = null;
    private audioContext: AudioContext | null = null;
    private DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';
    private WS_URL = this.DAEMON_URL.replace('http', 'ws') + '/ws/sovereign';

    constructor() { }

    async connect(callbacks: SovereignCallbacks, token: string) {
        this.socket = new WebSocket(`${this.WS_URL}?token=${token}`);

        this.socket.onopen = () => {
            console.log("[ SOVEREIGN ]: Connected.");
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
}
