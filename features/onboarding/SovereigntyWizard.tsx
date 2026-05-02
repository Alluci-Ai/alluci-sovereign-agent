import React, { useState } from 'react';

type SovereigntyLevel = 1 | 2 | 3;

interface WizardProps {
  onComplete: (level: SovereigntyLevel) => void;
}

export const SovereigntyWizard: React.FC<WizardProps> = ({ onComplete }) => {
  const [level, setLevel] = useState<SovereigntyLevel>(1);

  const handleSelect = (selectedLevel: SovereigntyLevel) => {
    setLevel(selectedLevel);
  };

  const handleApply = () => {
    // In production, this would trigger an IPC call to write the .env config 
    // and initialize the required daemons for the selected level.
    console.log(`Applying Sovereignty Level ${level} configuration...`);
    onComplete(level);
  };

  return (
    <div className="flex flex-col items-center justify-center p-8 bg-gray-900 text-white rounded-xl shadow-2xl border border-gray-800 w-full max-w-4xl mx-auto mt-10">
      <div className="mb-8 text-center">
        <h2 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400 mb-2">
          Select Your Sovereignty Level
        </h2>
        <p className="text-gray-400">
          Choose how much control and privacy you require. You can upgrade at any time.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full mb-10">
        {/* Level 1: Cloud-Only */}
        <div 
          onClick={() => handleSelect(1)}
          className={`cursor-pointer p-6 rounded-lg border-2 transition-all duration-300 ${level === 1 ? 'border-blue-500 bg-blue-900/20' : 'border-gray-700 hover:border-gray-500'}`}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-blue-400">Level 1</h3>
            <span className="text-xs font-semibold px-2 py-1 bg-blue-900/50 text-blue-300 rounded">Cloud-Only</span>
          </div>
          <p className="text-sm text-gray-300 mb-4">
            Zero local setup. Connects securely to 3rd-party APIs (OpenAI, Anthropic). Best for immediate onboarding.
          </p>
          <ul className="text-xs text-gray-400 space-y-2 list-disc list-inside">
            <li>No hardware requirements</li>
            <li>Instant setup</li>
            <li>Data processed externally</li>
          </ul>
        </div>

        {/* Level 2: Local LLM */}
        <div 
          onClick={() => handleSelect(2)}
          className={`cursor-pointer p-6 rounded-lg border-2 transition-all duration-300 ${level === 2 ? 'border-purple-500 bg-purple-900/20' : 'border-gray-700 hover:border-gray-500'}`}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-purple-400">Level 2</h3>
            <span className="text-xs font-semibold px-2 py-1 bg-purple-900/50 text-purple-300 rounded">Local Edge</span>
          </div>
          <p className="text-sm text-gray-300 mb-4">
            Runs local LLMs (Gemma 4 / Llama) via Ollama. Data remains on your hardware. Medium setup required.
          </p>
          <ul className="text-xs text-gray-400 space-y-2 list-disc list-inside">
            <li>Requires 8GB+ VRAM</li>
            <li>Absolute data privacy</li>
            <li>Cloud fallback disabled</li>
          </ul>
        </div>

        {/* Level 3: Full Sovereign */}
        <div 
          onClick={() => handleSelect(3)}
          className={`cursor-pointer p-6 rounded-lg border-2 transition-all duration-300 ${level === 3 ? 'border-emerald-500 bg-emerald-900/20 shadow-[0_0_15px_rgba(16,185,129,0.3)]' : 'border-gray-700 hover:border-gray-500'}`}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-emerald-400">Level 3</h3>
            <span className="text-xs font-semibold px-2 py-1 bg-emerald-900/50 text-emerald-300 rounded">Sovereign Base</span>
          </div>
          <p className="text-sm text-gray-300 mb-4">
            The ultimate sovereign stack. Integrates Local LLM, Watch Biometrics, VerusID, and Signal-CLI bridges.
          </p>
          <ul className="text-xs text-gray-400 space-y-2 list-disc list-inside">
            <li>Polytope Geometric Sync</li>
            <li>Zero Trust Architecture</li>
            <li>Sovereign Kill Switch active</li>
          </ul>
        </div>
      </div>

      <button 
        onClick={handleApply}
        className="px-8 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold rounded shadow-lg transition-transform hover:scale-105 active:scale-95"
      >
        Initialize Level {level} Architecture
      </button>
    </div>
  );
};
