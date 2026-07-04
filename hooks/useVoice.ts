import { useRef, useCallback, useState } from 'react';
import { useStore } from '../store/useStore';
import { getCsrfToken } from '../csrfStore';

export const useVoice = (bridgeManagerRef?: React.RefObject<any>) => {
    const {
        accessToken,
        setIsVoiceRecording,
        setVoiceTranscription,
        setTextInput
    } = useStore();

    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);
    const [stream, setStream] = useState<MediaStream | null>(null);

    const stopRecording = useCallback(async () => {
        // Toggle-to-Speak (Real-time WebSocket mode)
        if (bridgeManagerRef?.current) {
            await bridgeManagerRef.current.stopAudioStream();
            setStream(null);
            setIsVoiceRecording(false);
            return;
        }

        // Fallback hold-to-speak (MediaRecorder mode)
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            mediaRecorderRef.current.stop();
            setIsVoiceRecording(false);
        }
    }, [bridgeManagerRef, setIsVoiceRecording]);

    const startRecording = useCallback(async () => {
        // Toggle-to-Speak (Real-time WebSocket mode)
        if (bridgeManagerRef?.current) {
            try {
                const autoSubmit = true;
                setTextInput("");

                const success = await bridgeManagerRef.current.streamAudioWebSocket(
                    (text: string, type: 'fragment' | 'utterance' | 'cognition') => {
                        if (type === 'fragment') {
                            setTextInput(prev => prev ? `${prev} ${text}` : text);
                        } else if (type === 'utterance') {
                            setVoiceTranscription(text);
                            setTextInput(text);

                            if (autoSubmit) {
                                // Add user prompt to chat history visually
                                useStore.getState().setTranscriptions(prev => [...prev, {
                                    text: text,
                                    isUser: true,
                                    timestamp: new Date().toISOString()
                                }]);
                                setTextInput("");
                            }
                        } else if (type === 'cognition') {
                            // Add assistant response to chat history visually
                            useStore.getState().setTranscriptions(prev => [...prev, {
                                text: text,
                                isUser: false,
                                timestamp: new Date().toISOString()
                            }]);
                            // Stop recording once assistant response is received
                            stopRecording();
                        }
                    },
                    autoSubmit
                );

                if (success) {
                    setStream(bridgeManagerRef.current.getStream());
                    setIsVoiceRecording(true);
                }
            } catch (err) {
                console.error('[useVoice] Failed to establish audio WebSocket stream:', err);
                setIsVoiceRecording(false);
                setStream(null);
            }
            return;
        }

        // Fallback hold-to-speak (MediaRecorder mode)
        try {
            const streamObj = await navigator.mediaDevices.getUserMedia({ audio: true });
            setStream(streamObj);
            const mediaRecorder = new MediaRecorder(streamObj);
            mediaRecorderRef.current = mediaRecorder;
            chunksRef.current = [];

            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    chunksRef.current.push(e.data);
                }
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(chunksRef.current, { type: 'audio/wav' });
                await sendTranscriptionRequest(audioBlob);
                streamObj.getTracks().forEach(track => track.stop());
                setStream(null);
            };

            mediaRecorder.start();
            setIsVoiceRecording(true);
        } catch (err) {
            console.error('Failed to start recording', err);
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [accessToken, setIsVoiceRecording, setVoiceTranscription, setTextInput, bridgeManagerRef, stopRecording]);

    const sendTranscriptionRequest = async (blob: Blob) => {
        const formData = new FormData();
        formData.append('file', blob, 'recording.wav');

        try {
            const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';
            const csrfToken = await getCsrfToken(DAEMON_URL, accessToken);
            const response = await fetch(`${DAEMON_URL}/api/v1/voice/transcribe`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${accessToken}`,
                    ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
                },
                body: formData
            });

            if (response.ok) {
                const data = await response.json();
                if (data.text) {
                    setVoiceTranscription(data.text);
                    setTextInput(prev => prev ? `${prev} ${data.text}` : data.text);
                }
            }
        } catch (err) {
            console.error('Transcription failed', err);
        }
    };

    const playSynthesis = async (text: string) => {
        try {
            const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';
            const response = await fetch(`${DAEMON_URL}/api/v1/voice/synthesise?text=${encodeURIComponent(text)}`, {
                headers: {
                    'Authorization': `Bearer ${accessToken}`
                }
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                const audio = new Audio(url);
                audio.play();
            }
        } catch (err) {
            console.error('Synthesis failed', err);
        }
    };

    return { startRecording, stopRecording, playSynthesis, stream };
};

