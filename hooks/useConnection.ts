import React from 'react';
import { AlluciGeminiService } from '../geminiService';
import { AlluciSovereignService, SovereignCallbacks } from '../sovereignService';
import { useStore } from '../store/useStore';
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { clamp01 } from '../alluciCore';

export const useSovereignConnection = (
    geminiServiceRef: React.MutableRefObject<AlluciGeminiService | null>,
    sovereignServiceRef: React.MutableRefObject<AlluciSovereignService | null>,
    audioContextRef: React.MutableRefObject<AudioContext | null>,
    sourcesRef: React.MutableRefObject<Set<AudioBufferSourceNode>>,
    nextStartTimeRef: React.MutableRefObject<number>,
    refreshAuditLog: () => void,
    handleAudioOutput: (audio: string) => Promise<void>,
    sovereignMode: boolean,
    setAudioStream: (stream: MediaStream | null) => void
) => {
    const isConnected = useStore(state => state.isConnected);
    const setIsConnected = useStore(state => state.setIsConnected);
    const setTranscriptions = useStore(state => state.setTranscriptions);
    const setCanvasNodes = useStore(state => state.setCanvasNodes);
    const setActiveView = useStore(state => state.setActiveView);
    const connections = useStore(state => state.connections);
    const skills = useStore(state => state.skills);
    const accessToken = useStore(state => state.accessToken);
    const loadAvailableModels = useStore(state => state.loadAvailableModels);

    const handleConnect = async () => {
        if (isConnected) {
            geminiServiceRef.current?.disconnect();
            sovereignServiceRef.current?.disconnect();
            setIsConnected(false);
            setAudioStream(null);
            return;
        }

        try {
            if (accessToken) {
                await loadAvailableModels(accessToken);
            }

            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            setAudioStream(stream);

            const audioContext = audioContextRef.current!;
            if (audioContext.state === 'suspended') {
                await audioContext.resume();
            }

            await audioContext.audioWorklet.addModule('/audio-processor.js');
            const audioWorkletNode = new AudioWorkletNode(audioContext, 'audio-processor');
            const sourceNode = audioContext.createMediaStreamSource(stream);
            sourceNode.connect(audioWorkletNode);
            audioWorkletNode.connect(audioContext.destination);

            audioWorkletNode.port.onmessage = (e) => {
                const inputData = e.data;
                if (sovereignMode && sovereignServiceRef.current) {
                    sovereignServiceRef.current.sendAudio(inputData);
                } else if (geminiServiceRef.current) {
                    geminiServiceRef.current.sendRealtimeInput(inputData);
                }
            };

            if (sovereignMode) {
                if (!sovereignServiceRef.current) sovereignServiceRef.current = new AlluciSovereignService();

                const callbacks: SovereignCallbacks = {
                    onOpen: () => { setIsConnected(true); refreshAuditLog(); },
                    onClose: () => setIsConnected(false),
                    onAudioOutput: (b64) => {
                        const audio = new Audio("data:audio/wav;base64," + b64);
                        audio.play();
                    },
                    onTranscription: (text, isUser) => {
                        setTranscriptions(prev => {
                            const last = prev[prev.length - 1];
                            if (last && last.isUser === isUser) {
                                const updated = [...prev];
                                updated[updated.length - 1] = { ...last, text: last.text + text };
                                return updated;
                            }
                            return [...prev.slice(-49), { text, isUser, timestamp: new Date().toISOString() }];
                        });
                        refreshAuditLog();
                    },
                    onLLMChunk: (chunk) => {
                        setTranscriptions(prev => {
                            const last = prev[prev.length - 1];
                            if (last && !last.isUser) {
                                const updated = [...prev];
                                updated[updated.length - 1] = { ...last, text: last.text + chunk };
                                return updated;
                            }
                            return [...prev.slice(-49), { text: chunk, isUser: false, timestamp: new Date().toISOString() }];
                        });
                    },
                    onInterrupted: () => {
                        sourcesRef.current.forEach(s => s.stop());
                        sourcesRef.current.clear();
                        nextStartTimeRef.current = 0;
                    },
                    onError: (err) => console.error("Sovereign Error:", err),
                    onGroundingSources: (sources) => {
                        setTranscriptions(prev => {
                            const next = [...prev];
                            for (let i = next.length - 1; i >= 0; i--) {
                                if (!next[i].isUser) {
                                    next[i].sources = sources;
                                    break;
                                }
                            }
                            return next;
                        });
                    },
                    onCanvasManifest: (node) => {
                        setCanvasNodes(prev => [...prev, { ...node, id: `node_${Date.now()}` }]);
                        setActiveView('canvas');
                        geminiServiceRef.current?.audit.addEntry("A2UI_MANIFEST_RECEIVED", { type: node.type });
                        refreshAuditLog();
                    }
                };
                await sovereignServiceRef.current.connect(callbacks, accessToken || "");
            } else {
                if (!geminiServiceRef.current) geminiServiceRef.current = new AlluciGeminiService();
                geminiServiceRef.current.setConnections(connections);
                geminiServiceRef.current.setSkills(skills.filter(s => s.verified));

                await geminiServiceRef.current.connect({
                    onAudioOutput: handleAudioOutput,
                    onTranscription: (text, isUser) => {
                        setTranscriptions(prev => {
                            const last = prev[prev.length - 1];
                            if (last && last.isUser === isUser) {
                                const updated = [...prev];
                                updated[updated.length - 1] = { ...last, text: last.text + text };
                                return updated;
                            }
                            return [...prev.slice(-49), { text, isUser, timestamp: new Date().toISOString() }];
                        });
                        refreshAuditLog();
                    }
                });
            }
        } catch (err) {
            console.error("Connection failed:", err);
            setIsConnected(false);
        }
    };

    return { handleConnect };
};
