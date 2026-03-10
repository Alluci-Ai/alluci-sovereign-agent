import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { PendingAttachment } from '../types';

export const useInteractions = (
    geminiServiceRef: React.MutableRefObject<any>,
    isConnected: boolean,
    handleAudioOutput: (audio: string) => Promise<void>,
    refreshAuditLog: () => void,
    fileInputRef: React.RefObject<HTMLInputElement | null>
) => {
    const { setTranscriptions, isProcessing, setIsProcessing, textInput, setTextInput } = useStore();
    const [attachments, setAttachments] = useState<PendingAttachment[]>([]);
    const messageQueue = useRef<{ text: string, attachments: PendingAttachment[] }[]>([]);

    // Shared AbortController — AbortButton signals via this ref
    const abortControllerRef = useRef<AbortController | null>(null);

    /**
     * Core inference call, wrapped with AbortController lifecycle.
     * Returns the response text, or throws AbortError if cancelled.
     */
    const runInference = async (text: string, files: PendingAttachment[]): Promise<string> => {
        // Create a fresh controller for this request
        const controller = new AbortController();
        abortControllerRef.current = controller;

        try {
            if (geminiServiceRef.current) {
                const responseText = await geminiServiceRef.current.processMultimodal(text, files);

                // Check if aborted during the call
                if (controller.signal.aborted) {
                    throw new DOMException('Aborted', 'AbortError');
                }

                return responseText;
            }
            return "[ ERROR ]: Gemini service not initialized.";
        } finally {
            // Clear the ref only if this controller is still current
            if (abortControllerRef.current === controller) {
                abortControllerRef.current = null;
            }
        }
    };

    const handleCommandSubmit = async (e?: React.FormEvent) => {
        if (e) e.preventDefault();

        const currentText = textInput.trim();
        const currentAttachments = [...attachments];

        if (!currentText && currentAttachments.length === 0) return;

        // Message Queueing: Buffer if currently processing
        if (isProcessing) {
            messageQueue.current.push({ text: currentText, attachments: currentAttachments });
            setTextInput("");
            setAttachments([]);
            console.info("[ UX ]: Message buffered during stream.");
            return;
        }

        setTranscriptions(prev => [...prev, { text: currentText, isUser: true, timestamp: new Date().toISOString() }]);
        setTextInput("");
        setAttachments([]);
        setIsProcessing(true);

        try {
            const responseText = await runInference(currentText, currentAttachments);
            setTranscriptions(prev => [...prev, { text: responseText, isUser: false, timestamp: new Date().toISOString() }]);

            if (isConnected) {
                await geminiServiceRef.current?.speak(responseText, handleAudioOutput);
            }
        } catch (err: any) {
            // Distinguish user abort from real errors
            if (err?.name === 'AbortError') {
                console.info("[ UX ]: Generation aborted by user.");
                // Message is appended by AbortButton.onAbort — don't double-append
            } else {
                console.error(err);
                setTranscriptions(prev => [...prev, { text: "[ ERROR ]: Communication manifold disrupted.", isUser: false, timestamp: new Date().toISOString() }]);
            }
        } finally {
            setIsProcessing(false);
            refreshAuditLog();
        }
    };

    // Replay queue when processing finishes
    useEffect(() => {
        if (!isProcessing && messageQueue.current.length > 0) {
            const next = messageQueue.current.shift();
            if (next) {
                // Direct execution: bypass input state, process the queued message directly
                const processQueued = async () => {
                    setTranscriptions(prev => [...prev, { text: next.text, isUser: true, timestamp: new Date().toISOString() }]);
                    setIsProcessing(true);
                    try {
                        const responseText = await runInference(next.text, next.attachments);
                        setTranscriptions(prev => [...prev, { text: responseText, isUser: false, timestamp: new Date().toISOString() }]);
                        if (isConnected) {
                            await geminiServiceRef.current?.speak(responseText, handleAudioOutput);
                        }
                    } catch (err: any) {
                        if (err?.name === 'AbortError') {
                            console.info("[ UX ]: Queued generation aborted.");
                        } else {
                            console.error(err);
                            setTranscriptions(prev => [...prev, { text: "[ ERROR ]: Communication manifold disrupted.", isUser: false, timestamp: new Date().toISOString() }]);
                        }
                    } finally {
                        setIsProcessing(false);
                        refreshAuditLog();
                    }
                };
                processQueued();
            }
        }
    }, [isProcessing]);

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (!files) return;
        await processFiles(files);
        if (fileInputRef.current) fileInputRef.current.value = '';
    };

    const processFiles = async (files: FileList | File[]) => {
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
    };

    const handlePaste = useCallback(async (e: React.ClipboardEvent) => {
        const items = e.clipboardData?.items;
        if (!items) return;

        const imageFiles: File[] = [];
        for (let i = 0; i < items.length; i++) {
            if (items[i].type.indexOf('image') !== -1) {
                const file = items[i].getAsFile();
                if (file) imageFiles.push(file);
            }
        }

        if (imageFiles.length > 0) {
            console.info(`[ UX ]: Extracting ${imageFiles.length} pasted images.`);
            await processFiles(imageFiles);
        }
    }, [attachments]);

    const removeAttachment = (idx: number) => {
        setAttachments(prev => prev.filter((_, i) => i !== idx));
    };

    return {
        textInput, setTextInput,
        attachments, setAttachments,
        handleCommandSubmit,
        handleFileChange,
        handlePaste,
        removeAttachment,
        abortControllerRef,  // Exposed for AbortButton
    };
};

