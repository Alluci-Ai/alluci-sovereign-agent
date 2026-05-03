
import { useRef, useCallback, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { decode, decodeAudioData } from '../geminiService';
import { clamp01 } from '../alluciCore';

export const useAudioOutput = () => {
  const { updateAgent } = useStore();
  const audioContextRef = useRef<AudioContext | null>(null);
  const nextStartTimeRef = useRef<number>(0);
  const sourcesRef = useRef<Set<AudioBufferSourceNode>>(new Set());

  useEffect(() => {
    audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 24000 });
    return () => {
      audioContextRef.current?.close();
    };
  }, []);

  const handleAudioOutput = useCallback(async (base64Audio: string) => {
    if (!audioContextRef.current) return;
    const ctx = audioContextRef.current;
    nextStartTimeRef.current = Math.max(nextStartTimeRef.current, ctx.currentTime);
    const buffer = await decodeAudioData(decode(base64Audio), ctx, 24000, 1);
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(ctx.destination);
    source.start(nextStartTimeRef.current);
    nextStartTimeRef.current += buffer.duration;
    sourcesRef.current.add(source);
    updateAgent(prev => ({ ...prev, valenceCurvature: clamp01(prev.valenceCurvature + 0.15) }));
  }, [updateAgent]);

  return {
    audioContextRef,
    nextStartTimeRef,
    sourcesRef,
    handleAudioOutput
  };
};
