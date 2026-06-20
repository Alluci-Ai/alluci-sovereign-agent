
import React, { useState, useEffect, useCallback } from 'react';
import { TaskItem } from '../types';
import { useStore } from '../store/useStore';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';

export const ConfirmationModal: React.FC<{
    isOpen: boolean;
    title: string;
    message: string;
    onConfirm: () => void;
    onCancel: () => void;
}> = ({ isOpen, title, message, onConfirm, onCancel }) => {
    if (!isOpen) return null;
    return (
        <div style={{
            position: 'fixed', inset: 0, zIndex: 300,
            background: 'rgba(0,0,0,0.4)', backdropFilter: 'blur(6px)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
        }}>
            <div style={{
                width: '100%', maxWidth: 360,
                background: 'var(--bg-elevated)',
                borderRadius: 16, border: '1px solid var(--separator)',
                padding: 24,
                boxShadow: 'var(--glass-shadow-lg)',
            }}>
                <h3 style={{ fontSize: 15, fontWeight: 600, color: 'var(--accent-warm)', marginBottom: 10 }}>{title}</h3>
                <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: 20 }}>{message}</p>
                <div style={{ display: 'flex', gap: 8 }}>
                    <button onClick={onCancel} className="glass-btn" style={{ flex: 1, padding: '8px', fontSize: 13 }}>Cancel</button>
                    <button onClick={onConfirm} className="glass-btn glass-btn--primary" style={{ flex: 1, padding: '8px', fontSize: 13 }}>Execute</button>
                </div>
            </div>
        </div>
    );
};

export const TaskPanel: React.FC<{ onClose: () => void }> = ({ onClose }) => {
    const { activeAgentId } = useStore();
    const [tasks, setTasks] = useState<TaskItem[]>([]);
    const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'completed'>('all');
    const [priorityFilter, setPriorityFilter] = useState<string>('ALL');
    const [timelineFilter, setTimelineFilter] = useState<string>('ALL');
    const [newTaskDesc, setNewTaskDesc] = useState('');
    const [newTaskPriority, setNewTaskPriority] = useState<'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT'>('MEDIUM');
    const [newTaskDue, setNewTaskDue] = useState('');
    const [editingId, setEditingId] = useState<number | null>(null);
    const [confirmTask, setConfirmTask] = useState<TaskItem | null>(null);
    const [showToast, setShowToast] = useState(false);

    const fetchTasks = useCallback(async () => {
        try {
            const params = new URLSearchParams({ status: statusFilter, agent_id: activeAgentId });
            if (priorityFilter !== 'ALL') params.append('priority', priorityFilter);
            if (timelineFilter !== 'ALL') params.append('timeline', timelineFilter);
            const res = await fetch(`${DAEMON_URL}/api/v1/tasks?${params.toString()}`).catch(() => null);
            if (res && res.ok) setTasks(await res.json());
        // eslint-disable-next-line no-empty
        } catch (e) { }
    }, [statusFilter, priorityFilter, timelineFilter, activeAgentId]);

    useEffect(() => { fetchTasks(); }, [fetchTasks]);

    const handleAddTask = async () => {
        if (!newTaskDesc.trim()) return;
        try {
            await fetch(`${DAEMON_URL}/api/v1/tasks?agent_id=${activeAgentId}`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ description: newTaskDesc, completed: false, priority: newTaskPriority, due_date: newTaskDue || null })
            });
            setNewTaskDesc(''); setNewTaskDue(''); setNewTaskPriority('MEDIUM'); fetchTasks();
        } catch (e) { console.error(e); }
    };

    const executeUpdate = async (task: TaskItem, updates: Partial<TaskItem>) => {
        try {
            await fetch(`${DAEMON_URL}/api/v1/tasks/${task.index}?agent_id=${activeAgentId}`, {
                method: 'PUT', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ description: updates.description ?? task.description, completed: updates.completed ?? task.completed, priority: updates.priority ?? task.priority, due_date: updates.due_date ?? task.due_date })
            });
            fetchTasks(); if (editingId === task.index) setEditingId(null);
            if (updates.completed) { setShowToast(true); setTimeout(() => setShowToast(false), 3000); }
        } catch (e) { console.error(e); }
    };

    const handleDeleteTask = async (index: number) => {
        try { await fetch(`${DAEMON_URL}/api/v1/tasks/${index}?agent_id=${activeAgentId}`, { method: 'DELETE' }); fetchTasks(); } catch (e) { console.error(e); }
    };

    const getPriorityStyle = (p: string): React.CSSProperties => {
        switch (p) {
            case 'URGENT': return { color: 'var(--accent-danger)', background: 'var(--accent-danger-tint)', borderColor: 'rgba(255,69,58,0.25)' };
            case 'HIGH': return { color: 'var(--accent-warm)', background: 'rgba(255,159,10,0.12)', borderColor: 'rgba(255,159,10,0.25)' };
            case 'LOW': return { color: 'var(--accent)', background: 'var(--accent-tint)', borderColor: 'rgba(48,209,88,0.25)' };
            default: return { color: 'var(--text-secondary)', background: 'var(--fill-quaternary)', borderColor: 'var(--separator)' };
        }
    };

    return (
        <div style={{
            maxWidth: 720, width: '100%', margin: '0 auto',
            display: 'flex', flexDirection: 'column', height: '100%',
            position: 'relative',
        }}>
            <ConfirmationModal
                isOpen={!!confirmTask}
                title="High Priority Task"
                message={`You are about to mark a ${confirmTask?.priority} priority task as complete. Confirm?`}
                onCancel={() => setConfirmTask(null)}
                onConfirm={() => { if (confirmTask) executeUpdate(confirmTask, { completed: true }); setConfirmTask(null); }}
            />

            {/* Toast */}
            {showToast && (
                <div style={{
                    position: 'absolute', top: 12, right: 12, zIndex: 50,
                    background: 'var(--liquid-accent)', backdropFilter: 'blur(20px) saturate(180%)',
                    WebkitBackdropFilter: 'blur(20px) saturate(180%)',
                    border: '0.5px solid var(--liquid-accent-edge)',
                    color: 'var(--accent)',
                    fontSize: 12, fontWeight: 500, padding: '8px 14px',
                    borderRadius: 8, boxShadow: 'var(--liquid-inner-glow), var(--glass-shadow)',
                    animation: 'nudgeIn 0.3s ease forwards',
                }}>
                    Task resolved ✓
                </div>
            )}

            {/* Header */}
            <div style={{ marginBottom: 20 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                    <h3 style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.02em' }}>Tasks</h3>
                    <button onClick={onClose} className="glass-btn" style={{ display: 'none' }}>✕</button>
                </div>

                {/* Filters */}
                <div style={{
                    display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'flex-end',
                    padding: 14, borderRadius: 12,
                    background: 'var(--fill-quaternary)',
                    border: '1px solid var(--separator)',
                }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                        <span style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Status</span>
                        <div style={{ display: 'flex', gap: 2, background: 'var(--fill-quaternary)', borderRadius: 8, padding: 2, border: '1px solid var(--separator)' }}>
                            {['all', 'active', 'completed'].map(s => (
                                        <button key={s} onClick={() => setStatusFilter(s as 'all' | 'active' | 'completed')} style={{
                                    padding: '4px 10px', borderRadius: 6, fontSize: 11, fontWeight: 500,
                                    border: 'none', cursor: 'pointer',
                                    background: statusFilter === s ? 'var(--glass-bg-hover)' : 'transparent',
                                    color: statusFilter === s ? 'var(--text-primary)' : 'var(--text-tertiary)',
                                    boxShadow: statusFilter === s ? 'var(--glass-shadow)' : 'none',
                                    transition: 'all 0.15s ease', textTransform: 'capitalize',
                                }}>{s}</button>
                            ))}
                        </div>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                        <span style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Priority</span>
                        <select value={priorityFilter} onChange={e => setPriorityFilter(e.target.value)} className="glass-input" style={{ fontSize: 12, padding: '4px 8px', width: 'auto' }}>
                            <option value="ALL">All</option><option value="URGENT">Urgent</option><option value="HIGH">High</option><option value="MEDIUM">Medium</option><option value="LOW">Low</option>
                        </select>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                        <span style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Timeline</span>
                        <select value={timelineFilter} onChange={e => setTimelineFilter(e.target.value)} className="glass-input" style={{ fontSize: 12, padding: '4px 8px', width: 'auto' }}>
                            <option value="ALL">All Time</option><option value="TODAY">Today</option><option value="WEEK">This Week</option><option value="OVERDUE">Overdue</option>
                        </select>
                    </div>
                </div>
            </div>

            {/* Task List */}
            <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 16, paddingRight: 2 }} className="scrollbar-hide">
                {tasks.length === 0 && (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '48px 20px', color: 'var(--text-tertiary)', fontSize: 14 }}>
                        No tasks yet. Add one below.
                    </div>
                )}
                {tasks.map((task) => (
                    <div key={task.index} style={{
                        display: 'flex', alignItems: 'center', gap: 12,
                        padding: '10px 14px',
                        borderRadius: 10,
                        border: `1px solid ${task.completed ? 'var(--separator)' : 'var(--glass-edge)'}`,
                        background: task.completed ? 'var(--fill-quaternary)' : 'var(--glass-bg)',
                        opacity: task.completed ? 0.6 : 1,
                        transition: 'all 0.2s ease',
                    }}>
                        <input
                            type="checkbox" checked={task.completed}
                            onChange={() => {
                                if (!task.completed && (task.priority === 'HIGH' || task.priority === 'URGENT')) setConfirmTask(task);
                                else executeUpdate(task, { completed: !task.completed });
                            }}
                            style={{ width: 16, height: 16, accentColor: 'var(--accent)', cursor: 'pointer', flexShrink: 0 }}
                        />
                        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 3, minWidth: 0 }}>
                            {editingId === task.index ? (
                                <input autoFocus style={{
                                    width: '100%', fontSize: 13, fontFamily: 'var(--font-mono)',
                                    borderBottom: '1px solid var(--accent)', outline: 'none',
                                    background: 'transparent', color: 'var(--text-primary)', padding: '2px 0',
                                }}
                                    defaultValue={task.description}
                                    onBlur={(e) => executeUpdate(task, { description: e.target.value })}
                                    onKeyDown={(e) => e.key === 'Enter' && e.currentTarget.blur()}
                                />
                            ) : (
                                <span onClick={() => setEditingId(task.index)} style={{
                                    fontSize: 13, fontFamily: 'var(--font-mono)', cursor: 'text', color: 'var(--text-primary)',
                                    textDecoration: task.completed ? 'line-through' : 'none',
                                }}>{task.description}</span>
                            )}
                            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                                <span style={{
                                    fontSize: 10, fontWeight: 600, padding: '1px 6px', borderRadius: 4,
                                    border: '1px solid', ...getPriorityStyle(task.priority),
                                }}>{task.priority}</span>
                                {task.due_date && (
                                    <span style={{
                                        fontSize: 11, fontFamily: 'var(--font-mono)',
                                        color: (new Date(task.due_date) < new Date() && !task.completed) ? 'var(--accent-danger)' : 'var(--text-tertiary)',
                                        fontWeight: (new Date(task.due_date) < new Date() && !task.completed) ? 600 : 400,
                                    }}>Due: {task.due_date}</span>
                                )}
                            </div>
                        </div>
                        <div style={{ display: 'flex', gap: 4, alignItems: 'center', opacity: 0.5, transition: 'opacity 0.15s' }}
                            onMouseEnter={e => (e.currentTarget.style.opacity = '1')}
                            onMouseLeave={e => (e.currentTarget.style.opacity = '0.5')}>
                                    <select value={task.priority} onChange={(e) => executeUpdate(task, { priority: e.target.value as "LOW" | "MEDIUM" | "HIGH" | "URGENT" })} className="glass-input" style={{ fontSize: 11, padding: '2px 4px', width: 60 }}>
                                <option value="LOW">Low</option><option value="MEDIUM">Med</option><option value="HIGH">High</option><option value="URGENT">Urg</option>
                            </select>
                            <input type="date" className="glass-input" value={task.due_date || ''} onChange={(e) => executeUpdate(task, { due_date: e.target.value })} style={{ fontSize: 11, padding: '2px 4px', width: 120 }} />
                            <button onClick={() => handleDeleteTask(task.index)} style={{
                                background: 'none', border: 'none', color: 'var(--accent-danger)',
                                cursor: 'pointer', fontSize: 16, padding: '2px 6px',
                            }}>✕</button>
                        </div>
                    </div>
                ))}
            </div>

            {/* Add Task */}
            <div style={{
                display: 'flex', gap: 8, alignItems: 'center',
                padding: 12, borderRadius: 12,
                background: 'var(--fill-quaternary)',
                border: '1px solid var(--separator)',
            }}>
                <select value={newTaskPriority} onChange={(e) => setNewTaskPriority(e.target.value as "LOW" | "MEDIUM" | "HIGH" | "URGENT")} className="glass-input" style={{ width: 70, fontSize: 12, padding: '6px 6px' }}>
                    <option value="LOW">Low</option><option value="MEDIUM">Med</option><option value="HIGH">High</option><option value="URGENT">Urg</option>
                </select>
                <input value={newTaskDesc} onChange={(e) => setNewTaskDesc(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleAddTask()} placeholder="New task..." className="glass-input" style={{ flex: 1, fontSize: 13 }} />
                <input type="date" value={newTaskDue} onChange={(e) => setNewTaskDue(e.target.value)} className="glass-input" style={{ width: 130, fontSize: 12 }} />
                <button onClick={handleAddTask} className="glass-btn glass-btn--primary" style={{ fontSize: 12, padding: '6px 14px', flexShrink: 0 }}>Add</button>
            </div>
        </div>
    );
};
