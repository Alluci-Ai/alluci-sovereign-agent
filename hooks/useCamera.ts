
import { useRef, useCallback } from 'react';
import { useStore } from '../store/useStore';

export const useCamera = (geminiServiceRef: React.RefObject<any>, isConnected: boolean) => {
  const { isCameraActive, setIsCameraActive } = useStore();
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const frameIntervalRef = useRef<number | null>(null);

  const toggleCamera = useCallback(async () => {
    if (isCameraActive) {
      setIsCameraActive(false);
      if (videoRef.current?.srcObject) {
        (videoRef.current.srcObject as MediaStream).getTracks().forEach(t => t.stop());
      }
      if (frameIntervalRef.current) {
        clearInterval(frameIntervalRef.current);
        frameIntervalRef.current = null;
      }
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setIsCameraActive(true);
        frameIntervalRef.current = window.setInterval(() => {
          if (canvasRef.current && isConnected && geminiServiceRef.current) {
            const ctx = canvasRef.current.getContext('2d');
            ctx?.drawImage(videoRef.current!, 0, 0, 320, 240);
            geminiServiceRef.current.sendVideoFrame(canvasRef.current.toDataURL('image/jpeg', 0.5).split(',')[1]);
          }
        }, 1500);
      }
    } catch (err) {
      console.error("Camera access failed:", err);
    }
  }, [isCameraActive, setIsCameraActive, isConnected, geminiServiceRef]);

  return {
    videoRef,
    canvasRef,
    isCameraActive,
    toggleCamera
  };
};
