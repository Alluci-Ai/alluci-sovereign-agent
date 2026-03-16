
import React, { useState, useEffect, useCallback } from 'react';
import { useDAGRuns } from './hooks/useDAGRuns';
import { useTaskStream } from './hooks/useTaskStream';
import { RunListSidebar } from './components/RunListSidebar';
import { RunDetailHeader } from './components/RunDetailHeader';
import { DAGGraph } from './components/DAGGraph';
import { ObjectiveSubmitBar } from './components/ObjectiveSubmitBar';
import { TaskDetailDrawer } from './components/TaskDetailDrawer';
import { PlanPreviewModal } from './components/PlanPreviewModal';
import { useStore } from '../../store/useStore';
import type { TaskRecord, DAGRun } from './types';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

export const DAGPanel: React.FC = () => {
  const { accessToken } = useStore();
  const { runs, loading: runsLoading, refresh: refreshRuns } = useDAGRuns({ autoRefresh: true });

  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const [selectedRun, setSelectedRun] = useState<DAGRun | null>(null);
  const [initialTasks, setInitialTasks] = useState<TaskRecord[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [previewObjective, setPreviewObjective] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('');

  const { taskStates, streamStatus } = useTaskStream(selectedRunId);

  const loadRunDetail = useCallback(async (runId: number) => {
    try {
      const [runRes, tasksRes] = await Promise.all([
        fetch(`${DAEMON_URL}/api/v1/dag/runs/${runId}`, {
          headers: { Authorization: `Bearer ${accessToken}` },
          credentials: 'include',
        }),
        fetch(`${DAEMON_URL}/api/v1/dag/runs/${runId}/tasks`, {
          headers: { Authorization: `Bearer ${accessToken}` },
          credentials: 'include',
        }),
      ]);
      if (runRes.ok) setSelectedRun(await runRes.json());
      if (tasksRes.ok) {
        const data = await tasksRes.json();
        setInitialTasks(data.tasks || []);
      }
    } catch (e) {
      console.error('[DAGPanel] Failed to load run detail:', e);
    }
  }, [accessToken]);

  useEffect(() => {
    if (selectedRunId) loadRunDetail(selectedRunId);
  }, [selectedRunId, loadRunDetail]);

  // Merge initial tasks with live stream updates
  const mergedTasks: TaskRecord[] = initialTasks.map(t => {
    const live = taskStates[t.task_dag_id];
    if (!live) return t;
    return { ...t, status: live.status, result: live.result, error: live.error,
             start_time: live.start_time, end_time: live.end_time };
  });

  const handleCancel = async () => {
    if (!selectedRunId) return;
    await fetch(`${DAEMON_URL}/api/v1/dag/runs/${selectedRunId}/cancel`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
      credentials: 'include',
    });
    loadRunDetail(selectedRunId);
    refreshRuns();
  };

  const handleObjectiveSubmit = async (objective: string, autonomy: string) => {
    const res = await fetch(`${DAEMON_URL}/api/v1/objective/execute`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ objective, autonomy_level: autonomy }),
    });
    if (res.ok) {
      const data = await res.json();
      refreshRuns();
      if (data.run_id) setSelectedRunId(data.run_id);
    }
  };

  const selectedTaskRecord = mergedTasks.find(t => t.task_dag_id === selectedTaskId) ?? null;

  // Filter runs by status if filter is set
  const filteredRuns = statusFilter
    ? runs.filter(r => r.status === statusFilter)
    : runs;

  return (
    <div data-testid="dag-panel" className="inline-panel-wrapper" style={{ display: 'flex', flexDirection: 'row', gap: 0, padding: 0, height: '100%', overflow: 'hidden' }}>

      {/* Left: Run List Sidebar */}
      <RunListSidebar
        runs={filteredRuns}
        loading={runsLoading}
        selectedRunId={selectedRunId}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        onSelectRun={(id) => { setSelectedRunId(id); setSelectedTaskId(null); }}
        onRefresh={refreshRuns}
      />

      {/* Right: Detail Column */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, position: 'relative' }}>
        {/* Submit Bar — always visible at the top */}
        <ObjectiveSubmitBar
          onSubmit={handleObjectiveSubmit}
          onPreview={setPreviewObjective}
        />

        {selectedRun ? (
          <>
            <RunDetailHeader
              run={selectedRun}
              tasks={mergedTasks}
              streamStatus={streamStatus}
              onCancel={handleCancel}
              onRefresh={() => loadRunDetail(selectedRun.id)}
            />
            <DAGGraph
              tasks={mergedTasks}
              selectedTaskId={selectedTaskId}
              onSelectTask={setSelectedTaskId}
            />
          </>
        ) : (
          <div style={{
            flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexDirection: 'column', gap: 12, opacity: 0.35,
          }}>
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
              <circle cx="12" cy="5" r="2"/><circle cx="5" cy="19" r="2"/><circle cx="19" cy="19" r="2"/>
              <line x1="12" y1="7" x2="5" y2="17"/><line x1="12" y1="7" x2="19" y2="17"/>
            </svg>
            <p style={{ fontSize: 12, fontFamily: 'var(--font-mono)', letterSpacing: '0.08em' }}>
              SELECT_RUN_TO_VISUALIZE
            </p>
          </div>
        )}
      </div>

      {/* Task Detail Drawer */}
      {selectedTaskId && selectedTaskRecord && (
        <TaskDetailDrawer
          task={selectedTaskRecord}
          runId={selectedRunId!}
          onClose={() => setSelectedTaskId(null)}
          onRetry={() => loadRunDetail(selectedRunId!)}
        />
      )}

      {/* Plan Preview Modal */}
      {previewObjective && (
        <PlanPreviewModal
          objective={previewObjective}
          onClose={() => setPreviewObjective(null)}
          onExecute={(obj) => { setPreviewObjective(null); handleObjectiveSubmit(obj, 'SEMI_AUTONOMOUS'); }}
        />
      )}
    </div>
  );
};
