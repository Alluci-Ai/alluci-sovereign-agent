import React from 'react';

interface HACIModalProps {
  isOpen: boolean;
  actionDetails: string;
  onApprove: () => void;
  onReject: () => void;
}

export const HACI_Modal: React.FC<HACIModalProps> = ({ isOpen, actionDetails, onApprove, onReject }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-gray-900 border border-red-500 rounded-xl shadow-[0_0_30px_rgba(239,68,68,0.3)] w-full max-w-lg overflow-hidden">
        
        {/* Header */}
        <div className="bg-red-500/10 border-b border-red-500/30 p-4 flex items-center">
          <div className="w-3 h-3 rounded-full bg-red-500 animate-pulse mr-3"></div>
          <h2 className="text-red-400 font-bold uppercase tracking-wider">HACI Intercept Active</h2>
        </div>
        
        {/* Body */}
        <div className="p-6">
          <p className="text-gray-300 mb-4 font-semibold">
            The Sovereign Kill Switch has paused execution. High Cognitive Load action detected:
          </p>
          
          <div className="bg-black/50 p-4 rounded font-mono text-sm text-gray-400 mb-6 border border-gray-800 break-words">
            {actionDetails}
          </div>
          
          <p className="text-xs text-gray-500 mb-6 italic">
            Apple Watch biometric sync confirms your presence. Do you explicitly authorize this destructive action?
          </p>
          
          {/* Actions */}
          <div className="flex justify-end space-x-4">
            <button 
              onClick={onReject}
              className="px-6 py-2 rounded font-bold border border-gray-600 text-gray-300 hover:bg-gray-800 transition-colors"
            >
              Reject
            </button>
            <button 
              onClick={onApprove}
              className="px-6 py-2 rounded font-bold bg-red-600 hover:bg-red-500 text-white shadow-lg transition-colors"
            >
              Authorize
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
