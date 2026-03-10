import { useRef, useCallback } from 'react';
import { useStore } from '../store/useStore';

export const useVoice = () => {
    const {
        accessToken,
        setIsVoiceRecording,
        setVoiceTranscription,
        setTextInput
    } = useStore();

    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);

    const startRecording = useCallback(async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mediaRecorder = new MediaRecorder(stream);
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
                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorder.start();
            setIsVoiceRecording(true);
        } catch (err) {
            console.error('Failed to start recording', err);
        }
    }, [accessToken, setIsVoiceRecording, setVoiceTranscription, setTextInput]);

    const stopRecording = useCallback(() => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            mediaRecorderRef.current.stop();
            setIsVoiceRecording(false);
        }
    }, [setIsVoiceRecording]);

    const sendTranscriptionRequest = async (blob: Blob) => {
        const formData = new FormData();
        formData.append('file', blob, 'recording.wav');

        try {
            const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';
            const response = await fetch(`${DAEMON_URL}/api/voice/transcribe`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${accessToken}`
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
            const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';
            const response = await fetch(`${DAEMON_URL}/api/voice/synthesise?text=${encodeURIComponent(text)}`, {
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

    return { startRecording, stopRecording, playSynthesis };
};
