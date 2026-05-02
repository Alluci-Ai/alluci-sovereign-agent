import React, { useMemo } from 'react';
import type { TaskRecord } from '../types';

interface Props {
  tasks: TaskRecord[];
  selectedTaskId: string | null;
  onSelectTask: (id: string) => void;
}

const STATUS_COLORS: Record<string, string> = {
  completed: 'rgba(48,209,88,0.45)',
  running: 'rgba(255,159,10,0.45)',
  pending: 'rgba(191,90,242,0.45)',
  failed: 'rgba(255,69,58,0.45)',
  skipped: 'rgba(120,120,128,0.30)'
};

export const GanttChart: React.FC<Props> = ({ tasks, selectedTaskId, onSelectTask }) => {
  const { minTime, maxTime, sortedTasks } = useMemo(() => {
    let min = Infinity;
    let max = -Infinity;
    
    tasks.forEach(t => {
      const start = t.start_time ? new Date(t.start_time).getTime() : Date.now();
      const end = t.end_time ? new Date(t.end_time).getTime() : (t.status === 'running' ? Date.now() : start + 1000);
      if (start < min) min = start;
      if (end > max) max = end;
    });

    if (min === Infinity) {
      min = Date.now() - 60000;
      max = Date.now();
    }
    
    // Add 5% padding to the timeline
    const padding = Math.max((max - min) * 0.05, 1000);
    min -= padding;
    max += padding;

    // Sort by start time, then DAG ID
    const sorted = [...tasks].sort((a, b) => {
      const tA = a.start_time ? new Date(a.start_time).getTime() : Infinity;
      const tB = b.start_time ? new Date(b.start_time).getTime() : Infinity;
      if (tA === tB) return a.task_dag_id.localeCompare(b.task_dag_id);
      return tA - tB;
    });

    return { minTime: min, maxTime: max, sortedTasks: sorted };
  }, [tasks]);

  const durationStr = (t: TaskRecord) => {
    if (!t.start_time) return '—';
    const start = new Date(t.start_time).getTime();
    const end = t.end_time ? new Date(t.end_time).getTime() : Date.now();
    const sec = Math.max(0, (end - start) / 1000);
    return `${sec.toFixed(1)}s`;
  };

  return (
    <div className="dag-graph-container scrollbar-hide p-4 overflow-y-auto bg-zinc-950/30">
      {tasks.length === 0 ? (
        <div className="flex items-center justify-center h-full opacity-30 text-xs font-mono uppercase tracking-widest">
          NO_TASKS_IN_RUN
        </div>
      ) : (
        <div className="relative min-w-[600px] h-full flex flex-col gap-2 pb-8">
          {sortedTasks.map(t => {
            const start = t.start_time ? new Date(t.start_time).getTime() : minTime;
            const end = t.end_time ? new Date(t.end_time).getTime() : (t.status === 'running' ? maxTime : start + 1000);
            
            const totalRange = maxTime - minTime;
            const leftPerc = Math.max(0, ((start - minTime) / totalRange) * 100);
            let widthPerc = Math.max(0.5, ((end - start) / totalRange) * 100);
            
            if (leftPerc + widthPerc > 100) widthPerc = 100 - leftPerc;

            const isSelected = selectedTaskId === t.task_dag_id;
            const bgCol = STATUS_COLORS[t.status] || STATUS_COLORS.pending;

            return (
              <div 
                key={t.task_dag_id}
                onClick={() => onSelectTask(t.task_dag_id)}
                className={`relative h-10 w-full group cursor-pointer transition-all border-b border-zinc-800/30 ${isSelected ? 'bg-white/5' : 'hover:bg-white/5'}`}
              >
                {/* Left Label */}
                <div className="absolute left-2 top-0 bottom-0 flex items-center w-40 z-10 overflow-hidden text-ellipsis whitespace-nowrap">
                  <div className="flex flex-col">
                    <span className="text-[11px] font-bold text-zinc-300">{(t.action || 'Unknown').toUpperCase()}</span>
                    <span className="text-[9px] font-mono text-zinc-500">{t.task_dag_id.substring(0, 16)}</span>
                  </div>
                </div>

                {/* Timeline Bar */}
                <div className="absolute left-48 right-16 top-0 bottom-0 py-2">
                  <div className="relative w-full h-full bg-zinc-900/30 rounded overflow-hidden">
                    <div 
                      className="absolute top-0 bottom-0 rounded-sm shadow-sm transition-all duration-300"
                      style={{ 
                        left: `${leftPerc}%`, 
                        width: `${widthPerc}%`, 
                        background: bgCol,
                        boxShadow: isSelected ? `0 0 10px ${bgCol}` : 'none'
                      }}
                    />
                  </div>
                </div>

                {/* Right Duration */}
                <div className="absolute right-2 top-0 bottom-0 flex items-center justify-end w-12 z-10 text-[10px] font-mono text-zinc-400">
                  {durationStr(t)}
                </div>
              </div>
            );
          })}
          
          {/* Timeline axis (decorative) */}
          <div className="absolute bottom-2 left-48 right-16 border-t border-zinc-700/50 flex justify-between text-[8px] font-mono text-zinc-600 pt-1 px-1">
            <span>START</span>
            <span>TIMELINE_ELAPSED</span>
            <span>END</span>
          </div>
        </div>
      )}
    </div>
  );
};
