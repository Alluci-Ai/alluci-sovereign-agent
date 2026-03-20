import React, { useEffect, useState } from 'react';
import { sovereignService } from '../../sovereignService';

interface TierStats {
  backend: string;
  entries: number;
  sql_entries?: number;
  half_life_days?: number;
  promotion_threshold?: number;
}

interface HLSMStatsData {
  hlsm_version: string;
  tiers: {
    L0_working: TierStats;
    L1_episodic: TierStats;
    L2_semantic: TierStats;
  };
  consolidation_interval_minutes: number;
}

export const HLSMStats: React.FC = () => {
  const [stats, setStats] = useState<HLSMStatsData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchStats = async () => {
    try {
      const resp = await sovereignService.getMemoryStats();
      setStats(resp);
    } catch (e) {
      console.error("Failed to fetch memory stats", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    const timer = setInterval(fetchStats, 10000);
    return () => clearInterval(timer);
  }, []);

  if (loading || !stats) return <div className="text-zinc-500 animate-pulse">Loading Manifold Statistics...</div>;

  return (
    <div className="space-y-4 font-mono text-xs">
      <div className="flex justify-between border-b border-zinc-800 pb-2">
        <span className="text-zinc-400">H-LSM REVISION</span>
        <span className="text-emerald-400 underline decoration-emerald-900/50">{stats.hlsm_version}</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {/* L0 Working */}
        <div className="p-3 rounded-lg bg-zinc-900/50 border border-zinc-800">
          <div className="text-zinc-500 mb-1">L0 WORKING</div>
          <div className="text-lg text-white">{stats.tiers.L0_working.sql_entries || 0}</div>
          <div className="text-[10px] text-zinc-600 truncate">{stats.tiers.L0_working.backend}</div>
        </div>

        {/* L1 Episodic */}
        <div className="p-3 rounded-lg bg-zinc-900/50 border border-zinc-800">
          <div className="text-zinc-500 mb-1">L1 EPISODIC</div>
          <div className="text-lg text-white">{stats.tiers.L1_episodic.entries}</div>
          <div className="text-[10px] text-zinc-600">SQL ENGINE</div>
        </div>

        {/* L2 Semantic */}
        <div className="p-3 rounded-lg bg-emerald-950/10 border border-emerald-900/30">
          <div className="text-emerald-500/70 mb-1 font-bold">L2 SEMANTIC</div>
          <div className="text-lg text-emerald-400">{stats.tiers.L2_semantic.entries === -1 ? 'OFF' : stats.tiers.L2_semantic.entries}</div>
          <div className="text-[10px] text-emerald-900/70">{stats.tiers.L2_semantic.backend}</div>
        </div>
      </div>

      <div className="flex items-center gap-2 text-[10px] text-zinc-600">
        <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
        Consolidation Sweep: Every {stats.consolidation_interval_minutes}m
      </div>
    </div>
  );
};
