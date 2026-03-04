import React, { useState, useRef, useCallback } from 'react';
import { useStore } from '../store/useStore';
import { PendingAttachment } from '../types';

export const useInteractions = (
    geminiServiceRef: React.MutableRefObject<any>,
    isConnected: boolean,
    handleAudioOutput: (audio: string) => Promise<void>,
    refreshAuditLog: () => void,
    fileInputRef: React.RefObject<HTMLInputElement | null>
) => {
    const { setTranscriptions, isProcessing, setIsProcessing } = useStore();
    const [textInput, setTextInput] = useState("");
    const [attachments, setAttachments] = useState<PendingAttachment[]>([]);

    const handleCommandSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!textInput.trim() && attachments.length === 0) return;
        if (isProcessing) return;

        const currentText = textInput;
        const currentAttachments = [...attachments];

        setTranscriptions(prev => [...prev, { text: currentText, isUser: true, timestamp: new Date().toISOString() }]);
        setTextInput("");
        setAttachments([]);
        setIsProcessing(true);

        try {
            if (geminiServiceRef.current) {
                const responseText = await geminiServiceRef.current.processMultimodal(currentText, currentAttachments);
                setTranscriptions(prev => [...prev, { text: responseText, isUser: false, timestamp: new Date().toISOString() }]);

                if (isConnected) {
                    await geminiServiceRef.current.speak(responseText, handleAudioOutput);
                }
            }
        } catch (err) {
            console.error(err);
            setTranscriptions(prev => [...prev, { text: "[ ERROR ]: Communication manifold disrupted.", isUser: false, timestamp: new Date().toISOString() }]);
        } finally {
            setIsProcessing(false);
            refreshAuditLog();
        }
    };

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (!files) return;
        const newAttachments: PendingAttachment[] = [];
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const reader = new FileReader();
            const base64Promise = new Promise<string>((resolve) => {
                reader.onload = () => resolve((reader.result as string).split(',')[1]);
            });
            reader.readAsDataURL(file);
            const data = await base64Promise;
            newAttachments.push({ name: file.name, data, mimeType: file.type });
        }
        setAttachments(prev => [...prev, ...newAttachments]);
        if (fileInputRef.current) fileInputRef.current.value = '';
    };

    const removeAttachment = (idx: number) => {
        setAttachments(prev => prev.filter((_, i) => i !== idx));
    };

    return {
        textInput, setTextInput,
        attachments, setAttachments,
        handleCommandSubmit,
        handleFileChange,
        removeAttachment
    };
};
