
import { useState, useEffect, useRef, useCallback } from 'react';
import { useStore } from '../../../store/useStore';
import type { LiveTaskState, StreamStatus } from '../types';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

export function useTaskStream(runId: number | null) {
  const { accessToken } = useStore();
  const [taskStates, setTaskStates] = useState<Record<string, LiveTaskState>>({});
  const [streamStatus, setStreamStatus] = useState<StreamStatus>('idle');
  const sourceRef = useRef<EventSource | null>(null);
  const retryCountRef = useRef(0);

  const disconnect = useCallback(() => {
    sourceRef.current?.close();
    sourceRef.current = null;
    setStreamStatus('idle');
  }, []);

  useEffect(() => {
    if (!runId) {
      disconnect();
      return;
    }

    setStreamStatus('connecting');
    setTaskStates({});
    retryCountRef.current = 0;

    const url = `${DAEMON_URL}/api/dag/runs/${runId}/stream?token=${encodeURIComponent(accessToken || '')}`;
    const source = new EventSource(url);
    sourceRef.current = source;

    source.onopen = () => setStreamStatus('live');

    source.onmessage = (event) => {
      try {
        const update: LiveTaskState = JSON.parse(event.data);
        setTaskStates(prev => ({ ...prev, [update.task_dag_id]: update }));
      } catch { /* malformed event — skip */ }
    };

    source.addEventListener('done', () => {
      setStreamStatus('done');
      source.close();
    });

    source.onerror = () => {
      retryCountRef.current += 1;
      if (retryCountRef.current >= 3) {
        setStreamStatus('error');
        source.close();
      }
    };

    return () => {
      source.close();
      sourceRef.current = null;
    };
  }, [runId, accessToken, disconnect]);

  return { taskStates, streamStatus, disconnect };
}
