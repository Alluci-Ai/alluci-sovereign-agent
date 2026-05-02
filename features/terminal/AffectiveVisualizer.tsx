import React, { useEffect, useState } from 'react';

interface AffectiveState {
  valence: number; // 0-1024
  arousal: number; // 0-1024
  tension: number; // 0-1024
}

interface AffectiveVisualizerProps {
  state: AffectiveState;
}

export const AffectiveVisualizer: React.FC<AffectiveVisualizerProps> = ({ state }) => {
  const [pulseDuration, setPulseDuration] = useState('2s');
  const [color, setColor] = useState('#10B981'); // Default Emerald

  useEffect(() => {
    // Arousal dictates the speed of the pulsation (high arousal = fast pulse)
    const speed = Math.max(0.5, 3.0 - (state.arousal / 1024) * 2.5);
    setPulseDuration(`${speed}s`);

    // Valence dictates color: 0=Red (Negative), 512=Emerald (Neutral/Positive), 1024=Cyan (High Positive)
    if (state.valence < 400) {
      setColor('#EF4444'); // Red
    } else if (state.valence > 700) {
      setColor('#06B6D4'); // Cyan
    } else {
      setColor('#10B981'); // Emerald
    }
  }, [state]);

  // Tension dictates the polygon complexity/sharpness (Simulated via scale and border)
  const tensionScale = 1.0 + (state.tension / 1024) * 0.2;

  return (
    <div className="flex items-center space-x-4 bg-gray-900/50 p-2 rounded-lg border border-gray-800">
      <div className="relative w-12 h-12 flex items-center justify-center">
        {/* The Ambient Polytope */}
        <div 
          className="absolute inset-0 rounded-lg blur-md"
          style={{ 
            backgroundColor: color,
            opacity: 0.4,
            animation: `pulse ${pulseDuration} cubic-bezier(0.4, 0, 0.6, 1) infinite`
          }} 
        />
        <svg 
          width="32" 
          height="32" 
          viewBox="0 0 32 32" 
          className="relative z-10 transition-transform duration-500"
          style={{ transform: `scale(${tensionScale})` }}
        >
          <polygon 
            points="16,2 30,10 30,22 16,30 2,22 2,10" 
            fill="none" 
            stroke={color} 
            strokeWidth="2"
            style={{ animation: `spin ${parseFloat(pulseDuration) * 4}s linear infinite` }}
          />
        </svg>
      </div>
      
      <div className="flex flex-col text-xs text-gray-400 font-mono">
        <span className="text-gray-300 font-bold uppercase mb-1">ACE Sync</span>
        <div className="flex space-x-2">
          <span>V: {Math.round(state.valence)}</span>
          <span>A: {Math.round(state.arousal)}</span>
          <span>T: {Math.round(state.tension)}</span>
        </div>
      </div>
      
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.4; transform: scale(1); }
          50% { opacity: 0.8; transform: scale(1.1); }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};
