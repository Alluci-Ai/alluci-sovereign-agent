import React, { useEffect, useRef } from 'react';

interface AudioWaveformVisualizerProps {
    stream: MediaStream | null;
}

export const AudioWaveformVisualizer: React.FC<AudioWaveformVisualizerProps> = ({ stream }) => {
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const audioContextRef = useRef<AudioContext | null>(null);
    const analyserRef = useRef<AnalyserNode | null>(null);
    const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
    const animationFrameRef = useRef<number | null>(null);

    useEffect(() => {
        if (!stream) return;

        // 1. Initialize Audio Context & Analyser
        const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
        const audioContext = new AudioContextClass();
        if (audioContext.state === 'suspended') {
            audioContext.resume();
        }
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        analyser.smoothingTimeConstant = 0.8;

        const source = audioContext.createMediaStreamSource(stream);
        source.connect(analyser);

        audioContextRef.current = audioContext;
        analyserRef.current = analyser;
        sourceRef.current = source;

        // 2. Start Animation Loop
        const canvas = canvasRef.current;
        if (canvas) {
            const ctx = canvas.getContext('2d');
            const bufferLength = analyser.frequencyBinCount;
            const dataArray = new Uint8Array(bufferLength);

            const draw = () => {
                if (!canvasRef.current || !analyserRef.current || !ctx) return;

                animationFrameRef.current = requestAnimationFrame(draw);
                analyserRef.current.getByteFrequencyData(dataArray);

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
