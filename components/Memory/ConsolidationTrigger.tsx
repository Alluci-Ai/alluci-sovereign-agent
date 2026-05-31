import React, { useState } from 'react';
import { sovereignService } from '../../sovereignService';

export const ConsolidationTrigger: React.FC<{ onComplete?: () => void }> = ({ onComplete }) => {
  const [loading, setLoading] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [summary, setSummary] = useState<any>(null);

  const handleTrigger = async () => {
    setLoading(true);
    setSummary(null);
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const result = await (sovereignService as any).consolidateMemory();
      setSummary(result.cycle_summary);
      if (onComplete) onComplete();
    } catch (e) {
      console.error("Consolidation trigger failed", e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <button
        onClick={handleTrigger}
        disabled={loading}
        className="w-full flex items-center justify-between p-3 rounded-lg border border-emerald-900/40 bg-emerald-950/20 hover:bg-emerald-900/30 transition-colors group disabled:opacity-50"
      >
        <span className="text-emerald-400 font-mono text-xs uppercase tracking-widest">
          {loading ? 'EXECUTING SWEEP...' : 'TRIGGER L0→L1→L2 CONSOLIDATION'}
        </span>
        <div className={`w-2 h-2 rounded-full ${loading ? 'bg-emerald-400 animate-ping' : 'bg-emerald-600'}`} />
      </button>

      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 font-mono text-[9px] text-zinc-500 uppercase">
          <div className="p-2 border border-zinc-900 bg-zinc-900/30 rounded">
            Promoted: <span className="text-emerald-400">{summary.promoted}</span>
          </div>
          <div className="p-2 border border-zinc-900 bg-zinc-900/30 rounded">
            Pruned L1: <span className="text-red-900/70">{summary.pruned_l1}</span>
          </div>
          <div className="p-2 border border-zinc-900 bg-zinc-900/30 rounded">
            Pruned L2: <span className="text-red-900/70">{summary.pruned_l2}</span>
          </div>
          <div className="p-2 border border-zinc-900 bg-zinc-900/30 rounded">
            Pruned L0: <span className="text-zinc-400">{summary.pruned_l0}</span>
          </div>
        </div>
      )}
    </div>
  );
};
