import React, { useState, useEffect } from 'react';
import { 
  Plus, Trash2, Activity, Play, Settings2, Bell, MessageSquare, 
  Terminal, BarChart3, HardDrive, Clock, Globe, ShieldAlert,
  Save, AlertCircle, ChevronDown, ChevronUp, History
} from 'lucide-react';

interface HeartbeatOrder {
  id: string;
  label: string;
  active: boolean;
  probe_type: string;
  probe_config: Record<string, any>;
  action_type: string;
  action_config: Record<string, any>;
  interval_minutes: number;
}

interface Props {
  initialOrders: HeartbeatOrder[];
  onSave: (orders: HeartbeatOrder[]) => void;
  agentId?: string; // If provided, shows "Agent" specific context
}

const PROBE_TYPES = [
  { id: 'cron_expression', label: 'Schedule (Cron)', icon: Clock, desc: 'Always fires at the set interval' },
  { id: 'file_watch', label: 'File Watcher', icon: HardDrive, desc: 'Fires when a file or directory content changes' },
  { id: 'task_deadline', label: 'Task Deadline', icon: ShieldAlert, desc: 'Fires when TASKS.md has overdue items' },
  { id: 'url_fetch', label: 'URL Monitor', icon: Globe, desc: 'Fires when URL content changes or keyword is found' },
  { id: 'goal_progress', label: 'Goal Progress', icon: BarChart3, desc: 'Fires when a goal falls below a progress %' },
  { id: 'memory_pattern', label: 'Memory Pattern', icon: Settings2, desc: 'Fires when a keyword appears in memory N times' },
  { id: 'system_health', label: 'System Health', icon: Activity, desc: 'Fires on high task failure rates' },
  { id: 'bridge_silence', label: 'Bridge Silence', icon: MessageSquare, desc: 'Fires when a bridge message remains unanswered' }
];

const ACTION_TYPES = [
  { id: 'notify_ws', label: 'Show Toast', icon: Bell, desc: 'Push a notification to the browser UI' },
  { id: 'pcl_signal', label: 'PCL Signal', icon: Activity, desc: 'Store a structured signal for PCL reasoning' },
  { id: 'execute_objective', label: 'Run Objective', icon: Terminal, desc: 'Execute a specific task/DAG via Orchestrator' },
  { id: 'notify_bridge', label: 'Send Bridge Msg', icon: MessageSquare, desc: 'Send a message through Discord/Telegram/etc' },
  { id: 'evaluate_goal', label: 'Evaluate Goal', icon: Play, desc: 'Trigger an automated goal progress check' },
  { id: 'log_only', label: 'Log Only', icon: History, desc: 'Quietly log the event to H-LSM memory' }
];

export const HeartbeatOrderEditor: React.FC<Props> = ({ initialOrders, onSave, agentId }) => {
  const [orders, setOrders] = useState<HeartbeatOrder[]>(initialOrders);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const addOrder = () => {
    const newOrder: HeartbeatOrder = {
      id: Math.random().toString(36).substring(2, 10),
      label: 'New Heartbeat Monitor',
      active: true,
      probe_type: 'cron_expression',
      probe_config: {},
      action_type: 'log_only',
      action_config: {},
      interval_minutes: 15
    };
    setOrders([...orders, newOrder]);
    setExpandedId(newOrder.id);
  };

  const removeOrder = (id: string) => {
    setOrders(orders.filter(o => o.id !== id));
  };

  const updateOrder = (id: string, updates: Partial<HeartbeatOrder>) => {
    setOrders(orders.map(o => o.id === id ? { ...o, ...updates } : o));
  };

  return (
    <div className="space-y-4 text-sm">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-zinc-400 font-medium flex items-center gap-2">
          <Activity className="w-4 h-4 text-sky-400" />
          Pulse Configuration
        </h3>
        <button 
          onClick={addOrder}
          className="px-3 py-1.5 bg-sky-500/10 hover:bg-sky-500/20 text-sky-400 rounded-lg flex items-center gap-2 transition-colors border border-sky-500/20"
        >
          <Plus className="w-4 h-4" />
          Add Heartbeat
        </button>
      </div>

      {orders.length === 0 && (
        <div className="p-8 border border-dashed border-zinc-800 rounded-xl text-center text-zinc-500 italic">
          No heartbeat orders configured for this identity.
        </div>
      )}

      {orders.map((order) => {
        const isExpanded = expandedId === order.id;
        const SelectedProbe = PROBE_TYPES.find(p => p.id === order.probe_type) || PROBE_TYPES[0];
        const SelectedAction = ACTION_TYPES.find(a => a.id === order.action_type) || ACTION_TYPES[0];

        return (
          <div key={order.id} className={`border ${isExpanded ? 'border-zinc-700 bg-zinc-900/50' : 'border-zinc-800 bg-zinc-900/20'} rounded-xl overflow-hidden transition-all shadow-lg`}>
            {/* Header */}
            <div 
              className="px-4 py-3 flex items-center gap-3 cursor-pointer hover:bg-zinc-800/30 group"
              onClick={() => setExpandedId(isExpanded ? null : order.id)}
            >
              <input 
                type="checkbox"
                checked={order.active}
                onChange={(e) => {
                  e.stopPropagation();
                  updateOrder(order.id, { active: e.target.checked });
                }}
                className="w-4 h-4 rounded border-zinc-700 bg-zinc-800 text-sky-500 focus:ring-sky-500/20"
              />
              <div className="flex-1 min-w-0">
                <input 
                  type="text"
                  value={order.label}
                  onChange={(e) => updateOrder(order.id, { label: e.target.value })}
                  onClick={(e) => e.stopPropagation()}
                  className="bg-transparent border-none p-0 focus:ring-0 text-zinc-100 font-medium w-full placeholder-zinc-600"
                  placeholder="Monitor Label..."
                />
              </div>
              <div className="flex items-center gap-2 text-zinc-500 text-xs shrink-0">
                <div className="flex items-center gap-1 group-hover:text-zinc-300">
                  <SelectedProbe.icon className="w-3.5 h-3.5" />
                  <span>{SelectedProbe.label}</span>
                </div>
                <span>→</span>
                <div className="flex items-center gap-1 group-hover:text-zinc-300">
                  <SelectedAction.icon className="w-3.5 h-3.5" />
                  <span>{SelectedAction.label}</span>
                </div>
              </div>
              <button 
                onClick={(e) => {
                  e.stopPropagation();
                  removeOrder(order.id);
                }}
                className="p-1.5 text-zinc-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <Trash2 className="w-4 h-4" />
              </button>
              {isExpanded ? <ChevronUp className="w-4 h-4 text-zinc-500" /> : <ChevronDown className="w-4 h-4 text-zinc-500" />}
            </div>

            {/* Details */}
            {isExpanded && (
              <div className="p-4 border-t border-zinc-800 space-y-6 bg-zinc-900/40">
                <div className="grid grid-cols-2 gap-6">
                  {/* Probe Section */}
                  <div className="space-y-3">
                    <label className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold flex items-center gap-1.5">
                      <Settings2 className="w-3 h-3" />
                      Condition Probe
                    </label>
                    <select 
                      value={order.probe_type}
                      onChange={(e) => updateOrder(order.id, { probe_type: e.target.value, probe_config: {} })}
                      className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-zinc-300 focus:border-sky-500/50 outline-none"
                    >
                      {PROBE_TYPES.map(p => (
                        <option key={p.id} value={p.id}>{p.label}</option>
                      ))}
                    </select>
                    <p className="text-[11px] text-zinc-600 italic px-1">{SelectedProbe.desc}</p>
                    
                    {/* Dynamic Probe Config */}
                    <div className="pt-2">
                       {order.probe_type === 'file_watch' && (
                         <input 
                           type="text"
                           placeholder="Path to file/dir..."
                           className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-zinc-300 placeholder-zinc-700"
                           value={order.probe_config.path || ''}
                           onChange={(e) => updateOrder(order.id, { probe_config: { ...order.probe_config, path: e.target.value } })}
                         />
                       )}
                       {order.probe_type === 'url_fetch' && (
                         <div className="space-y-2">
                            <input 
                              type="text" 
                              placeholder="https://..."
                              className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-zinc-300"
                              value={order.probe_config.url || ''}
                              onChange={(e) => updateOrder(order.id, { probe_config: { ...order.probe_config, url: e.target.value } })}
                            />
                            <div className="flex gap-2">
                              <input 
                                type="text"
                                placeholder="Keyword (optional)..."
                                className="flex-1 bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-zinc-300"
                                value={order.probe_config.keyword || ''}
                                onChange={(e) => updateOrder(order.id, { probe_config: { ...order.probe_config, keyword: e.target.value } })}
                              />
                            </div>
                         </div>
                       )}
                    </div>
                  </div>

                  {/* Action Section */}
                  <div className="space-y-3">
                    <label className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold flex items-center gap-1.5">
                      <Terminal className="w-3 h-3" />
                      Automatic Action
                    </label>
                    <select 
                      value={order.action_type}
                      onChange={(e) => updateOrder(order.id, { action_type: e.target.value, action_config: {} })}
                      className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-zinc-300 focus:border-sky-500/50 outline-none"
                    >
                      {ACTION_TYPES.map(a => (
                        <option key={a.id} value={a.id}>{a.label}</option>
                      ))}
                    </select>
                    <p className="text-[11px] text-zinc-600 italic px-1">{SelectedAction.desc}</p>

                    {/* Dynamic Action Config */}
                    <div className="pt-2">
                       {order.action_type === 'execute_objective' && (
                         <textarea 
                           placeholder="Sovereign objective to execute..."
                           className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-zinc-300 min-h-[60px]"
                           value={order.action_config.objective_template || ''}
                           onChange={(e) => updateOrder(order.id, { action_config: { ...order.action_config, objective_template: e.target.value } })}
                         />
                       )}
                       {order.action_type === 'notify_bridge' && (
                         <div className="space-y-2">
                            <input 
                              type="text" 
                              placeholder="Bridge ID (discord, telegram...)"
                              className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-zinc-300"
                              value={order.action_config.bridge_id || ''}
                              onChange={(e) => updateOrder(order.id, { action_config: { ...order.action_config, bridge_id: e.target.value } })}
                            />
                            <input 
                              type="text"
                              placeholder="Recipient (channel_id/user_id)..."
                              className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-zinc-300"
                              value={order.action_config.recipient || ''}
                              onChange={(e) => updateOrder(order.id, { action_config: { ...order.action_config, recipient: e.target.value } })}
                            />
                         </div>
                       )}
                    </div>
                  </div>
                </div>

                <div className="pt-4 border-t border-zinc-800/50 flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-zinc-500 uppercase font-bold">Run Every</span>
                      <input 
                        type="number"
                        value={order.interval_minutes}
                        onChange={(e) => updateOrder(order.id, { interval_minutes: parseInt(e.target.value) || 1 })}
                        className="w-16 bg-zinc-950 border border-zinc-800 rounded px-2 py-1 text-zinc-300 text-xs"
                      />
                      <span className="text-zinc-600 text-[10px]">MINS</span>
                    </div>
                  </div>
                  <div className="text-[10px] text-zinc-600 flex items-center gap-1.5">
                    <AlertCircle className="w-3 h-3" />
                    Changes are pending save.
                  </div>
                </div>
              </div>
            )}
          </div>
        );
      })}

      <div className="pt-6 flex justify-end">
        <button 
          onClick={() => onSave(orders)}
          className="px-6 py-2 bg-zinc-100 hover:bg-white text-zinc-950 rounded-xl flex items-center gap-2 font-bold transition-all shadow-[0_0_20px_rgba(255,255,255,0.1)] hover:scale-[1.02]"
        >
          <Save className="w-4 h-4" />
          Update Identities
        </button>
      </div>
    </div>
  );
};
