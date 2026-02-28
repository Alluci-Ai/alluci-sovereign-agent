import React, { useState, useEffect, useRef, useCallback, useLayoutEffect } from 'react';
import {
  AlluciGeminiService,
  decode,
  decodeAudioData,
  FilePart,
  GroundingSource
} from './geminiService';
import { AlluciSovereignService, SovereignCallbacks } from './sovereignService';
import { AuditLedger, SovereignSecurityManager, SkillVerifier, generateSystemPrompt, BioVault, clamp01 } from './alluciCore';
import { ACEController, ACENudge } from './aceController';
import LiveCanvas, { CanvasNode } from './LiveCanvas';
import { AuditEntry, PersonalityTraits, Connection, AuthType, SkillManifest, ApiManifoldKeys, AutonomyLevel, SoulPreferences, SoulHumor, SoulConciseness, SoulManifest, GraphNode, GraphEdge } from './types';
import SoulPreferencesPanel from './SoulPreferencesPanel';
import SkillBuilderWizard from './SkillBuilderWizard';
import ApiWizard from './ApiWizard';
import { QRCodeCanvas } from 'qrcode.react';

// [ CONFIGURATION_NODE ]
const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

declare global {
  interface Window {
    google: any;
  }
}

const KNOWN_PROVIDERS = {
  llm: [
    { id: 'openai', label: 'OpenAI (GPT-5.1 / o1)' },
    { id: 'anthropic', label: 'Anthropic (Claude 4.5 / 4.6)' },
    { id: 'googleCloud', label: 'Google Cloud (Gemini 3)' },
    { id: 'groq', label: 'Groq (High-Speed)' },
    { id: 'deepseek', label: 'DeepSeek (R1 / V3)' }
  ],
  audio: [
    { id: 'openaiRealtime', label: 'OpenAI Realtime API' },
    { id: 'elevenLabsAgents', label: 'ElevenLabs (Agents API)' },
    { id: 'retellAi', label: 'Retell AI (Telephony)' },
    { id: 'inworldAi', label: 'Inworld AI (Character)' }
  ],
  music: [
    { id: 'suno', label: 'Suno API (Vocals/Melody)' },
    { id: 'elevenLabsMusic', label: 'ElevenLabs Music API' },
    { id: 'stableAudio', label: 'Stable Audio (Stability AI)' },
    { id: 'soundverse', label: 'Soundverse (functional)' },
    { id: 'udio', label: 'Udio (High Fidelity)' },
    { id: 'googleLyria', label: 'Google (Lyria 3)' }
  ],
  image: [
    { id: 'openaiDalle', label: 'OpenAI (DALL·E 3)' },
    { id: 'falAi', label: 'Fal.ai (Fast Diffusion)' },
    { id: 'midjourney', label: 'Midjourney (Alpha API)' },
    { id: 'adobeFirefly', label: 'Adobe Firefly API' },
    { id: 'googleNanoBanana', label: 'Google (Nano Banana)' },
    { id: 'seedance', label: 'Seedance 2.0' }
  ],
  video: [
    { id: 'runway', label: 'Runway (Gen-4.5)' },
    { id: 'luma', label: 'Luma Dream Machine' },
    { id: 'heygen', label: 'HeyGen / Synthesia' },
    { id: 'livepeer', label: 'Livepeer (Decentralized)' },
    { id: 'googleVeo', label: 'Google (Veo)' },
    { id: 'googleGenie', label: 'Google (Genie)' }
  ]
};

// [ VALIDATION_LOGIC ]
const validateApiKey = (provider: string, key: string): boolean => {
  if (!key) return true; // Allow empty to clear
  const k = key.trim();
  if (k.length < 8) return false; // Too short to be real for any modern API

  // Pattern Matching for Known Families
  if (provider.startsWith('openai')) return k.startsWith('sk-');
  if (provider.startsWith('google')) return k.startsWith('AIza'); // Google Cloud / Gemini Keys
  if (provider.startsWith('elevenLabs')) return /^[a-fA-F0-9]{32}$/.test(k) || k.startsWith('sk_'); // Usually 32 hex chars

  // Specific Provider Logic
  switch (provider) {
    case 'anthropic': return k.startsWith('sk-ant');
    case 'groq': return k.startsWith('gsk_');
    case 'deepseek': return k.startsWith('sk-'); // DeepSeek often uses sk- prefix similar to OpenAI
    case 'retellAi': return k.startsWith('key_');
    case 'falAi': return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(k) || k.startsWith('key-');
    case 'runway': return k.startsWith('runway_') || k.length > 25; // Heuristic
    case 'stableAudio': return k.length > 30; // Long token
    case 'livepeer': return k.length > 20;
    case 'adobeFirefly': return k.startsWith('ec_') || k.length > 20; // Often client IDs or JWTs
    case 'inworldAi': return k.length > 30;
    case 'heygen': return k.length > 20;
    // For others (Midjourney, Suno, Luma, Seedance, etc), ensure decent length entropy
    default: return k.length > 15;
  }
};

// Export PolytopeIdentity for reuse in sub-panels
export const PolytopeIdentity: React.FC<{ color?: string; size?: number; active?: boolean }> = ({ color = "#91D65F", size = 48, active }) => {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="none" className={`transition-all duration-700 ${active ? 'scale-110 drop-shadow-[0_0_12px_rgba(145,214,95,0.4)]' : 'scale-100 opacity-60'}`}>
      <path d="M11 26L89 8L45 42L11 26Z" fill={color} fillOpacity="1" />
      <path d="M89 8L74 92L45 42L89 8Z" fill={color} fillOpacity="0.8" />
      <path d="M74 92L11 26L45 42L74 92Z" fill={color} fillOpacity="0.6" />
    </svg>
  );
};

// --- Types for Task Management ---
interface TaskItem {
  index: number;
  description: string;
  completed: boolean;
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';
  due_date: string | null;
}

const ExecutionTimeline: React.FC<{ isProcessing: boolean }> = ({ isProcessing }) => {
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (!isProcessing) {
      setStep(0);
      return;
    }
    const interval = setInterval(() => {
      setStep(s => (s < 4 ? s + 1 : s));
    }, 1500); // Simulate progress for the visualizer
    return () => clearInterval(interval);
  }, [isProcessing]);

  if (!isProcessing && step === 0) return null;

  const steps = [
    { label: "PARSING_INTENT", status: step > 0 ? 'COMPLETE' : 'ACTIVE' },
    { label: "DAG_CONSTRUCTION", status: step > 1 ? 'COMPLETE' : step === 1 ? 'ACTIVE' : 'PENDING' },
    { label: "SOVEREIGN_EXECUTION", status: step > 2 ? 'COMPLETE' : step === 2 ? 'ACTIVE' : 'PENDING' },
    { label: "CRITIC_REVIEW", status: step > 3 ? 'COMPLETE' : step === 3 ? 'ACTIVE' : 'PENDING' }
  ];

  return (
    <div className="w-full bg-zinc/5 border-y border-sovereign/10 p-2 flex justify-between items-center gap-2 mb-4 animate-in fade-in slide-in-from-top-2">
      {steps.map((s, i) => (
        <div key={i} className="flex flex-col items-center flex-1">
          <div className={`h-1 w-full mb-1 transition-all duration-500 ${s.status === 'COMPLETE' ? 'bg-agent' : s.status === 'ACTIVE' ? 'bg-tension animate-pulse' : 'bg-zinc/20'}`} />
          <span className={`text-[6px] baunk-style tracking-tighter ${s.status === 'ACTIVE' ? 'text-black' : 'text-zinc opacity-50'}`}>{s.label}</span>
        </div>
      ))}
    </div>
  );
};

// ... ConfirmationModal, TaskPanel, AuthPortal, RealtimeBarVisualizer, CircularVisualizer (Same as previous) ...
const ConfirmationModal: React.FC<any> = ({ isOpen, title, message, onConfirm, onCancel }) => {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-[300] bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200">
      <div className="facet w-full max-w-sm bg-white p-6 border-2 border-tension shadow-2xl">
        <h3 className="baunk-style text-[12px] text-tension mb-4 tracking-widest">{title}</h3>
        <p className="text-[10px] font-mono leading-relaxed mb-6">{message}</p>
        <div className="flex gap-2">
          <button onClick={onCancel} className="flex-1 baunk-style text-[9px] py-3 border border-zinc/20 hover:bg-zinc/5">
            [ CANCEL ]
          </button>
          <button onClick={onConfirm} className="flex-1 baunk-style text-[9px] py-3 bg-tension text-white hover:bg-black transition-colors">
            [ EXECUTE ]
          </button>
        </div>
      </div>
    </div>
  );
};

const TaskPanel: React.FC<{ onClose: () => void }> = ({ onClose }) => {
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
      const params = new URLSearchParams({ status: statusFilter });
      if (priorityFilter !== 'ALL') params.append('priority', priorityFilter);
      if (timelineFilter !== 'ALL') params.append('timeline', timelineFilter);
      const res = await fetch(`${DAEMON_URL}/tasks?${params.toString()}`).catch(() => null);
      if (res && res.ok) setTasks(await res.json());
    } catch (e) { }
  }, [statusFilter, priorityFilter, timelineFilter]);

  useEffect(() => { fetchTasks(); }, [fetchTasks]);

  const handleAddTask = async () => {
    if (!newTaskDesc.trim()) return;
    try {
      await fetch(`${DAEMON_URL}/tasks`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description: newTaskDesc, completed: false, priority: newTaskPriority, due_date: newTaskDue || null })
      });
      setNewTaskDesc(''); setNewTaskDue(''); setNewTaskPriority('MEDIUM'); fetchTasks();
    } catch (e) { console.error(e); }
  };

  const executeUpdate = async (task: TaskItem, updates: Partial<TaskItem>) => {
    try {
      await fetch(`${DAEMON_URL}/tasks/${task.index}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description: updates.description ?? task.description, completed: updates.completed ?? task.completed, priority: updates.priority ?? task.priority, due_date: updates.due_date ?? task.due_date })
      });
      fetchTasks(); if (editingId === task.index) setEditingId(null);
      if (updates.completed) { setShowToast(true); setTimeout(() => setShowToast(false), 3000); }
    } catch (e) { console.error(e); }
  };

  const handleDeleteTask = async (index: number) => {
    try { await fetch(`${DAEMON_URL}/tasks/${index}`, { method: 'DELETE' }); fetchTasks(); } catch (e) { console.error(e); }
  };

  const getPriorityColor = (p: string) => {
    switch (p) {
      case 'URGENT': return 'text-red-600 bg-red-100 border-red-200';
      case 'HIGH': return 'text-tension bg-orange-100 border-orange-200';
      case 'LOW': return 'text-agent bg-green-100 border-green-200';
      default: return 'text-zinc bg-zinc/5 border-zinc/20';
    }
  };

  return (
    <div className="flex flex-col h-full bg-white relative">
      <ConfirmationModal isOpen={!!confirmTask} title="HIGH_PRIORITY_INTERVENTION" message={`You are about to mark a ${confirmTask?.priority} priority task as complete. This action will update the sovereign ledger. Confirm execution?`} onCancel={() => setConfirmTask(null)} onConfirm={() => { if (confirmTask) executeUpdate(confirmTask, { completed: true }); setConfirmTask(null); }} />
      {showToast && <div className="absolute top-4 right-4 bg-agent text-white text-[9px] baunk-style px-4 py-3 shadow-lg z-50 animate-in slide-in-from-right duration-300">[ TASK_RESOLVED_SUCCESSFULLY ]</div>}
      <div className="flex flex-col border-b border-sovereign/10 pb-6 mb-6 gap-4">
        <div className="flex justify-between items-center"><h3 className="baunk-style text-xl tracking-[0.3em]">TASK_MANIFOLD_REGISTRY</h3><button onClick={onClose} className="md:hidden text-lg">✕</button></div>
        <div className="flex flex-wrap gap-4 p-4 bg-zinc/5 border border-zinc/10">
          <div className="flex flex-col gap-1"><span className="text-[6px] baunk-style opacity-40">STATUS</span><div className="flex gap-1">{['all', 'active', 'completed'].map(s => (<button key={s} onClick={() => setStatusFilter(s as any)} className={`px-2 py-1 text-[8px] baunk-style border ${statusFilter === s ? 'bg-sovereign text-white border-sovereign' : 'bg-white text-zinc border-zinc/20'}`}>{s}</button>))}</div></div>
          <div className="flex flex-col gap-1"><span className="text-[6px] baunk-style opacity-40">PRIORITY</span><select value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)} className="bg-white border border-zinc/20 text-[9px] font-mono p-1 h-6 outline-none"><option value="ALL">ALL_LEVELS</option><option value="URGENT">URGENT</option><option value="HIGH">HIGH</option><option value="MEDIUM">MEDIUM</option><option value="LOW">LOW</option></select></div>
          <div className="flex flex-col gap-1"><span className="text-[6px] baunk-style opacity-40">TIMELINE</span><select value={timelineFilter} onChange={(e) => setTimelineFilter(e.target.value)} className="bg-white border border-zinc/20 text-[9px] font-mono p-1 h-6 outline-none"><option value="ALL">ALL_TIME</option><option value="TODAY">TODAY</option><option value="WEEK">THIS_WEEK</option><option value="OVERDUE">OVERDUE</option></select></div>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto scrollbar-hide space-y-3 mb-6">
        {tasks.map((task) => (
          <div key={task.index} className={`flex items-center gap-4 p-3 border group transition-all duration-300 ${task.completed ? 'bg-zinc/5 border-zinc/10 opacity-60' : 'bg-white border-sovereign/10 hover:border-sovereign shadow-sm hover:shadow-md'}`}>
            <input type="checkbox" checked={task.completed} onChange={() => { if (!task.completed && (task.priority === 'HIGH' || task.priority === 'URGENT')) setConfirmTask(task); else executeUpdate(task, { completed: !task.completed }); }} className="accent-sovereign w-4 h-4 cursor-pointer" />
            <div className="flex-1 flex flex-col gap-1">
              {editingId === task.index ? (<input autoFocus className="w-full text-[10px] font-mono border-b border-sovereign outline-none bg-transparent" defaultValue={task.description} onBlur={(e) => executeUpdate(task, { description: e.target.value })} onKeyDown={(e) => e.key === 'Enter' && e.currentTarget.blur()} />) : (<span onClick={() => setEditingId(task.index)} className={`text-[10px] font-mono cursor-text ${task.completed ? 'line-through' : ''}`}>{task.description}</span>)}
              <div className="flex gap-2 items-center"><span className={`text-[6px] baunk-style px-1.5 py-0.5 border ${getPriorityColor(task.priority)}`}>{task.priority}</span>{task.due_date && (<span className={`text-[7px] font-mono opacity-60 ${new Date(task.due_date) < new Date() && !task.completed ? 'text-red-500 font-bold' : ''}`}>DUE: {task.due_date}</span>)}</div>
            </div>
            <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity items-center"><select value={task.priority} onChange={(e) => executeUpdate(task, { priority: e.target.value as any })} className="text-[8px] bg-transparent border border-zinc/20 outline-none cursor-pointer p-1"><option value="LOW">LOW</option><option value="MEDIUM">MED</option><option value="HIGH">HIGH</option><option value="URGENT">URG</option></select><input type="date" className="text-[8px] bg-transparent border border-zinc/20 outline-none w-24 p-1" value={task.due_date || ''} onChange={(e) => executeUpdate(task, { due_date: e.target.value })} /><button onClick={() => handleDeleteTask(task.index)} className="text-red-400 hover:text-red-600 font-bold px-2">✕</button></div>
          </div>
        ))}
      </div>
      <div className="p-4 bg-zinc/5 border border-sovereign/10 flex gap-3 items-center shadow-inner">
        <select value={newTaskPriority} onChange={(e) => setNewTaskPriority(e.target.value as any)} className="bg-white border border-zinc/20 text-[9px] font-mono p-2 outline-none h-10 w-20"><option value="LOW">LOW</option><option value="MEDIUM">MED</option><option value="HIGH">HIGH</option><option value="URGENT">URG</option></select>
        <input value={newTaskDesc} onChange={(e) => setNewTaskDesc(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleAddTask()} placeholder="NEW_OBJECTIVE_VECTOR..." className="flex-1 bg-white border border-zinc/20 text-[10px] font-mono p-2 outline-none h-10" />
        <input type="date" value={newTaskDue} onChange={(e) => setNewTaskDue(e.target.value)} className="bg-white border border-zinc/20 text-[9px] font-mono p-2 outline-none h-10 w-28" />
        <button onClick={handleAddTask} className="bg-sovereign text-white baunk-style text-[9px] px-6 h-10 hover:bg-agent transition-colors">[ ADD ]</button>
      </div>
    </div>
  );
};

const AuthPortal: React.FC<any> = ({ connection, onComplete, onCancel }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [verusChallenge, setVerusChallenge] = useState<any>(null);
  const [polling, setPolling] = useState(false);

  const isVerus = connection.id === 'verus';

  const fetchVerusChallenge = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`${DAEMON_URL}/auth/verusid/challenge`);
      if (res.ok) {
        setVerusChallenge(await res.json());
        setPolling(true);
      }
    } catch (e) { console.error("Verus Challenge Failed", e); }
    finally { setIsLoading(false); }
  };

  useEffect(() => {
    if (isVerus && !verusChallenge) {
      fetchVerusChallenge();
    }
  }, [isVerus]);

  // Polling for VerusID Callback (In a real mobile app, the mobile app hits the callback)
  // For simulation/dev, we can poll the daemon to see if the challenge was consumed
  useEffect(() => {
    if (!polling || !verusChallenge) return;
    const interval = setInterval(async () => {
      // Logic to check if challenge is resolved
      // In this specific architecture, the backend issues JWT on callback.
      // For this UI, we might wait for the user to manually 'confirm' or 
      // have the backend signal completion via a status endpoint.
    }, 2000);
    return () => clearInterval(interval);
  }, [polling, verusChallenge]);

  const handleAuth = () => {
    if (isVerus) return; // Managed by QR flow
    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
      setIsVerifying(true);
      setTimeout(() => {
        onComplete(`active_${connection.id.toLowerCase()}_session`, `https://api.dicebear.com/7.x/identicon/svg?seed=${connection.id}`);
      }, 1500);
    }, 1200);
  };

  return (
    <div className="fixed inset-0 z-[250] flex items-center justify-center bg-black/80 backdrop-blur-xl p-4">
      <div className="facet w-full max-w-md bg-white p-6 md:p-10 border-2 shadow-2xl animate-in zoom-in-95 duration-300">
        <div className="h-1.5 w-full flex absolute top-0 left-0"><div className="h-full bg-sovereign flex-1" /><div className="h-full bg-agent flex-1" /><div className="h-full bg-tension flex-1" /><div className="h-full bg-flux flex-1" /></div>
        <div className="flex justify-between items-center border-b border-sovereign pb-6 mb-8 mt-2">
          <div className="flex flex-col">
            <span className="baunk-style text-[12px] md:text-[14px] tracking-[0.4em]">{isVerus ? 'VERUSID_SOVEREIGN_LINK' : 'SECURE_HANDSHAKE'}</span>
            <span className="text-[8px] font-mono opacity-40 uppercase">{connection.name} Manifold</span>
          </div>
          <button onClick={onCancel} className="text-zinc hover:text-black transition-colors px-2 py-1">✕</button>
        </div>

        <div className="flex flex-col gap-6">
          {isVerus ? (
            <div className="flex flex-col items-center gap-6">
              {isLoading ? (
                <div className="h-48 flex items-center justify-center animate-pulse text-zinc text-[10px] baunk-style">
                  [ GENERATING_VDXF_CHALLENGE... ]
                </div>
              ) : verusChallenge ? (
                <>
                  <div className="p-4 bg-white border-4 border-black shadow-lg">
                    <QRCodeCanvas
                      value={JSON.stringify(verusChallenge)}
                      size={180}
                      level="H"
                      includeMargin={true}
                    />
                  </div>
                  <div className="text-center">
                    <h3 className="text-[10px] font-bold baunk-style mb-2">SCAN WITH VERUS MOBILE</h3>
                    <p className="text-[9px] opacity-60 font-mono leading-relaxed max-w-[280px]">
                      Identity: <span className="text-black font-bold">{verusChallenge.identity_hint || "Self-Sovereign"}</span><br />
                      Nonce: <span className="opacity-40">{verusChallenge.nonce.slice(0, 16)}...</span>
                    </p>
                  </div>
                  <div className="w-full flex flex-col gap-2">
                    <div className="h-1 w-full bg-zinc/10 overflow-hidden">
                      <div className="h-full bg-sovereign animate-progress-fast" style={{ width: '100%' }} />
                    </div>
                    <span className="text-[7px] font-mono text-center animate-pulse lowercase">Waiting for blockchain-verifiable signature...</span>
                  </div>
                </>
              ) : (
                <div className="text-red-500 text-[10px] baunk-style">[ ERROR: DAEMON_UNREACHABLE ]</div>
              )}
            </div>
          ) : (
            <>
              {!isVerifying ? (
                <>
                  <div className="text-center mb-4">
                    <div className="w-16 h-16 bg-zinc/5 rounded-full flex items-center justify-center mx-auto mb-4 border border-zinc/10">
                      <span className="text-2xl font-bold">{connection.name.slice(0, 1)}</span>
                    </div>
                    <h3 className="text-[12px] font-sans font-bold">Initiate {connection.name} Bridge</h3>
                    <p className="text-[10px] opacity-60 max-w-[280px] mx-auto mt-2 leading-relaxed">
                      Connecting via <span className="text-agent font-bold">{connection.authType}</span> protocol.
                      Enforced isolation and end-to-end encryption.
                    </p>
                  </div>
                  <button disabled={isLoading} onClick={handleAuth} className={`w-full p-4 baunk-style text-[10px] flex items-center justify-center gap-3 transition-all ${isLoading ? 'bg-zinc text-white animate-pulse' : 'bg-sovereign text-white hover:bg-agent'}`}>
                    {isLoading ? '[ NEGOTIATING... ]' : '[ AUTHORIZE_ONE_TOUCH ]'}
                  </button>
                </>
              ) : (
                <div className="flex flex-col items-center gap-6 py-4">
                  <div className="relative">
                    <div className="w-20 h-20 rounded-full border-4 border-agent animate-ping absolute opacity-20" />
                    <div className="w-20 h-20 rounded-full border-2 border-agent flex items-center justify-center">
                      <svg className="w-10 h-10 text-agent animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M12 11c0 3.517-1.009 6.799-2.753 9.571m-3.44-2.04l.054-.09A13.916 13.916 0 008 11a4 4 0 118 0c0 1.017-.07 2.019-.203 3m-2.118 6.844A21.88 21.88 0 0015.171 17m3.839 1.132c.645-2.266.99-4.659.99-7.132A8 8 0 008 4.07M3 15.364c.64-1.319 1-2.8 1-4.364 0-1.457.39-2.823 1.07-4" />
                      </svg>
                    </div>
                  </div>
                  <div className="text-[10px] font-mono text-center tracking-widest text-agent uppercase animate-pulse">Verification_In_Progress</div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

const RealtimeBarVisualizer: React.FC<{
  value: number;
  label: string;
  color: string;
  height?: number;
  onChange?: (val: number) => void
}> = ({ value, label, color, height = 4, onChange }) => {
  const segments = 24;
  const activeSegments = Math.floor(value * segments);

  const handleClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!onChange) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const newValue = Math.max(0, Math.min(1, x / rect.width));
    onChange(newValue);
  };

  return (
    <div className="flex flex-col gap-1.5 w-full group cursor-pointer" onClick={handleClick}>
      <div className="flex justify-between items-center baunk-style text-[6px] tracking-widest opacity-60 group-hover:opacity-100 transition-opacity">
        <span>{label}</span>
        <span className="font-mono">{(value * 100).toFixed(0)}%</span>
      </div>
      <div className="flex gap-[1px]" style={{ height: `${height}px` }}>
        {Array.from({ length: segments }).map((_, i) => (
          <div
            key={i}
            className="flex-1 transition-all duration-500 ease-out"
            style={{
              backgroundColor: i < activeSegments ? color : 'rgba(161, 161, 161, 0.1)',
              boxShadow: i < activeSegments ? `0 0 4px ${color}44` : 'none'
            }}
          />
        ))}
      </div>
    </div>
  );
};

const CircularVisualizer: React.FC<{ stream: MediaStream | null; active: boolean; accent: string }> = ({ stream, active, accent }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    if (!stream || !active) return;
    const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 24000 });
    const analyser = audioCtx.createAnalyser();
    const source = audioCtx.createMediaStreamSource(stream);
    source.connect(analyser);
    analyser.fftSize = 256;
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    let animationId: number;
    const draw = () => {
      animationId = requestAnimationFrame(draw);
      analyser.getByteFrequencyData(dataArray);
      const { width, height } = canvas;
      const centerX = width / 2;
      const centerY = height / 2;
      const radius = Math.min(width, height) / 3.5;
      ctx.clearRect(0, 0, width, height);
      ctx.strokeStyle = '#000000';
      ctx.lineWidth = 0.5;
      ctx.beginPath(); ctx.arc(centerX, centerY, radius, 0, Math.PI * 2); ctx.stroke();
      for (let i = 0; i < bufferLength; i++) {
        const barHeight = (dataArray[i] / 255) * radius * 0.7;
        const angle = (i / bufferLength) * Math.PI * 2;
        ctx.strokeStyle = accent;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(centerX + Math.cos(angle) * radius, centerY + Math.sin(angle) * radius);
        ctx.lineTo(centerX + Math.cos(angle) * (radius + barHeight), centerY + Math.sin(angle) * (radius + barHeight));
        ctx.stroke();
      }
    };
    draw();
    return () => { cancelAnimationFrame(animationId); audioCtx.close(); };
  }, [stream, active, accent]);
  return <canvas ref={canvasRef} width={400} height={400} className="w-full h-full object-contain" />;
};

interface Message {
  text: string;
  isUser: boolean;
  sources?: GroundingSource[];
  timestamp: string;
}

interface PendingAttachment extends FilePart {
  name: string;
}

type MobileView = 'terminal' | 'vision' | 'system';

const MobileNav: React.FC<{ active: MobileView; setActive: (v: MobileView) => void }> = ({ active, setActive }) => (
  <nav className="md:hidden flex h-14 border-t border-sovereign bg-white z-40 shrink-0 shadow-[0_-5px_20px_rgba(0,0,0,0.05)]">
    <button onClick={() => setActive('vision')} className={`flex-1 flex flex-col items-center justify-center gap-1 baunk-style text-[8px] transition-colors ${active === 'vision' ? 'bg-sovereign text-white' : 'text-zinc hover:bg-zinc/5'}`}><span>[ VISION ]</span></button>
    <button onClick={() => setActive('terminal')} className={`flex-1 flex flex-col items-center justify-center gap-1 baunk-style text-[8px] transition-colors border-x border-sovereign/10 ${active === 'terminal' ? 'bg-sovereign text-white' : 'text-zinc hover:bg-zinc/5'}`}><span>[ TERMINAL ]</span></button>
    <button onClick={() => setActive('system')} className={`flex-1 flex flex-col items-center justify-center gap-1 baunk-style text-[8px] transition-colors ${active === 'system' ? 'bg-sovereign text-white' : 'text-zinc hover:bg-zinc/5'}`}><span>[ SYSTEM ]</span></button>
  </nav>
);

const MobileMenu: React.FC<{ isOpen: boolean; onClose: () => void; onAction: (action: string) => void }> = ({ isOpen, onClose, onAction }) => {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-[60] bg-white/95 backdrop-blur-xl flex flex-col p-8 gap-6 animate-in fade-in duration-200">
      <div className="flex justify-between items-center border-b border-sovereign pb-4"><span className="baunk-style text-lg tracking-widest">[ MENU ]</span><button onClick={onClose} className="text-xl p-2">✕</button></div>
      <div className="flex flex-col gap-3 text-center overflow-y-auto">
        <button onClick={() => onAction('audit')} className="alce-button baunk-style text-xs py-4 border-b border-zinc/10">[ AUDIT_LOG ]</button>
        <button onClick={() => onAction('files')} className="alce-button baunk-style text-xs py-4 border-b border-zinc/10">[ FILES ]</button>
        <button onClick={() => onAction('tasks')} className="alce-button baunk-style text-xs py-4 border-b border-zinc/10">[ TASKS ]</button>
        <button onClick={() => onAction('skills')} className="alce-button baunk-style text-xs py-4 border-b border-zinc/10">[ SKILLS ]</button>
        <button onClick={() => onAction('bridges')} className="alce-button baunk-style text-xs py-4 border-b border-zinc/10">[ BRIDGES ]</button>
        <button onClick={() => onAction('api')} className="alce-button baunk-style text-xs py-4 border-b border-zinc/10">[ API_KEYS ]</button>
        <button onClick={() => onAction('soul')} className="alce-button baunk-style text-xs py-4">[ SOUL_CORE ]</button>
      </div>
    </div>
  );
};

const HeartbeatIndicator: React.FC<{ active: boolean }> = ({ active }) => {
  const [pulse, setPulse] = useState(false);
  useEffect(() => { if (!active) return; const interval = setInterval(() => { setPulse(true); setTimeout(() => setPulse(false), 200); }, 2000); return () => clearInterval(interval); }, [active]);
  if (!active) return null;
  return (
    <div className="flex items-center gap-1 opacity-60"><div className={`w-1.5 h-1.5 bg-tension rounded-full transition-all duration-300 ${pulse ? 'scale-150 shadow-[0_0_8px_#FF7D00]' : 'scale-100'}`} /><span className="text-[6px] font-mono tracking-wider">HEARTBEAT_ACTIVE</span></div>
  );
};

const App: React.FC = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [daemonStatus, setDaemonStatus] = useState<'ONLINE' | 'OFFLINE'>('OFFLINE');
  const [harmonicStatus, setHarmonicStatus] = useState<string>('Inactive');

  const [mobileView, setMobileView] = useState<MobileView>('terminal');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isDriveOpen, setIsDriveOpen] = useState(false);
  const [isAuditOpen, setIsAuditOpen] = useState(false);
  const [isPreferencesOpen, setIsPreferencesOpen] = useState(false);
  const [isSoulOpen, setIsSoulOpen] = useState(false);
  const [isApiManifoldOpen, setIsApiManifoldOpen] = useState(false);
  const [isTaskPanelOpen, setIsTaskPanelOpen] = useState(false);
  const [showSkillWizard, setShowSkillWizard] = useState(false);
  const [isApiWizardOpen, setIsApiWizardOpen] = useState(false);

  const [activeAuth, setActiveAuth] = useState<Connection | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<SkillManifest | null>(null);
  const [skills, setSkills] = useState<SkillManifest[]>([]);

  const [userEmotional, setUserEmotional] = useState(0.4); // Valence: 0 (Neg) - 1 (Pos)
  const [userPhysical, setUserPhysical] = useState(0.3); // Arousal: 0 (Calm) - 1 (Excited)
  const [userCognitive, setUserCognitive] = useState(0.6); // Load: 0 (Bored) - 1 (Overloaded)

  const [agentEmotional, setAgentEmotional] = useState(0.2);
  const [agentPhysical, setAgentPhysical] = useState(0.5);
  const [agentCognitive, setAgentCognitive] = useState(0.9);
  const [valenceCurvature, setValenceCurvature] = useState(0.3);
  const [manifoldIntegrity, setManifoldIntegrity] = useState(0.12);

  const [transcriptions, setTranscriptions] = useState<Message[]>([]);
  const [textInput, setTextInput] = useState("");
  const [attachments, setAttachments] = useState<PendingAttachment[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [audioStream, setAudioStream] = useState<MediaStream | null>(null);
  const [auditLog, setAuditLog] = useState<AuditEntry[]>([]);

  const [masterKeyInput, setMasterKeyInput] = useState("");
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [authStatus, setAuthStatus] = useState<string | null>(null);

  const [addingServiceCategory, setAddingServiceCategory] = useState<keyof ApiManifoldKeys | null>(null);
  const [newServiceName, setNewServiceName] = useState("");
  const [newServiceKey, setNewServiceKey] = useState("");

  // Store the authoritative base manifest to allow for dynamic adaptation
  const [baseManifest, setBaseManifest] = useState<SoulManifest | null>(null);

  const [apiKeys, setApiKeys] = useState<ApiManifoldKeys>(() => {
    return {
      llm: { openai: '', anthropic: '', googleCloud: '', groq: '', deepseek: '' },
      audio: { openaiRealtime: '', elevenLabsAgents: '', retellAi: '', inworldAi: '' },
      music: { suno: '', elevenLabsMusic: '', stableAudio: '', soundverse: '', udio: '', googleLyria: '' },
      image: { openaiDalle: '', falAi: '', midjourney: '', adobeFirefly: '', googleNanoBanana: '', seedance: '' },
      video: { runway: '', luma: '', heygen: '', livepeer: '', googleVeo: '', googleGenie: '' }
    };
  });

  const [activeNudges, setActiveNudges] = useState<ACENudge[]>([]);
  const [activeMainView, setActiveMainView] = useState<'TERMINAL' | 'CANVAS'>('TERMINAL');
  const [canvasNodes, setCanvasNodes] = useState<CanvasNode[]>([
    { id: 'initial_node', type: 'TEXT', content: 'SYSTEM READY: A2UI_PROTOCOL_ACTIVE', x: 50, y: 150 }
  ]);
  const aceControllerRef = useRef(new ACEController());
  const bioVaultRef = useRef(new BioVault());

  const clearNudge = (id: string) => {
    setActiveNudges(prev => prev.filter(n => n.id !== id));
  };

  useEffect(() => {
    // Initial load from secure vault
    const loadVaultKeys = async () => {
      try {
        const res = await fetch(`${DAEMON_URL}/api/vault/keys`, { credentials: 'include' });
        if (res.ok) {
          const keys = await res.json();
          if (keys && Object.keys(keys).length > 0) {
            setApiKeys(prev => ({ ...prev, ...keys }));
          }
        }
      } catch (e) {
        console.error("Vault retrieval failed. Local-first fallback active.");
      }
    };
    loadVaultKeys();
  }, []);

  useEffect(() => {
    // [ ACE_FLOW_SENSING_LOOP ]
    const nudge = aceControllerRef.current.computeNudge(userEmotional, userPhysical, userCognitive);
    if (nudge) {
      setActiveNudges(prev => [...prev, nudge]);
      geminiServiceRef.current?.audit.addEntry("ACE_FLOW_NUDGE_ISSUED", { type: nudge.type, message: nudge.message });
      refreshAuditLog();
    }

    // [ BIO_VAULT_ENCLAVE_SYNC ]
    bioVaultRef.current.ingestTelemetry({ v: userEmotional, a: userPhysical, l: userCognitive });
  }, [userEmotional, userPhysical, userCognitive]);

  const handleSaveApiKeys = async (newKeys: ApiManifoldKeys) => {
    setApiKeys(newKeys);
    try {
      const res = await fetch(`${DAEMON_URL}/api/vault/keys`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newKeys),
        credentials: 'include'
      });
      if (res.ok) {
        geminiServiceRef.current?.audit.addEntry("API_MANIFOLD_PERSISTED", { status: "SUCCESS" });
        refreshAuditLog();
      }
    } catch (e) {
      console.error("Vault persistence failed.");
    }
  };

  const [connections, setConnections] = useState<Connection[]>([
    { id: 'icloud', name: 'iCloud', status: 'DISCONNECTED', type: 'WORKSPACE', authType: 'TOKEN', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: false },
    { id: 'imessage', name: 'iMessage', status: 'DISCONNECTED', type: 'MESSAGING', authType: 'SECURE_TUNNEL', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'iwatch', name: 'iWatch', status: 'DISCONNECTED', type: 'MESSAGING', authType: 'SECURE_TUNNEL', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'iphone', name: 'iPhone', status: 'DISCONNECTED', type: 'MESSAGING', authType: 'SECURE_TUNNEL', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'wa', name: 'WhatsApp', status: 'DISCONNECTED', type: 'MESSAGING', authType: 'QR_SYNC', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'tg', name: 'Telegram', status: 'DISCONNECTED', type: 'MESSAGING', authType: 'TOKEN', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'sl', name: 'Slack', status: 'DISCONNECTED', type: 'MESSAGING', authType: 'OAUTH2', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'dc', name: 'Discord', status: 'DISCONNECTED', type: 'MESSAGING', authType: 'OAUTH2', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'sg', name: 'Signal', status: 'DISCONNECTED', type: 'MESSAGING', authType: 'TOKEN', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'ig', name: 'Instagram', status: 'DISCONNECTED', type: 'MESSAGING', authType: 'OAUTH2', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'fb', name: 'Facebook', status: 'DISCONNECTED', type: 'MESSAGING', authType: 'OAUTH2', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'x', name: 'X', status: 'DISCONNECTED', type: 'MESSAGING', authType: 'OAUTH2', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'mt', name: 'MS Teams', status: 'DISCONNECTED', type: 'WORKSPACE', authType: 'OAUTH2', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'webchat', name: 'WebChat', status: 'DISCONNECTED', type: 'MESSAGING', authType: 'WEB_SESSION', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: false },
    { id: 'wechat', name: 'WeChat', status: 'DISCONNECTED', type: 'MESSAGING', authType: 'QR_SYNC', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'gm', name: 'Gmail', status: 'DISCONNECTED', type: 'WORKSPACE', authType: 'OAUTH2', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'gd', name: 'G-Drive', status: 'DISCONNECTED', type: 'WORKSPACE', authType: 'OAUTH2', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'verus', name: 'VerusID', status: 'DISCONNECTED', type: 'WORKSPACE', authType: 'IDENTITY_LINK', autonomyLevel: AutonomyLevel.SOVEREIGN, isEncrypted: true }
  ]);

  const skillVerifier = useRef(new SkillVerifier());
  const audioContextRef = useRef<AudioContext | null>(null);
  const nextStartTimeRef = useRef<number>(0);
  const sourcesRef = useRef<Set<AudioBufferSourceNode>>(new Set());
  const geminiServiceRef = useRef<AlluciGeminiService | null>(null);
  const sovereignServiceRef = useRef<AlluciSovereignService | null>(null);
  const [sovereignMode, setSovereignMode] = useState(true); // Default to Sovereign for privacy-first
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const frameIntervalRef = useRef<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let mounted = true;
    const checkDaemon = async () => {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 2000);
        const res = await fetch(`${DAEMON_URL}/system/status`, { signal: controller.signal });
        clearTimeout(timeoutId);
        if (mounted) {
          if (res.ok) {
            const data = await res.json();
            setDaemonStatus('ONLINE');
            if (data.harmonic_status) setHarmonicStatus(data.harmonic_status);
          } else {
            setDaemonStatus('OFFLINE');
          }
        }
      } catch (e) {
        if (mounted) setDaemonStatus('OFFLINE');
      }
    };
    checkDaemon();
    const interval = setInterval(checkDaemon, 5000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const fetchSkills = useCallback(async () => {
    const core = skillVerifier.current.getManifests();
    try {
      // Cookie-based auth automatically included via credentials: 'include'
      const res = await fetch(`${DAEMON_URL}/skills`, {
        credentials: 'include'
      });
      if (res.ok) {
        const custom = await res.json();
        const combined = [...core];
        custom.forEach((c: SkillManifest) => {
          if (!combined.find(k => k.id === c.id)) combined.push(c);
        });
        setSkills(combined);
        return;
      }
    } catch (e) { }
    setSkills(core);
  }, []);

  useEffect(() => { fetchSkills(); }, [fetchSkills, isSettingsOpen]);

  useEffect(() => {
    audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 24000 });
    geminiServiceRef.current = new AlluciGeminiService();

    // Attempt to load full SoulManifest for the service on init
    const loadSoul = async () => {
      // Cookie-based auth
      try {
        const res = await fetch(`${DAEMON_URL}/soul/manifest`, { credentials: 'include' });
        if (res.ok) {
          const manifest = await res.json();
          geminiServiceRef.current?.setPersonality(manifest);
          setBaseManifest(manifest);
          return;
        }
      } catch (e) { }
    };
    loadSoul();

    geminiServiceRef.current?.setSkills(skillVerifier.current.getActiveSkills());

    return () => {
      geminiServiceRef.current?.disconnect();
      if (frameIntervalRef.current) clearInterval(frameIntervalRef.current);
    };
  }, []);

  useEffect(() => {
    if (skills.length > 0) {
      geminiServiceRef.current?.setSkills(skills.filter(s => s.verified));
    }
  }, [skills]);

  // [ AFFECTIVE_ADAPTATION_LOOP ]
  // Dynamically adjusts personality vectors based on real-time biometric state.
  useEffect(() => {
    if (!baseManifest || !geminiServiceRef.current) return;

    // Deep clone to create a temporary runtime persona
    const dynamicManifest = JSON.parse(JSON.stringify(baseManifest)) as SoulManifest;
    const prefs = dynamicManifest.preferences;

    // 1. Valence Modulation (Emotional State)
    // Low Valence (< 0.4) indicates sadness/distress -> Increase Empathy, Warm up Tone
    if (userEmotional < 0.4) {
      prefs.empathy = Math.min(1.0, prefs.empathy + 0.4);
      prefs.tone = Math.max(0.0, prefs.tone - 0.3); // Softer
    } else if (userEmotional > 0.8) {
      // High Valence -> User is happy, match energy
      prefs.creativity = Math.min(1.0, prefs.creativity + 0.2);
    }

    // 2. Cognitive Load Modulation
    // High Load (> 0.7) -> Reduce verbosity, enforce conciseness
    if (userCognitive > 0.7) {
      prefs.conciseness = SoulConciseness.CONCISE;
      prefs.verbosity = Math.max(0.0, prefs.verbosity - 0.4);
    } else if (userCognitive < 0.3) {
      // Low Load -> User is bored/relaxed, be expressive/educational
      prefs.conciseness = SoulConciseness.EXPRESSIVE;
      prefs.verbosity = Math.min(1.0, prefs.verbosity + 0.2);
    }

    // 3. Arousal Modulation (Physical Energy)
    // High Arousal (> 0.8) + Low Valence (< 0.4) = Stress/Anger -> De-escalate
    if (userPhysical > 0.8 && userEmotional < 0.4) {
      prefs.tone = 0.2; // Very casual/calm/soothing
      prefs.empathy = 1.0; // Max empathy
      prefs.assertiveness = 0.3; // Less directive, more supportive
    }

    // Push adapted state to the AI service
    geminiServiceRef.current.setPersonality(dynamicManifest);

  }, [userEmotional, userPhysical, userCognitive, baseManifest]);

  // Auto-scroll effect
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcriptions, isProcessing]);

  const refreshAuditLog = useCallback(() => {
    if (geminiServiceRef.current) setAuditLog(geminiServiceRef.current.audit.getEntries());
  }, []);

  const handleAudioOutput = useCallback(async (base64Audio: string) => {
    if (!audioContextRef.current) return;
    const ctx = audioContextRef.current;
    nextStartTimeRef.current = Math.max(nextStartTimeRef.current, ctx.currentTime);
    const buffer = await decodeAudioData(decode(base64Audio), ctx, 24000, 1);
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(ctx.destination);
    source.start(nextStartTimeRef.current);
    nextStartTimeRef.current += buffer.duration;
    sourcesRef.current.add(source);
    setValenceCurvature(prev => clamp01(prev + 0.15));
  }, []);

  const handleConnect = async () => {
    if (isConnected) {
      geminiServiceRef.current?.disconnect();
      sovereignServiceRef.current?.disconnect();
      setIsConnected(false);
      setAudioStream(null);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      setAudioStream(stream);

      // Create an AudioWorkletNode for real-time audio processing
      const audioContext = audioContextRef.current!;
      await audioContext.audioWorklet.addModule('/audio-processor.js');
      const audioWorkletNode = new AudioWorkletNode(audioContext, 'audio-processor');
      const sourceNode = audioContext.createMediaStreamSource(stream);
      sourceNode.connect(audioWorkletNode);
      audioWorkletNode.connect(audioContext.destination);

      audioWorkletNode.port.onmessage = (e) => {
        const inputData = e.data;
        if (sovereignMode && sovereignServiceRef.current) {
          sovereignServiceRef.current.sendAudio(inputData);
        } else if (geminiServiceRef.current) {
          geminiServiceRef.current.sendRealtimeInput(inputData);
        }
      };

      if (sovereignMode) {
        if (!sovereignServiceRef.current) sovereignServiceRef.current = new AlluciSovereignService();

        const callbacks: SovereignCallbacks = {
          onOpen: () => { setIsConnected(true); refreshAuditLog(); },
          onClose: () => setIsConnected(false),
          onAudioOutput: (b64) => {
            const audio = new Audio("data:audio/wav;base64," + b64);
            audio.play();
          },
          onTranscription: (text, isUser) => {
            setTranscriptions(prev => {
              const last = prev[prev.length - 1];
              if (last && last.isUser === isUser) {
                const updated = [...prev];
                updated[updated.length - 1] = { ...last, text: last.text + text };
                return updated;
              }
              return [...prev.slice(-49), { text, isUser, timestamp: new Date().toISOString() }];
            });
            refreshAuditLog();
          },
          onLLMChunk: (chunk) => {
            setTranscriptions(prev => {
              const last = prev[prev.length - 1];
              if (last && !last.isUser) {
                const updated = [...prev];
                updated[updated.length - 1] = { ...last, text: last.text + chunk };
                return updated;
              }
              return [...prev.slice(-49), { text: chunk, isUser: false, timestamp: new Date().toISOString() }];
            });
          },
          onInterrupted: () => {
            sourcesRef.current.forEach(s => s.stop());
            sourcesRef.current.clear();
            nextStartTimeRef.current = 0;
          },
          onError: (err) => console.error("Sovereign Error:", err),
          onGroundingSources: (sources) => {
            setTranscriptions(prev => {
              const next = [...prev];
              for (let i = next.length - 1; i >= 0; i--) {
                if (!next[i].isUser) {
                  next[i].sources = sources;
                  break;
                }
              }
              return next;
            });
          },
          onCanvasManifest: (node) => {
            setCanvasNodes(prev => [...prev, { ...node, id: `node_${Date.now()}` }]);
            setActiveMainView('CANVAS'); // Auto-switch to showcase the manifest
            geminiServiceRef.current?.audit.addEntry("A2UI_MANIFEST_RECEIVED", { type: node.type });
            refreshAuditLog();
          }
        };
        await sovereignServiceRef.current.connect(callbacks);
      } else {
        // Cloud Gemini Flow
        if (!geminiServiceRef.current) geminiServiceRef.current = new AlluciGeminiService();
        geminiServiceRef.current.setConnections(connections);
        geminiServiceRef.current.setSkills(skills.filter(s => s.verified));

        await geminiServiceRef.current.connect({
          onAudioOutput: handleAudioOutput,
          onTranscription: (text, isUser) => {
            setTranscriptions(prev => {
              const last = prev[prev.length - 1];
              if (last && last.isUser === isUser) {
                const updated = [...prev];
                updated[updated.length - 1] = { ...last, text: last.text + text };
                return updated;
              }
              return [...prev.slice(-49), { text, isUser, timestamp: new Date().toISOString() }];
            });
            refreshAuditLog();
          }
        });
      }
    } catch (err) {
      console.error("Connection failed:", err);
      setIsConnected(false);
    }
  };

  // ... (Auth helpers, camera toggle, command submit, file handling ... same as original)

  const startAuthFlow = (conn: Connection) => {
    if (conn.status === 'CONNECTED') {
      setConnections(prev => prev.map(c => c.id === conn.id ? { ...c, status: 'DISCONNECTED', accountAlias: undefined, profileImg: undefined } : c));
      return;
    }
    setActiveAuth(conn);
  };

  const handleAuthComplete = (alias: string, profileImg?: string) => {
    if (!activeAuth) return;
    const connId = activeAuth.id;
    setConnections(prev => prev.map(c => c.id === connId ? { ...c, status: 'CONNECTED', accountAlias: alias, profileImg } : c));
    setActiveAuth(null);
  };

  const handleDaemonLogin = async () => {
    setIsAuthenticating(true);
    setAuthStatus(null);
    try {
      const res = await fetch(`${DAEMON_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: masterKeyInput }),
        credentials: 'include'
      });
      if (res.ok) {
        setAuthStatus("SUCCESS: Sovereign Identity Verified.");
        setMasterKeyInput("");
      } else {
        setAuthStatus("FAILURE: Invalid Key.");
      }
    } catch (e) {
      setAuthStatus("ERROR: Daemon Unreachable.");
    } finally {
      setIsAuthenticating(false);
    }
  };

  const toggleCamera = async () => {
    if (isCameraActive) {
      setIsCameraActive(false);
      (videoRef.current?.srcObject as MediaStream)?.getTracks().forEach(t => t.stop());
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setIsCameraActive(true);
        frameIntervalRef.current = window.setInterval(() => {
          if (canvasRef.current && isConnected) {
            const ctx = canvasRef.current.getContext('2d');
            ctx?.drawImage(videoRef.current!, 0, 0, 320, 240);
            geminiServiceRef.current?.sendVideoFrame(canvasRef.current.toDataURL('image/jpeg', 0.5).split(',')[1]);
          }
        }, 1500);
      }
    } catch (err) { console.error(err); }
  };

  const handleCommandSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!textInput.trim() && attachments.length === 0) return;
    if (isProcessing) return;

    const currentText = textInput;
    const currentAttachments = [...attachments];

    setTranscriptions(prev => [...prev, { text: currentText, isUser: true, timestamp: new Date().toISOString() }]);
    setTextInput("");
    setAttachments([]);
    setIsProcessing(true);

    try {
      if (geminiServiceRef.current) {
        const responseText = await geminiServiceRef.current.processMultimodal(currentText, currentAttachments);
        setTranscriptions(prev => [...prev, { text: responseText, isUser: false, timestamp: new Date().toISOString() }]);

        if (isConnected) {
          await geminiServiceRef.current.speak(responseText, handleAudioOutput);
        }
      }
    } catch (err) {
      console.error(err);
      setTranscriptions(prev => [...prev, { text: "[ ERROR ]: Communication manifold disrupted.", isUser: false, timestamp: new Date().toISOString() }]);
    } finally {
      setIsProcessing(false);
      refreshAuditLog();
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    const newAttachments: PendingAttachment[] = [];
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const reader = new FileReader();
      const base64Promise = new Promise<string>((resolve) => {
        reader.onload = () => resolve((reader.result as string).split(',')[1]);
      });
      reader.readAsDataURL(file);
      const data = await base64Promise;
      newAttachments.push({ name: file.name, data, mimeType: file.type });
    }
    setAttachments(prev => [...prev, ...newAttachments]);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const removeAttachment = (idx: number) => {
    setAttachments(prev => prev.filter((_, i) => i !== idx));
  };

  const handleToggleSkill = (id: string) => {
    setSkills(prev => prev.map(s =>
      s.id === id ? { ...s, verified: !s.verified } : s
    ));
  };

  const handleDeleteSkill = async (id: string) => {
    // Cookie-based auth
    try {
      await fetch(`${DAEMON_URL}/skills/${id}`, {
        method: 'DELETE',
        credentials: 'include'
      });
      fetchSkills();
    } catch (e) { console.error(e); }
  };

  const handleMobileMenuAction = (action: string) => {
    setIsMobileMenuOpen(false);
    switch (action) {
      case 'audit': setIsAuditOpen(true); refreshAuditLog(); break;
      case 'files': setIsDriveOpen(true); break;
      case 'tasks': setIsTaskPanelOpen(true); break;
      case 'skills': setIsSettingsOpen(true); break;
      case 'bridges': setIsPreferencesOpen(true); break;
      case 'api': setIsApiManifoldOpen(true); break;
      case 'soul': setIsSoulOpen(true); break;
    }
  };

  const handleSaveApiKeysLocal = (newKeys: ApiManifoldKeys) => {
    handleSaveApiKeys(newKeys);
    setIsApiWizardOpen(false);
  };

  // Callback to sync personality/soul manifest from IdentityForge to Runtime
  const handleManifestUpdate = (newManifest: SoulManifest) => {
    geminiServiceRef.current?.setPersonality(newManifest);
    setBaseManifest(newManifest);
    // Optionally trigger a log or notification
    geminiServiceRef.current?.audit.addEntry("SOUL_MANIFEST_UPDATED", { hash: "new_state_injected" });
    refreshAuditLog();
  };

  const accentColor = isConnected ? '#91D65F' : '#A1A1A1';

  const groupedConnections = {
    'APPLE_ECOSYSTEM': connections.filter(c => ['icloud', 'imessage', 'iwatch', 'iphone'].includes(c.id)),
    'SOCIAL_MANIFOLD': connections.filter(c => ['wa', 'tg', 'dc', 'sg', 'ig', 'fb', 'x'].includes(c.id)),
    'ENTERPRISE_CORE': connections.filter(c => ['sl', 'mt', 'gm', 'gd', 'webchat', 'wechat'].includes(c.id)),
    'VERUS_IDENTITY': connections.filter(c => ['verus'].includes(c.id))
  };

  const copyText = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const getFormattedTime = (iso: string) => {
    try {
      return new Date(iso).toLocaleString('en-US', {
        month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
      });
    } catch (e) { return iso; }
  };

  return (
    <div className="h-[100dvh] w-screen overflow-hidden bg-white flex flex-col md:grid md:grid-cols-12 md:gap-[2px] md:p-[2px] simplicial-grid">
      {activeAuth && <AuthPortal connection={activeAuth} onComplete={handleAuthComplete} onCancel={() => setActiveAuth(null)} />}
      <MobileMenu isOpen={isMobileMenuOpen} onClose={() => setIsMobileMenuOpen(false)} onAction={handleMobileMenuAction} />

      <header className="facet col-span-full h-14 md:h-16 flex items-center px-4 md:px-6 justify-between z-50 border-b md:border border-sovereign bg-white shrink-0">
        <div className="flex items-center gap-3 md:gap-4"><PolytopeIdentity color={accentColor} size={24} active={isConnected} /><div className="flex flex-col"><h1 className="baunk-style text-[9px] md:text-[10px] tracking-[0.2em] md:tracking-[0.4em]">[ POLYTOPE ] v4.3</h1><span className="text-[6px] font-mono opacity-30 uppercase tracking-tighter hidden md:block">Autonomous_Executive_Manifold</span></div><div className="ml-4 hidden md:block"><HeartbeatIndicator active={daemonStatus === 'ONLINE'} /></div></div>
        <div className="hidden md:flex items-center gap-4">
          <button onClick={() => { setIsAuditOpen(true); refreshAuditLog(); }} className="alce-button text-[8px] baunk-style hidden lg:block">[ AUDIT ]</button>
          <button onClick={() => setIsDriveOpen(!isDriveOpen)} className="alce-button text-[8px] baunk-style hidden lg:block">[ FILES ]</button>
          <button onClick={() => setIsTaskPanelOpen(true)} className="alce-button text-[8px] baunk-style">[ TASKS ]</button>
          <button onClick={() => setIsSettingsOpen(!isSettingsOpen)} className="alce-button text-[8px] baunk-style">[ SKILLS ]</button>
          <button onClick={() => setIsPreferencesOpen(true)} className="alce-button text-[8px] baunk-style">[ BRIDGES ]</button>
          <button onClick={() => setIsApiWizardOpen(true)} className="alce-button text-[8px] baunk-style">[ API ]</button>
          <button onClick={() => setIsSoulOpen(true)} className="alce-button text-[8px] baunk-style">[ SOUL ]</button>
          <div className="flex bg-zinc/10 rounded-full p-1 scale-90">
            <button
              onClick={() => setSovereignMode(false)}
              className={`px-3 py-1 rounded-full text-[8px] baunk-style transition-all ${!sovereignMode ? 'bg-agent text-white shadow-lg' : 'opacity-40 hover:opacity-100'}`}
            >
              GEMINI_CLOUD
            </button>
            <button
              onClick={() => setSovereignMode(true)}
              className={`px-3 py-1 rounded-full text-[8px] baunk-style transition-all ${sovereignMode ? 'bg-tension text-white shadow-lg' : 'opacity-40 hover:opacity-100'}`}
            >
              SOVEREIGN_LOCAL
            </button>
          </div>
          <button onClick={handleConnect} className={`alce-button text-[9px] baunk-style px-6 ${isConnected ? 'text-tension' : 'text-agent'}`}>{isConnected ? '[ SLEEP ]' : '[ AWAKEN ]'}</button>
        </div>
        <div className="flex md:hidden items-center gap-3"><HeartbeatIndicator active={daemonStatus === 'ONLINE'} /><button onClick={handleConnect} className={`alce-button text-[8px] baunk-style px-3 py-1.5 ${isConnected ? 'text-tension' : 'text-agent'}`}>{isConnected ? '[ SLEEP ]' : '[ AWAKEN ]'}</button><button onClick={() => setIsMobileMenuOpen(true)} className="alce-button baunk-style text-[10px] px-3 py-1.5 border-l border-sovereign">☰</button></div>
      </header>

      <aside className={`md:col-span-3 bg-zinc/5 overflow-y-auto scrollbar-hide md:border-r border-sovereign flex flex-col ${mobileView === 'vision' ? 'flex-1' : 'hidden md:flex'}`}>
        <div className="facet flex-none h-48 md:h-64 lg:h-48 p-4 border-none"><div className="flex-1 bg-white relative border border-sovereign overflow-hidden"><CircularVisualizer stream={audioStream} active={isConnected} accent={accentColor} /><video ref={videoRef} autoPlay playsInline muted className={`absolute inset-0 w-full h-full object-cover grayscale opacity-0 ${isCameraActive ? 'opacity-40' : ''}`} /></div><button onClick={toggleCamera} className="alce-button baunk-style text-[7px] mt-4 w-full">{isCameraActive ? '[ CLOSE_VISION ]' : '[ OPEN_PROBE ]'}</button></div>
        <div className="flex-1 p-6 flex flex-col gap-8 scrollbar-hide bg-white/50 backdrop-blur-sm border-t border-sovereign/10">
          <h3 className="baunk-style text-[8px] opacity-40 border-b border-sovereign pb-1 text-center">Affective_Engine_v4.3</h3>
          <div className="flex flex-col gap-6">
            <div className="space-y-4 bg-zinc/5 p-3 border border-sovereign/5"><span className="baunk-style text-[6px] opacity-30 block mb-1">User_Resonance_Manifold</span>
              <RealtimeBarVisualizer label="Valence (Emotion)" value={userEmotional} color="#000000" onChange={setUserEmotional} />
              <RealtimeBarVisualizer label="Arousal (Physical)" value={userPhysical} color="#FF7D00" onChange={setUserPhysical} />
              <RealtimeBarVisualizer label="Cognitive Load" value={userCognitive} color="#91D65F" onChange={setUserCognitive} />
            </div>
            <div className="space-y-4 bg-agent/5 p-3 border border-agent/10"><span className="baunk-style text-[6px] opacity-30 block mb-1">System_Coherence_Manifold</span><RealtimeBarVisualizer label="System_Coherence" value={agentCognitive} color="#91D65F" /><RealtimeBarVisualizer label="Valence_Curvature" value={valenceCurvature} color="#995CC0" /><RealtimeBarVisualizer label="Manifold_Integrity" value={manifoldIntegrity} color="#FF7D00" /></div>
            <div className="space-y-2 bg-flux/5 p-3 border border-flux/10 animate-in fade-in slide-in-from-bottom-2"><span className="baunk-style text-[6px] opacity-30 block mb-1">Harmonic_State</span><div className="flex justify-between items-center text-[7px] font-mono"><span className="opacity-60">STATUS:</span><span className={`font-bold ${harmonicStatus === 'Stress_Basin' ? 'text-red-500' : harmonicStatus === 'Loop_Detected' ? 'text-tension' : 'text-agent'}`}>{harmonicStatus.toUpperCase()}</span></div></div>
          </div>
        </div>
      </aside>

      <main className={`md:col-span-6 facet relative md:border-none flex flex-col min-h-0 ${mobileView === 'terminal' ? 'flex-1' : 'hidden md:flex'}`}>
        {/* ACE_NUDGE_OVERLAY */}
        {activeNudges.length > 0 && (
          <div className="absolute top-4 left-4 right-4 z-[60] flex flex-col gap-2 pointer-events-none">
            {activeNudges.map(nudge => (
              <div key={nudge.id} className="p-4 bg-white border-2 border-tension shadow-2xl animate-in slide-in-from-top-4 duration-500 pointer-events-auto flex justify-between items-start gap-4">
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-tension animate-pulse" />
                    <span className="baunk-style text-[8px] tracking-[0.2em] text-tension">{nudge.type}_FLOW_INTERVENTION</span>
                  </div>
                  <p className="text-[10px] font-mono leading-relaxed opacity-80">{nudge.message}</p>
                </div>
                <button onClick={() => clearNudge(nudge.id)} className="text-[10px] baunk-style hover:text-tension transition-colors">[ RESOLVED ]</button>
              </div>
            ))}
          </div>
        )}

        {/* VIEW_SWITCHER */}
        <div className="absolute top-4 right-4 z-[50] flex bg-white/50 backdrop-blur-md border border-black/5 rounded-full p-1 scale-90 origin-right">
          <button
            onClick={() => setActiveMainView('TERMINAL')}
            className={`px-4 py-1.5 rounded-full text-[8px] baunk-style transition-all ${activeMainView === 'TERMINAL' ? 'bg-black text-white shadow-md' : 'opacity-40 hover:opacity-100'}`}
          >
            TERMINAL
          </button>
          <button
            onClick={() => setActiveMainView('CANVAS')}
            className={`px-4 py-1.5 rounded-full text-[8px] baunk-style transition-all ${activeMainView === 'CANVAS' ? 'bg-black text-white shadow-md' : 'opacity-40 hover:opacity-100'}`}
          >
            A2UI_CANVAS
          </button>
        </div>

        {activeMainView === 'CANVAS' ? (
          <div className="flex-1 p-4 md:p-8 bg-zinc/5">
            <LiveCanvas nodes={canvasNodes} />
          </div>
        ) : (
          <div ref={scrollContainerRef} className="flex-1 overflow-y-auto p-4 md:p-8 flex flex-col gap-6 md:gap-8 scrollbar-hide bg-white">
            <ExecutionTimeline isProcessing={isProcessing} />
            {transcriptions.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center opacity-5 select-none animate-pulse">
                <PolytopeIdentity color="#000" size={100} />
                <h2 className="baunk-style text-[8px] mt-6 tracking-[1.2em]">EXECUTIVE_SESSION_IDLE</h2>
              </div>
            )}
            {transcriptions.map((t, i) => (
              <div key={i} className={`flex flex-col ${t.isUser ? 'items-end' : 'items-start'} animate-in fade-in slide-in-from-bottom-2 duration-300`}>
                <div className="flex items-center gap-2 mb-1 opacity-40">
                  <span className="text-[6px] baunk-style tracking-widest">{t.isUser ? 'USER_PROJECTION' : 'ALLUCI_EXECUTIVE'}</span>
                  <span className="text-[6px] font-mono">[{getFormattedTime(t.timestamp)}]</span>
                </div>
                <div className={`relative group max-w-[90%] md:max-w-[85%] px-4 md:px-5 py-3 md:py-4 text-[11px] md:text-[12px] border font-mono leading-relaxed ${t.isUser ? 'bg-white border-zinc/20' : 'bg-agent/5 border-agent/20'}`}>
                  {t.text}
                  <button
                    onClick={() => copyText(t.text)}
                    className="absolute -top-3 -right-3 opacity-0 group-hover:opacity-100 transition-opacity bg-white border border-zinc/20 text-[6px] baunk-style px-2 py-1 shadow-sm hover:bg-zinc/5 z-10"
                    title="Copy to Clipboard"
                  >
                    [ COPY ]
                  </button>
                  {t.sources && t.sources.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-agent/10 flex flex-wrap gap-2">
                      <span className="baunk-style text-[6px] opacity-40 w-full mb-1">Grounding_Context_Retrieved</span>
                      {t.sources.map((s, idx) => (
                        <a key={idx} href={s.uri} target="_blank" rel="noopener noreferrer" className="text-[8px] bg-agent/10 hover:bg-agent/30 text-agent px-2 py-1 border border-agent/20 no-underline transition-all uppercase font-bold">
                          {s.title.slice(0, 20)}...
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {isProcessing && <div className="text-[8px] baunk-style text-flux animate-pulse tracking-[0.5em] py-2">ALLUCI_CORE_CALCULATING_TRAJECTORY...</div>}
            <div ref={messagesEndRef} className="h-2 flex-none" />
          </div>
        )}
        <form onSubmit={handleCommandSubmit} className="shrink-0 p-3 md:p-4 border-t border-sovereign bg-zinc/5 flex flex-col gap-2 shadow-[0_-10px_30px_rgba(0,0,0,0.03)] z-10">
          {attachments.length > 0 && (<div className="flex flex-wrap gap-2 mb-1">{attachments.map((file, idx) => (<div key={idx} className="flex items-center gap-2 bg-white border border-sovereign/10 px-3 py-1.5 text-[7px] font-mono group animate-in slide-in-from-left-2"><span className="opacity-40">{file.mimeType.split('/')[0].toUpperCase()}</span><span className="truncate max-w-[150px] font-bold">{file.name}</span><button type="button" onClick={() => removeAttachment(idx)} className="text-tension hover:text-black transition-colors px-1 font-bold">✕</button></div>))}</div>)}
          <div className="flex gap-2 md:gap-3 items-end"><div className="flex gap-1"><button type="button" onClick={() => fileInputRef.current?.click()} title="Ingest Data" className="alce-button baunk-style text-[14px] h-10 w-10 md:h-12 md:w-12 p-0 flex items-center justify-center transition-transform active:scale-95 bg-white">+</button><input type="file" ref={fileInputRef} onChange={handleFileChange} multiple className="hidden" /></div><textarea value={textInput} onChange={(e) => setTextInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleCommandSubmit(e); } }} placeholder="EXECUTIVE_COMMAND..." className="flex-1 bg-white border border-sovereign/10 focus:border-sovereign transition-colors text-xs tracking-widest font-medium p-3 md:p-4 resize-none scrollbar-hide h-10 md:h-12 rounded-none" /><button type="submit" className="alce-button baunk-style text-[9px] md:text-[10px] h-10 md:h-12 px-4 md:px-8 flex items-center justify-center bg-white">[ TRANSMIT ]</button></div>
        </form>
      </main >

      <aside className={`md:col-span-3 p-4 md:p-6 bg-zinc/5 overflow-hidden border-l border-sovereign flex flex-col gap-6 ${mobileView === 'system' ? 'flex-1' : 'hidden md:flex'}`}>
        <h3 className="baunk-style text-[8px] opacity-40 border-b border-sovereign pb-1 text-center">Audit_Chain_v4.3</h3>
        <div className="flex-1 overflow-y-auto scrollbar-hide flex flex-col gap-4 text-[7px]">{auditLog.slice(0, 15).map((e, i) => (<div key={i} className="flex flex-col border-l-2 border-sovereign/10 pl-3 py-2 bg-white/30 mb-1 animate-in slide-in-from-right-2"><span className="opacity-40 font-mono text-[6px] mb-1">{e.timestamp}</span><span className="font-bold uppercase tracking-widest text-[8px]">{e.event}</span><span className="truncate opacity-60 italic font-mono mt-1">{JSON.stringify(e.details)}</span></div>))}<button onClick={() => { setIsAuditOpen(true); refreshAuditLog(); }} className="alce-button baunk-style text-[7px] mt-4 w-full bg-white">[ VIEW_FULL_CHAIN ]</button></div>
      </aside>

      <MobileNav active={mobileView} setActive={setMobileView} />
      <footer className="facet hidden md:flex col-span-full h-8 items-center justify-center bg-zinc/5 border-t border-sovereign text-[7px] baunk-style opacity-30 tracking-[2em] font-bold">ALLUCI_EXECUTIVE_OS_v4.3_STABLE_SOVEREIGN_PROTOCOL</footer>

      {
        (isAuditOpen || isPreferencesOpen || isSettingsOpen || isDriveOpen || isSoulOpen || isApiManifoldOpen || isTaskPanelOpen) && (
          <div className="fixed inset-0 z-[100] bg-black/60 backdrop-blur-sm p-0 md:p-6 flex items-end md:items-center justify-center animate-in fade-in duration-300">
            <div className="facet w-full h-[100dvh] md:h-[90vh] md:w-full md:max-w-6xl bg-white shadow-2xl flex flex-col border-t-2 md:border-2 border-sovereign overflow-hidden animate-in slide-in-from-bottom-10 md:zoom-in-95 relative">
              <header className="p-4 md:p-8 border-b border-sovereign flex justify-between items-center bg-white z-[120]">
                <div className="flex flex-col"><h2 className="baunk-style text-xs md:text-lg tracking-[0.2em] md:tracking-[0.5em] truncate max-w-[200px] md:max-w-none">{isAuditOpen ? 'EXECUTIVE_LEDGER' : isSettingsOpen ? 'SKILL_MANIFEST' : isPreferencesOpen ? 'BRIDGE_DIRECTORY' : isDriveOpen ? 'FILE_MANIFOLD' : isSoulOpen ? 'SOUL_PREFERENCES' : isApiManifoldOpen ? 'API_MANIFOLD_PREFERENCES' : isTaskPanelOpen ? 'TASK_MANIFOLD' : ''}</h2><span className="text-[6px] md:text-[8px] font-mono opacity-30 uppercase mt-1">Sovereign_Protocol_v4.3_Active</span></div>
                <button onClick={() => { setIsAuditOpen(false); setIsPreferencesOpen(false); setIsSettingsOpen(false); setIsDriveOpen(false); setIsSoulOpen(false); setIsApiManifoldOpen(false); setIsTaskPanelOpen(false); setSelectedSkill(null); setShowSkillWizard(false); }} className="alce-button baunk-style text-[9px] md:text-[10px] hover:bg-tension px-4 md:px-10 py-2">[ EXIT ]</button>
              </header>
              <div className="flex-1 overflow-y-auto p-4 md:p-10 scrollbar-hide relative">
                {isTaskPanelOpen ? (<TaskPanel onClose={() => setIsTaskPanelOpen(false)} />) : isApiManifoldOpen ? (
                  <div className="flex flex-col items-center justify-center py-20 gap-8">
                    <h3 className="baunk-style text-lg tracking-widest text-center">SOVEREIGN_API_MANIFOLD_CONTROL</h3>
                    <button
                      onClick={() => { setIsApiManifoldOpen(false); setIsApiWizardOpen(true); }}
                      className="alce-button baunk-style text-[10px] px-12 py-4 bg-sovereign text-white hover:bg-agent"
                    >
                      [ LAUNCH_API_WIZARD ]
                    </button>
                  </div>
                ) : isSoulOpen ? (<SoulPreferencesPanel onClose={() => setIsSoulOpen(false)} onManifestUpdate={handleManifestUpdate} />) : isPreferencesOpen ? (
                  <div className="flex flex-col gap-16">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-16">
                      <div className="flex flex-col">
                        <h3 className="baunk-style text-[12px] border-b border-sovereign pb-1 mb-8 opacity-50 tracking-[0.3em]">Security_&_Trust_Protocol</h3>
                        <div className="p-6 bg-agent/5 border border-agent/20 text-[10px] font-mono leading-relaxed mb-10 space-y-4">
                          <p>● <span className="font-bold">ONE_TOUCH_LOGIN</span>: Enabled for all verified biometric platforms.</p>
                          <p>● <span className="font-bold">E2E_ENCRYPTION</span>: Mandatory for iMessage, Signal, and WhatsApp bridges.</p>
                          <p>● <span className="font-bold">SESSION_ISOLATION</span>: Each bridge operates in a secure Simplicial Vault.</p>
                          <p>● <span className="font-bold">AUTONOMY_LEVEL</span>: Full sovereign execution authorized via VerusID.</p>
                        </div>
                        <div className="grid grid-cols-2 gap-4 max-w-sm">
                          <button className="alce-button text-[8px] baunk-style w-full bg-sovereign text-white">[ ROTATE_KEYS ]</button>
                          <button className="alce-button text-[8px] baunk-style w-full">[ FLUSH_CACHE ]</button>
                        </div>
                      </div>

                      <div className="flex flex-col">
                        <h3 className="baunk-style text-[12px] border-b border-sovereign pb-1 mb-8 opacity-50 tracking-[0.3em]">Hardware_&_Safety_Report</h3>
                        <div className="p-6 bg-zinc/5 border border-zinc/10 text-[10px] font-mono leading-relaxed space-y-4">
                          <div className="flex justify-between">
                            <span className="opacity-40">ARCHITECTURE:</span>
                            <span className="font-bold">{navigator.userAgent.includes('Mac OS X') ? 'APPLE_SILICON' : 'X86_64_LINUX'}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="opacity-40">ACCELERATION:</span>
                            <span className="text-agent font-bold">[ METAL_ACTIVE ]</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="opacity-40">MANIFOLD_INTEGRITY:</span>
                            <span className="text-flux font-bold">100%_SECURE</span>
                          </div>
                          <div className="pt-4 border-t border-zinc/10 text-[8px] opacity-40">
                            Strict Isolation Protocol: Data and Vault keys never leave local hardware.
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="space-y-12 pb-20">
                      {Object.entries(groupedConnections).map(([groupName, groupConns]) => (
                        <div key={groupName}>
                          <h3 className="baunk-style text-[12px] border-b border-sovereign pb-1 mb-8 opacity-50 tracking-[0.3em]">{groupName}</h3>
                          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                            {groupConns.map(conn => (
                              <div key={conn.id} className={`facet p-6 transition-all duration-300 group hover:shadow-xl ${conn.status === 'CONNECTED' ? 'border-agent shadow-lg' : 'border-zinc/20 hover:border-sovereign'}`}>
                                <div className="flex justify-between items-start mb-6">
                                  <div className="flex flex-col">
                                    <span className="baunk-style text-[10px] block font-bold mb-1">{conn.name}</span>
                                    <span className="text-[7px] font-mono opacity-40 uppercase">{conn.type}</span>
                                  </div>
                                  <div className="flex flex-col items-end gap-1">
                                    <span className={`text-[6px] baunk-style px-1.5 py-0.5 border ${conn.status === 'CONNECTED' ? 'bg-agent text-white border-agent' : 'bg-zinc/5 opacity-40 border-zinc/20'}`}>
                                      {conn.authType}
                                    </span>
                                    {conn.isEncrypted && (
                                      <span className="text-[5px] baunk-style text-agent">[ E2EE_ACTIVE ]</span>
                                    )}
                                  </div>
                                </div>
                                {conn.status === 'CONNECTED' ? (
                                  <div className="flex items-center gap-3 mb-6 animate-in slide-in-from-top-2">
                                    <div className="relative">
                                      <img src={conn.profileImg || `https://api.dicebear.com/7.x/identicon/svg?seed=${conn.id}`} className="w-10 h-10 rounded-full border border-sovereign/10 grayscale group-hover:grayscale-0 transition-all" alt="" />
                                      <div className="absolute bottom-0 right-0 w-3 h-3 bg-agent rounded-full border-2 border-white shadow-sm" />
                                    </div>
                                    <div className="flex flex-col">
                                      <div className="text-[8px] font-bold font-mono text-sovereign">{conn.accountAlias}</div>
                                      <div className="text-[6px] font-mono opacity-40 uppercase tracking-tighter">Vault_ID: {conn.id.substring(0, 8)}...</div>
                                    </div>
                                  </div>
                                ) : (
                                  <div className="h-10 mb-6 flex items-center justify-center border border-dashed border-zinc/20 bg-zinc/5">
                                    <span className="text-[7px] font-mono opacity-20 uppercase tracking-widest italic">{conn.name} Offline</span>
                                  </div>
                                )}
                                <button onClick={() => startAuthFlow(conn)} className={`alce-button py-3 text-[8px] w-full baunk-style transition-all ${conn.status === 'CONNECTED' ? 'text-tension border-tension hover:bg-tension hover:text-white' : 'text-sovereign hover:bg-sovereign hover:text-white'}`}>
                                  {conn.status === 'CONNECTED' ? '[ TERMINATE_VAULT ]' : '[ ACTIVATE_BRIDGE ]'}
                                </button>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : isSettingsOpen ? (showSkillWizard ? (<SkillBuilderWizard onClose={() => { setShowSkillWizard(false); fetchSkills(); }} />) : (<div className="grid grid-cols-1 md:grid-cols-2 gap-6 relative"><div onClick={() => setShowSkillWizard(true)} className="facet p-8 border-dashed border-zinc/20 hover:border-agent transition-all duration-300 group cursor-pointer flex flex-col items-center justify-center gap-4 bg-zinc/5 hover:bg-agent/5 h-[300px]"><div className="w-16 h-16 rounded-full border border-zinc/20 flex items-center justify-center group-hover:border-agent transition-colors"><span className="text-2xl text-zinc-400 group-hover:text-agent">+</span></div><span className="baunk-style text-[10px] tracking-[0.2em] group-hover:text-agent">CREATE_NEW_COGNITIVE_MODULE</span></div>{skills.map(skill => (<div key={skill.id} onClick={() => setSelectedSkill(skill)} className={`facet p-8 border-zinc/10 relative hover:border-agent transition-all duration-500 group cursor-pointer ${!skill.verified ? 'opacity-40 grayscale' : 'shadow-sm'}`}><div className="flex justify-between items-start mb-6"><div className="flex flex-col"><span className="baunk-style text-[12px] group-hover:text-agent transition-colors">{skill.name}</span><span className="text-[7px] font-mono opacity-30 mt-1 uppercase tracking-tighter">{skill.category} / {skill.id}</span></div><div className="flex gap-2"><button onClick={(e) => { e.stopPropagation(); handleDeleteSkill(skill.id); }} className="px-2 py-1 text-[8px] baunk-style text-red-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity">✕</button><button onClick={(e) => { e.stopPropagation(); handleToggleSkill(skill.id); }} className={`px-3 py-1 text-[8px] baunk-style border ${skill.verified ? 'bg-agent text-white border-agent' : 'bg-white text-zinc border-zinc/20 hover:border-tension hover:text-tension'}`}>{skill.verified ? '[ ACTIVE ]' : '[ OFFLINE ]'}</button></div></div><div className="space-y-2 mb-6"><span className="text-[7px] baunk-style opacity-30 block">Capabilities:</span><div className="flex flex-wrap gap-1">{(skill.capabilities || []).length > 0 ? (skill.capabilities.map((cap, ci) => (<span key={ci} className="bg-zinc/5 border border-zinc/10 px-2 py-0.5 text-[7px] font-mono opacity-60 truncate max-w-full">{cap}</span>))) : (<span className="text-[7px] font-mono opacity-30 italic">No specific tool bindings.</span>)}</div></div><div className="flex justify-between items-center text-[7px] font-mono opacity-20 mt-8 pt-4 border-t border-zinc/5"><span>SIG: {skill.signature}</span></div></div>))}</div>)) : isDriveOpen ? (<div className="flex flex-col items-center justify-center h-full gap-12 py-20"><div className="relative"><div className="absolute inset-0 bg-agent/5 rounded-full blur-3xl scale-150 animate-pulse" /><PolytopeIdentity color="#000" size={160} active={isConnected} /></div><div className="text-center space-y-4 max-w-xl px-6"><h3 className="baunk-style text-xl tracking-[0.8em]">MANIFOLD_STORAGE_STABLE</h3><p className="text-[11px] opacity-40 font-mono leading-relaxed">Awaiting sovereign data packets. Integrated iCloud, Google Drive, and MS Teams bridges are prepared for bi-directional synchronization.</p></div><button onClick={() => fileInputRef.current?.click()} className="alce-button baunk-style text-[10px] px-20 h-16">[ UPLOAD_DATA_PACKET ]</button></div>) : null}
              </div>
              {selectedSkill && (
                <div className="absolute top-0 md:top-24 left-0 md:left-1/2 md:-translate-x-1/2 z-[150] w-full h-full md:h-auto md:w-[90%] max-w-2xl md:max-h-[75vh] bg-white border-2 border-sovereign shadow-[0_20px_60px_rgba(0,0,0,0.3)] flex flex-col animate-in slide-in-from-top-10 duration-500">
                  <header className="p-6 border-b border-sovereign flex justify-between items-center bg-white shrink-0"><div className="flex flex-col"><span className="text-agent baunk-style text-[8px] tracking-[0.4em] mb-1">{selectedSkill.category}</span><h3 className="baunk-style text-sm md:text-base tracking-tighter">{selectedSkill.name}</h3></div><button onClick={() => setSelectedSkill(null)} className="alce-button baunk-style text-[8px] hover:bg-tension border-none font-bold">[ EXIT ]</button></header>
                  <div className="flex-1 overflow-y-auto p-8 scrollbar-hide space-y-10">
                    <section className="space-y-4"><h4 className="baunk-style text-[10px] opacity-40 border-b border-sovereign/10 pb-1">Skill_Overview</h4><p className="text-xs font-mono leading-relaxed opacity-70">{selectedSkill.description}</p></section>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8"><section className="space-y-3"><h4 className="baunk-style text-[9px] text-agent">Mindsets</h4><ul className="space-y-2">{selectedSkill.mindsets.map((m, i) => (<li key={i} className="text-[10px] font-mono flex gap-2"><span className="opacity-30">[{i + 1}]</span><span className="uppercase">{m}</span></li>))}</ul></section><section className="space-y-3"><h4 className="baunk-style text-[9px] text-flux">Methodologies</h4><ul className="space-y-2">{selectedSkill.methodologies.map((m, i) => (<li key={i} className="text-[10px] font-mono flex gap-2"><span className="opacity-30">[{i + 1}]</span><span>{m}</span></li>))}</ul></section></div>
                    <section className="space-y-4"><h4 className="baunk-style text-[9px] text-tension">Cognitive_Chains_&_Logic</h4><div className="bg-zinc/5 p-4 border border-zinc/10 space-y-4"><div className="flex flex-wrap gap-3 items-center">{selectedSkill.chainsOfThought.map((t, i) => (<React.Fragment key={i}><div className="flex items-center gap-2 text-[9px] font-mono"><span className="bg-sovereign text-white w-4 h-4 rounded-full flex items-center justify-center text-[7px]">{i + 1}</span><span>{t}</span></div>{i < selectedSkill.chainsOfThought.length - 1 && <span className="text-agent opacity-40">→</span>}</React.Fragment>))}</div><div className="pt-3 border-t border-zinc/10"><span className="text-[7px] baunk-style opacity-30 block mb-1">Fundamental_Logic:</span><div className="space-y-1">{selectedSkill.logic.map((l, i) => (<p key={i} className="text-[10px] font-mono italic opacity-60">"{l}"</p>))}</div></div></div></section>
                    <section className="space-y-4"><h4 className="baunk-style text-[9px] text-sovereign">Best_Practices_Guide</h4><div className="space-y-2">{selectedSkill.bestPractices && selectedSkill.bestPractices.map((b, i) => (<div key={i} className="p-3 bg-white border border-sovereign/5 text-[10px] font-mono flex gap-3 shadow-sm"><span className="text-agent">●</span><span>{b}</span></div>))}</div></section>
                    <footer className="pt-8 border-t border-zinc/10 flex flex-col gap-2 text-[6px] font-mono opacity-20 pb-4"><span>SIGNATURE: {selectedSkill.signature}</span><span>PUBLIC_KEY: {selectedSkill.publicKey}</span><span>AUTHORIZED_EXECUTIVE_MANIFOLD_CALIBRATION_STABLE</span></footer>
                  </div>
                </div>
              )}
            </div>
          </div>
        )
      }
    </div >
  );
};

export default App;
