import { useState, useRef, useEffect, useCallback } from 'react';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';
const WS_URL = DAEMON_URL 
    ? DAEMON_URL.replace(/^http/, 'ws')
    : (window.location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + window.location.host;

export const useVoiceStream = (
    onTranscriptionFragment: (text: string, isFinal: boolean) => void,
    onUtteranceFinalized: (text: string) => void
) => {
    const [isRecording, setIsRecording] = useState(false);
    const [isAgentSpeaking, setIsAgentSpeaking] = useState(false);
    const [isConnected, setIsConnected] = useState(false);
    
    const wsRef = useRef<WebSocket | null>(null);
    const audioCtxRef = useRef<AudioContext | null>(null);
    const workletNodeRef = useRef<AudioWorkletNode | null>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const playbackCtxRef = useRef<AudioContext | null>(null);
    
    // Auto-muting reference so the worklet listener can check it cleanly
    const isAgentSpeakingRef = useRef(false);
    const isRecordingRef = useRef(false);

    useEffect(() => {
        isAgentSpeakingRef.current = isAgentSpeaking;
    }, [isAgentSpeaking]);

    useEffect(() => {
        isRecordingRef.current = isRecording;
    }, [isRecording]);

    const stopRecording = useCallback(() => {
        setIsRecording(false);
        if (workletNodeRef.current) {
            workletNodeRef.current.disconnect();
            workletNodeRef.current = null;
        }
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop());
            streamRef.current = null;
        }
        if (audioCtxRef.current) {
            audioCtxRef.current.close();
            audioCtxRef.current = null;
        }
    }, []);

    const playPcmAudio = useCallback(async (pcmData: ArrayBuffer) => {
        if (!playbackCtxRef.current) {
            playbackCtxRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 48000 });
        }
        
        const audioCtx = playbackCtxRef.current;
        if (audioCtx.state === 'suspended') {
            await audioCtx.resume();
        }

        // Convert Int16 PCM to Float32 for Web Audio API
        const int16Array = new Int16Array(pcmData);
        const float32Array = new Float32Array(int16Array.length);
        for (let i = 0; i < int16Array.length; i++) {
            float32Array[i] = int16Array[i] / 32768.0;
        }

        const audioBuffer = audioCtx.createBuffer(1, float32Array.length, 48000);
        audioBuffer.getChannelData(0).set(float32Array);

        const source = audioCtx.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(audioCtx.destination);
        
        source.onended = () => {
            setIsAgentSpeaking(false);
        };
        
        setIsAgentSpeaking(true);
        source.start();
    }, []);

    const connectWebSocket = useCallback(() => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;
        
        const ws = new WebSocket(`${WS_URL}/api/v1/voice/stream?device_tier=MACBOOK_WORKSTATION&auto_submit=true`);
        ws.binaryType = 'arraybuffer';
        
        ws.onopen = () => setIsConnected(true);
        ws.onclose = () => setIsConnected(false);
        
        ws.onmessage = async (event) => {
            if (typeof event.data === 'string') {
                try {
                    const payload = JSON.parse(event.data);
                    // Discard incoming transcription fragments if recording was halted
                    if (!isRecordingRef.current && (payload.type === 'fragment' || payload.type === 'utterance')) {
                        return;
                    }
                    if (payload.type === 'fragment') {
                        onTranscriptionFragment(payload.text, false);
                    } else if (payload.type === 'utterance') {
                        onTranscriptionFragment(payload.text, true);
                        onUtteranceFinalized(payload.text);
                        // VAD finalized the utterance, stop recording
                        stopRecording();
                    } else if (payload.type === 'cognition') {
                        // The LLM text response
                    }
                } catch (e) {
                    console.error("Failed to parse voice WS message:", e);
                }
            } else if (event.data instanceof ArrayBuffer) {
                // Incoming PCM binary audio from Kokoro
                await playPcmAudio(event.data);
            }
        };
        
        wsRef.current = ws;
    }, [onTranscriptionFragment, onUtteranceFinalized, playPcmAudio, stopRecording]);

    const startRecording = useCallback(async () => {
        try {
            connectWebSocket();
            
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: { echoCancellation: true, noiseSuppression: true } 
            });
            streamRef.current = stream;
            
            const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
            audioCtxRef.current = audioCtx;
            
            await audioCtx.audioWorklet.addModule('/audio-processor.js');
            
            const source = audioCtx.createMediaStreamSource(stream);
            const workletNode = new AudioWorkletNode(audioCtx, 'audio-processor');
            workletNodeRef.current = workletNode;
            
            // Send the native sample rate to the processor so it can calculate the ratio
            workletNode.port.postMessage({ type: 'init', sampleRate: audioCtx.sampleRate });
            
            workletNode.port.onmessage = (event) => {
                if (event.data.type === 'audio') {
                    // Mute outbound audio if the agent is speaking
                    if (!isAgentSpeakingRef.current && wsRef.current?.readyState === WebSocket.OPEN) {
                        wsRef.current.send(event.data.data);
                    }
                }
            };
            
            source.connect(workletNode);
            // DO NOT connect workletNode to destination to avoid feedback
            
            setIsRecording(true);
        } catch (e) {
            console.error("Failed to start recording:", e);
            stopRecording();
        }
    }, [connectWebSocket, stopRecording]);

    const toggleRecording = useCallback(() => {
        if (isRecording) {
            // Send manual finalize signal if stopped by user
            if (wsRef.current?.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify({ type: 'control', action: 'finalize_utterance' }));
            }
            stopRecording();
        } else {
            startRecording();
        }
    }, [isRecording, startRecording, stopRecording]);

    useEffect(() => {
        return () => {
            stopRecording();
            if (wsRef.current) wsRef.current.close();
        };
    }, [stopRecording]);

    return {
        isRecording,
        isAgentSpeaking,
        isConnected,
        toggleRecording,
        stream: streamRef.current
    };
};
