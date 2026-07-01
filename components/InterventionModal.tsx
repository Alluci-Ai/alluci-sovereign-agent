import React from 'react';
import { ShieldAlert, CheckCircle, ArrowDownCircle, ExternalLink } from 'lucide-react';

interface InterventionModalProps {
    isOpen: boolean;
    requestedModel: string;
    modality: string;
    onDowngrade: () => void;
    onApproveException: () => void;
    onAuthorizePermanently: () => void;
}

const InterventionModal: React.FC<InterventionModalProps> = ({ 
    isOpen, 
    requestedModel, 
    modality,
    onDowngrade, 
    onApproveException, 
    onAuthorizePermanently 
}) => {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-md animate-in fade-in duration-300">
            <div className="bg-glass-1 border border-red-500/30 rounded-2xl p-6 max-w-md w-full shadow-[0_0_40px_rgba(239,68,68,0.15)] flex flex-col gap-6 animate-in zoom-in-95 duration-300">
                <div className="flex items-start gap-4">
                    <div className="p-3 bg-red-500/10 rounded-xl text-red-400 border border-red-500/20">
                        <ShieldAlert size={24} />
                    </div>
                    <div className="flex flex-col gap-1">
                        <h2 className="text-lg font-bold text-red-50">Cognitive Boundary Reached</h2>
                        <p className="text-sm text-text-secondary leading-relaxed">
                            Your agent requested to use <span className="font-mono text-accent bg-accent/10 px-1 rounded">{requestedModel}</span> for {modality} synthesis.
                        </p>
                    </div>
                </div>

                <div className="bg-glass-pressed rounded-xl p-4 border border-glass-edge/50">
                    <h3 className="text-[11px] font-bold text-text-primary uppercase tracking-widest mb-2">Why am I seeing this?</h3>
                    <p className="text-xs text-text-secondary">
                        You have not authorized <span className="font-mono text-xs">{requestedModel}</span> under the {modality} category in this Agent's Engine Matrix settings.
                    </p>
                    <a href="#" className="text-[10px] text-accent mt-3 flex items-center gap-1 hover:underline w-fit opacity-80 hover:opacity-100 transition-opacity">
                        Manage all cognitive boundaries in the Engine Matrix Panel <ExternalLink size={10} />
                    </a>
                </div>

                <div className="flex flex-col gap-3 mt-2">
                    <p className="text-[11px] font-medium text-text-tertiary mb-1 text-center">How would you like to proceed?</p>
                    
                    <button 
                        onClick={onDowngrade}
                        className="flex items-center gap-3 w-full p-3 rounded-xl bg-glass-2 border border-glass-edge hover:bg-glass-3 transition-colors text-left"
                    >
                        <ArrowDownCircle size={16} className="text-text-secondary" />
                        <div className="flex flex-col">
                            <span className="text-sm font-medium text-text-primary">Downgrade to Authorized Model</span>
                            <span className="text-[10px] text-text-tertiary">Enforces Matrix and safely degrades inference</span>
                        </div>
                    </button>

                    <button 
                        onClick={onApproveException}
                        className="flex items-center gap-3 w-full p-3 rounded-xl bg-glass-2 border border-glass-edge hover:bg-glass-3 transition-colors text-left"
                    >
                        <ShieldAlert size={16} className="text-yellow-400" />
                        <div className="flex flex-col">
                            <span className="text-sm font-medium text-yellow-50">Approve Exception</span>
                            <span className="text-[10px] text-yellow-100/60">Allows a one-time API bypass for this task only</span>
                        </div>
                    </button>

                    <button 
                        onClick={onAuthorizePermanently}
                        className="flex items-center gap-3 w-full p-3 rounded-xl bg-accent/20 border border-accent/40 hover:bg-accent/30 transition-colors text-left shadow-[0_0_15px_rgba(var(--accent-color),0.15)]"
                    >
                        <CheckCircle size={16} className="text-accent" />
                        <div className="flex flex-col">
                            <span className="text-sm font-medium text-accent">✨ Authorize Permanently</span>
                            <span className="text-[10px] text-accent/70">Automatically adds it to the Engine Matrix</span>
                        </div>
                    </button>
                </div>
            </div>
        </div>
    );
};

export default InterventionModal;
