
import { useState, useEffect, useCallback, useRef } from 'react';
import { useStore } from '../../../store/useStore';
import type { DAGRun } from '../types';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';
const POLL_INTERVAL_MS = 5000;

interface UseDAGRunsOptions {
  status?: string;
  limit?: number;
  autoRefresh?: boolean;
  agent_id?: string;
}

export function useDAGRuns({ status, limit = 20, autoRefresh = true, agent_id = 'executive' }: UseDAGRunsOptions = {}) {
  const { accessToken } = useStore();
  const [runs, setRuns] = useState<DAGRun[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchRuns = useCallback(async (currentOffset = 0, replace = true, isBackgroundPoll = false) => {
    if (!isBackgroundPoll) {
      setLoading(true);
    }
    setError(null);
    try {
      const params = new URLSearchParams({ limit: String(limit), offset: String(currentOffset), agent_id });
      if (status) params.set('status', status);
      const res = await fetch(`${DAEMON_URL}/api/v1/dag/runs?${params}`, {
        headers: { Authorization: `Bearer ${accessToken}` },
        credentials: 'include',
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setRuns(prev => replace ? data.runs : [...prev, ...data.runs]);
      setTotal(data.total);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (e: any) {
      setError(e.message);
    } finally {
      if (!isBackgroundPoll) {
        setLoading(false);
      }
    }
  }, [accessToken, status, limit, agent_id]);

  const refresh = useCallback(() => fetchRuns(0, true, false), [fetchRuns]);

  const loadMore = useCallback(() => {
    const nextOffset = offset + limit;
    setOffset(nextOffset);
    fetchRuns(nextOffset, false, false);
  }, [offset, limit, fetchRuns]);

  useEffect(() => {
    fetchRuns(0, true, false);
    if (autoRefresh) {
      intervalRef.current = setInterval(() => fetchRuns(0, true, true), POLL_INTERVAL_MS);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchRuns, autoRefresh]);

  return { runs, total, loading, error, refresh, loadMore, hasMore: runs.length < total };
}
