import React, { useEffect, useRef } from 'react';

interface AudioWaveformVisualizerProps {
    stream: MediaStream | null;
    analyser?: AnalyserNode | null;
}

export const AudioWaveformVisualizer: React.FC<AudioWaveformVisualizerProps> = ({ stream, analyser: providedAnalyser }) => {
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const audioContextRef = useRef<AudioContext | null>(null);
    const analyserRef = useRef<AnalyserNode | null>(null);
    const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
    const animationFrameRef = useRef<number | null>(null);

    useEffect(() => {
        if (!stream && !providedAnalyser) return;

        let activeAnalyser: AnalyserNode;

        if (providedAnalyser) {
            activeAnalyser = providedAnalyser;
        } else {
            // Fallback: Initialize Audio Context & Analyser locally
            const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
            const audioContext = new AudioContextClass();
            if (audioContext.state === 'suspended') {
                audioContext.resume();
            }
            const newAnalyser = audioContext.createAnalyser();
            newAnalyser.fftSize = 256;
            newAnalyser.smoothingTimeConstant = 0.8;

            if (stream) {
                const source = audioContext.createMediaStreamSource(stream);
                source.connect(newAnalyser);
                sourceRef.current = source;
            }

            audioContextRef.current = audioContext;
            analyserRef.current = newAnalyser;
            activeAnalyser = newAnalyser;
        }

        // 2. Start Animation Loop
        const canvas = canvasRef.current;
        if (canvas) {
            const ctx = canvas.getContext('2d');
            const bufferLength = activeAnalyser.frequencyBinCount;
            const dataArray = new Uint8Array(bufferLength);

            const draw = () => {
                if (!canvasRef.current || !ctx) return;

                animationFrameRef.current = requestAnimationFrame(draw);
                activeAnalyser.getByteFrequencyData(dataArray);

                const width = canvas.width;
                const height = canvas.height;

                // Clear with a transparent backing
                ctx.clearRect(0, 0, width, height);

                // Draw audio wave bars with glow
                const barWidth = (width / bufferLength) * 1.6;
                let barHeight;
                let x = 0;

                ctx.shadowBlur = 15;
                ctx.shadowColor = 'rgba(255, 125, 0, 0.6)';

                // Create sleek linear gradient for visualizer bars
                const gradient = ctx.createLinearGradient(0, height, 0, 0);
                gradient.addColorStop(0, 'rgba(255, 125, 0, 0.1)');
                gradient.addColorStop(0.5, 'rgba(255, 125, 0, 0.8)');
                gradient.addColorStop(1, 'rgba(255, 125, 0, 1)');

                ctx.fillStyle = gradient;

                for (let i = 0; i < bufferLength; i++) {
                    // Amplitude scaling (minimum 2px height so it's visible in silence)
                    barHeight = Math.max(2, (dataArray[i] / 255) * height * 0.85);

                    // Centering visualizer waves symmetrically
                    const y = (height - barHeight) / 2;

                    // Rounded visualizer bars
                    ctx.beginPath();
                    ctx.roundRect(x, y, barWidth - 2, barHeight, 4);
                    ctx.fill();

                    x += barWidth;
                }
            };

            draw();
        }

        // Cleanup on stream change / component unmount
        return () => {
            if (animationFrameRef.current) {
                cancelAnimationFrame(animationFrameRef.current);
            }
            if (sourceRef.current) {
                sourceRef.current.disconnect();
            }
            if (audioContextRef.current) {
                audioContextRef.current.close().catch(() => {});
            }
        };
    }, [stream]);

    return (
        <canvas
            ref={canvasRef}
            className="w-full h-8 max-w-md mx-auto opacity-90 transition-all duration-300 pointer-events-none"
            width={320}
            height={32}
            style={{
                filter: 'drop-shadow(0 0 8px rgba(255, 125, 0, 0.25))',
            }}
        />
    );
};
