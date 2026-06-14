// eslint-disable-next-line @typescript-eslint/no-unused-vars
import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { PendingAttachment } from '../types';

export const useInteractions = (
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    geminiServiceRef: React.MutableRefObject<any>,
    isConnected: boolean,
    handleAudioOutput: (audio: string) => Promise<void>,
    refreshAuditLog: () => void,
    fileInputRef: React.RefObject<HTMLInputElement | null>,
    sovereignMode: boolean = true
) => {
    const { 
        setTranscriptions, 
        isProcessing, 
        setIsProcessing, 
        textInput, 
        setTextInput,
        attachments,
        setAttachments
    } = useStore();
    const messageQueue = useRef<{ text: string, attachments: PendingAttachment[] }[]>([]);
    const submittingRef = useRef(false);

    // Shared AbortController — AbortButton signals via this ref
    const abortControllerRef = useRef<AbortController | null>(null);

    /**
     * Core inference call, wrapped with AbortController lifecycle.
     * Returns the response text, or throws AbortError if cancelled.
     */
    const runInference = async (
        text: string, 
        files: PendingAttachment[], 
        onToken?: (token: string) => void
    ): Promise<string> => {
        // Create a fresh controller for this request
        const controller = new AbortController();
        abortControllerRef.current = controller;

        try {
            if (geminiServiceRef.current) {
                const mode = sovereignMode ? 'LOCAL' : 'CLOUD';
                const responseText = await geminiServiceRef.current.processMultimodal(text, files, mode, onToken);

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
 
        if (submittingRef.current) return;
        submittingRef.current = true;
 
        // Message Queueing: Buffer if currently processing
        if (isProcessing) {
            messageQueue.current.push({ text: currentText, attachments: currentAttachments });
            setTextInput("");
            setAttachments([]);
            console.info("[ UX ]: Message buffered during stream.");
            submittingRef.current = false;
            return;
        }
 
        setTranscriptions(prev => [...prev, { text: currentText, isUser: true, timestamp: new Date().toISOString() }]);
        setTextInput("");
        setAttachments([]);
        setIsProcessing(true);
 
        const assistantMsgId = `assistant-stream-${Date.now()}`;
        setTranscriptions(prev => [...prev, { 
            text: '', 
            isUser: false, 
            timestamp: new Date().toISOString(), 
            id: assistantMsgId 
        }]);
 
        try {
            let cumulativeText = '';
            const responseText = await runInference(currentText, currentAttachments, (token) => {
                cumulativeText += token;
                setTranscriptions(prev => prev.map(msg => 
                    msg.id === assistantMsgId ? { ...msg, text: cumulativeText } : msg
                ));
            });
            setTranscriptions(prev => prev.map(msg => 
                msg.id === assistantMsgId ? { ...msg, text: responseText } : msg
            ));
 
            if (isConnected) {
                await geminiServiceRef.current?.speak(responseText, handleAudioOutput);
            }
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        } catch (err: any) {
            // Distinguish user abort from real errors
            if (err?.name === 'AbortError') {
                console.info("[ UX ]: Generation aborted by user.");
                setTranscriptions(prev => prev.filter(msg => msg.id !== assistantMsgId));
            } else {
                console.error(err);
                setTranscriptions(prev => prev.map(msg => 
                    msg.id === assistantMsgId ? { ...msg, text: "[ ERROR ]: Communication manifold disrupted." } : msg
                ));
            }
        } finally {
            setIsProcessing(false);
            refreshAuditLog();
            submittingRef.current = false;
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
                    
                    const assistantMsgId = `assistant-stream-${Date.now()}`;
                    setTranscriptions(prev => [...prev, { 
                        text: '', 
                        isUser: false, 
                        timestamp: new Date().toISOString(), 
                        id: assistantMsgId 
                    }]);

                    try {
                        let cumulativeText = '';
                        const responseText = await runInference(next.text, next.attachments, (token) => {
                            cumulativeText += token;
                            setTranscriptions(prev => prev.map(msg => 
                                msg.id === assistantMsgId ? { ...msg, text: cumulativeText } : msg
                            ));
                        });
                        setTranscriptions(prev => prev.map(msg => 
                            msg.id === assistantMsgId ? { ...msg, text: responseText } : msg
                        ));
                        if (isConnected) {
                            await geminiServiceRef.current?.speak(responseText, handleAudioOutput);
                        }
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    } catch (err: any) {
                        if (err?.name === 'AbortError') {
                            console.info("[ UX ]: Queued generation aborted.");
                            setTranscriptions(prev => prev.filter(msg => msg.id !== assistantMsgId));
                        } else {
                            console.error(err);
                            setTranscriptions(prev => prev.map(msg => 
                                msg.id === assistantMsgId ? { ...msg, text: "[ ERROR ]: Communication manifold disrupted." } : msg
                            ));
                        }
                    } finally {
                        setIsProcessing(false);
                        refreshAuditLog();
                    }
                };
                processQueued();
            }
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

