
import React, { useRef, useEffect, useCallback, useMemo } from 'react';
import type { TaskRecord } from '../types';

interface Props {
  tasks: TaskRecord[];
  selectedTaskId: string | null;
  onSelectTask: (id: string) => void;
}

const NODE_W = 180, NODE_H = 52, H_GAP = 80, V_GAP = 24, PAD = 32;

const STATUS_COLORS: Record<string, { fill: string; stroke: string; text: string }> = {
  completed: { fill: 'rgba(48,209,88,0.16)',   stroke: 'rgba(48,209,88,0.45)',   text: '#30D158' },
  running:   { fill: 'rgba(255,159,10,0.16)',  stroke: 'rgba(255,159,10,0.45)',  text: '#FF9F0A' },
  pending:   { fill: 'rgba(191,90,242,0.16)',  stroke: 'rgba(191,90,242,0.45)', text: '#BF5AF2' },
  failed:    { fill: 'rgba(255,69,58,0.16)',   stroke: 'rgba(255,69,58,0.45)',   text: '#FF453A' },
  skipped:   { fill: 'rgba(120,120,128,0.12)', stroke: 'rgba(120,120,128,0.30)', text: '#8E8E93' },
};

export function computeLayout(tasks: TaskRecord[]) {
  const layers = new Map<string, number>();
  const sorted = [...tasks];

  let changed = true;
  while (changed) {
    changed = false;
    for (const t of sorted) {
      const deps: string[] = t.args?.dependencies ?? [];
      const maxDepLayer = deps.length > 0
        ? Math.max(-1, ...deps.map(d => layers.get(d) ?? -1))
        : -1;
      const newLayer = maxDepLayer + 1;
      if ((layers.get(t.task_dag_id) ?? -1) !== newLayer) {
        layers.set(t.task_dag_id, newLayer);
        changed = true;
      }
    }
  }

  const byLayer = new Map<number, string[]>();
  for (const [id, layer] of layers) {
    if (!byLayer.has(layer)) byLayer.set(layer, []);
    byLayer.get(layer)!.push(id);
  }

  const positions = new Map<string, { x: number; y: number }>();
  const numLayers = layers.size > 0 ? Math.max(...layers.values()) + 1 : 0;

  for (let l = 0; l < numLayers; l++) {
    const ids = byLayer.get(l) ?? [];
    const x = PAD + l * (NODE_W + H_GAP);
    ids.forEach((id, i) => {
      const y = PAD + i * (NODE_H + V_GAP);
      positions.set(id, { x, y });
    });
  }

  return positions;
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.arcTo(x + w, y, x + w, y + r, r);
  ctx.lineTo(x + w, y + h - r);
  ctx.arcTo(x + w, y + h, x + w - r, y + h, r);
  ctx.lineTo(x + r, y + h);
  ctx.arcTo(x, y + h, x, y + h - r, r);
  ctx.lineTo(x, y + r);
  ctx.arcTo(x, y, x + r, y, r);
  ctx.closePath();
}

export const DAGGraph: React.FC<Props> = ({ tasks, selectedTaskId, onSelectTask }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const positionsRef = useRef<Map<string, { x: number; y: number }>>(new Map());

  const taskMap = useMemo(() => {
    const m = new Map<string, TaskRecord>();
    tasks.forEach(t => m.set(t.task_dag_id, t));
    return m;
  }, [tasks]);

  const positions = useMemo(() => computeLayout(tasks), [tasks]);
  positionsRef.current = positions;

  const { canvasW, canvasH } = useMemo(() => {
    let maxX = 0, maxY = 0;
    for (const { x, y } of positions.values()) {
      maxX = Math.max(maxX, x + NODE_W + PAD);
      maxY = Math.max(maxY, y + NODE_H + PAD);
    }
    return { canvasW: Math.max(maxX, 400), canvasH: Math.max(maxY, 200) };
  }, [positions]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = canvasW * dpr;
    canvas.height = canvasH * dpr;
    canvas.style.width = `${canvasW}px`;
    canvas.style.height = `${canvasH}px`;
    const ctx = canvas.getContext('2d')!;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, canvasW, canvasH);

    // Draw edges
    ctx.lineWidth = 1.5;
    for (const task of tasks) {
      const pos = positions.get(task.task_dag_id);
      if (!pos) continue;
      const deps: string[] = task.args?.dependencies ?? [];
      for (const depId of deps) {
        const depPos = positions.get(depId);
        if (!depPos) continue;
        const x1 = depPos.x + NODE_W, y1 = depPos.y + NODE_H / 2;
        const x2 = pos.x,             y2 = pos.y + NODE_H / 2;
        const mx = (x1 + x2) / 2;
        const depTask = taskMap.get(depId);
        const col = STATUS_COLORS[depTask?.status ?? 'pending'];
        ctx.strokeStyle = col?.stroke ?? 'rgba(255,255,255,0.12)';
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.bezierCurveTo(mx, y1, mx, y2, x2, y2);
        ctx.stroke();
        // Arrowhead
        ctx.fillStyle = col?.stroke ?? 'rgba(255,255,255,0.12)';
        ctx.beginPath();
        ctx.moveTo(x2, y2);
        ctx.lineTo(x2 - 8, y2 - 4);
        ctx.lineTo(x2 - 8, y2 + 4);
        ctx.closePath();
        ctx.fill();
      }
    }

    // Draw nodes
    for (const task of tasks) {
      const pos = positions.get(task.task_dag_id);
      if (!pos) continue;
      const col = STATUS_COLORS[task.status] ?? STATUS_COLORS.pending;
      const isSelected = task.task_dag_id === selectedTaskId;

      ctx.fillStyle = col.fill;
      roundRect(ctx, pos.x, pos.y, NODE_W, NODE_H, 10);
      ctx.fill();

      ctx.strokeStyle = isSelected ? col.text : col.stroke;
      ctx.lineWidth = isSelected ? 2 : 1;
      roundRect(ctx, pos.x, pos.y, NODE_W, NODE_H, 10);
      ctx.stroke();

      ctx.fillStyle = col.text;
      ctx.font = `600 10px monospace`;
      ctx.textAlign = 'left';
      const actionLabel = (task.action || 'unknown').toUpperCase().slice(0, 16);
      ctx.fillText(actionLabel, pos.x + 12, pos.y + 17);

      ctx.fillStyle = 'rgba(235,235,245,0.45)';
      ctx.font = `400 9px monospace`;
      const idLabel = task.task_dag_id.slice(0, 22);
      ctx.fillText(idLabel, pos.x + 12, pos.y + 32);

      ctx.fillStyle = col.text;
      ctx.beginPath();
      ctx.arc(pos.x + NODE_W - 14, pos.y + 14, 4, 0, Math.PI * 2);
      ctx.fill();

      if (task.status === 'running') {
        ctx.strokeStyle = 'rgba(255,159,10,0.4)';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.arc(pos.x + NODE_W - 14, pos.y + 14, 7, 0, Math.PI * 2);
        ctx.stroke();
      }
    }
  }, [tasks, positions, selectedTaskId, taskMap, canvasW, canvasH]);

  useEffect(() => { draw(); }, [draw]);

  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current!.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    for (const task of tasks) {
      const pos = positionsRef.current.get(task.task_dag_id);
      if (!pos) continue;
      if (mx >= pos.x && mx <= pos.x + NODE_W && my >= pos.y && my <= pos.y + NODE_H) {
        onSelectTask(task.task_dag_id);
        return;
      }
    }
  };

  return (
    <div className="dag-graph-container scrollbar-hide">
      {tasks.length === 0 ? (
        <div className="dag-empty-label" style={{ paddingTop: 60 }}>
          NO_TASKS_IN_RUN
        </div>
      ) : (
        <canvas
          ref={canvasRef}
          onClick={handleClick}
          style={{ cursor: 'pointer', display: 'block' }}
        />
      )}
    </div>
  );
};
